import argparse
import json
from pathlib import Path
from . import engine, metrics, server, experiments

def main():
    p=argparse.ArgumentParser(description='Jev Decision Lab: synthetic-first enterprise decision experiments')
    p.add_argument('command',nargs='?',choices=['serve','eval','smoke','check','bench'],default='serve')
    p.add_argument('--port',type=int,default=8765)
    p.add_argument('--mode',choices=['replay','live'],default='replay')
    p.add_argument('--allow-network',action='store_true',help='Explicit consent for sending supplied synthetic cases to TypeSafe')
    p.add_argument('--out',default='runs/result.json')
    p.add_argument('--repeats',type=int,default=1)
    args=p.parse_args()
    if args.command=='serve': return server.serve(args.port)
    if args.mode=='live' and not args.allow_network: p.error('Live commands require --allow-network plus the server environment configuration')
    if args.command=='bench':
        if args.mode!='live' or not args.allow_network: p.error('bench requires --mode live --allow-network')
        result=experiments.benchmark(repeats=args.repeats)
        path=Path(args.out);path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
        print(f'Wrote live request-shape experiment to {path}')
        if any(not shape['all_successful'] for repeat in result['results'] for shape in repeat['shapes']): raise SystemExit(1)
        return
    if args.command=='check':
        for c in engine.cases(): engine.run(c['id'])
        print('All 12 synthetic cases and provider contracts validate. No network calls.')
        return
    ids=[engine.cases()[0]['id']] if args.command=='smoke' else [c['id'] for c in engine.cases()]
    receipts=[]; errors=[]
    for case_id in ids:
        try: receipts.append(engine.run(case_id,args.mode,consent=args.allow_network))
        except (ValueError,PermissionError,RuntimeError) as exc:
            errors.append({'case_id':case_id,'error':str(exc)})
            # Stop rather than repeatedly sending a known-broken request/account configuration.
            break
    result={'mode':args.mode,'requested_cases':len(ids),'succeeded':len(receipts),'failed':len(errors),
            'not_attempted':len(ids)-len(receipts)-len(errors),'errors':errors,'receipts':receipts}
    if args.command=='eval': result['evaluation']=metrics.evaluate(receipts,engine.load('labels'))
    path=Path(args.out);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(f'Wrote {path}: {len(receipts)} succeeded, {len(errors)} failed; {result["not_attempted"]} not attempted.')
    if errors: raise SystemExit(1)

if __name__=='__main__':main()
