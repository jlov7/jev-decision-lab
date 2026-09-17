"""python -m jev_lab: offline-first commands with explicit network consent."""
import argparse
import json
from pathlib import Path
from . import engine, metrics, server, experiments


def main():
    p = argparse.ArgumentParser(description='Synthetic-first enterprise judgment experiments')
    p.add_argument('command', nargs='?', choices=['serve', 'eval', 'smoke', 'check', 'bench'], default='serve')
    p.add_argument('--port', type=int, default=8765)
    p.add_argument('--mode', choices=['replay', 'live'], default='replay')
    p.add_argument('--allow-network', action='store_true')
    p.add_argument('--out', default='runs/result.json')
    p.add_argument('--repeats', type=int, default=1)
    args = p.parse_args()
    if args.command == 'serve':
        return server.serve(args.port)
    if args.mode == 'live' and not args.allow_network:
        p.error('Live commands require --allow-network and server-side environment configuration')
    if args.command == 'check':
        for c in engine.cases():
            engine.run(c['id'])
        print(f'{len(engine.cases())} teaching cases validate. No network calls.')
        return
    if args.command == 'bench':
        if args.mode != 'live' or not args.allow_network:
            p.error('bench requires --mode live --allow-network')
        result = experiments.benchmark(repeats=args.repeats)
        failed = any(not s['all_successful'] for r in result['results'] for s in r['shapes'])
    else:
        ids = [engine.cases()[0]['id']] if args.command == 'smoke' else [c['id'] for c in engine.cases()]
        receipts, errors = [], []
        for case_id in ids:
            try:
                receipts.append(engine.run(case_id, args.mode, consent=args.allow_network))
            except (ValueError, PermissionError, RuntimeError) as exc:
                errors.append({'case_id': case_id, 'error': str(exc)})
                break
        result = {'mode': args.mode, 'requested_cases': len(ids), 'succeeded': len(receipts),
                  'failed': len(errors), 'not_attempted': len(ids) - len(receipts) - len(errors),
                  'errors': errors, 'receipts': receipts}
        if args.command == 'eval':
            result['evaluation'] = metrics.evaluate(receipts, engine.load('labels'))
        failed = bool(errors)
    path = Path(args.out)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    print(f'Wrote {path}. ' + ('A failure was recorded; no fallback was used.' if failed else 'Command completed. Inspect provenance before interpreting results.'))
    if failed:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
