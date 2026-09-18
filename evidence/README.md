# Evidence

Raw records behind the numbers quoted in the README and in `docs/QA.md`.

| File | What it is |
|---|---|
| `unit-final.txt` | Verbose output of the last local run of the full test suite |
| `first-live-2026-09-18.json` | Burst 1 summary and its eleven validated receipts |
| `live-2026-09-18-run2.json` | Burst 2 summary and twelve receipts |
| `compare-live-2026-09-18.json`, `compare-live-2026-09-18-run2.json` | Four-case compares: Jev, replay, keyword rules |
| `experiments-live-2026-09-18.json` | Stability probes (S02, S04) and evidence ablations (S02, S04) |
| `compare-claude-code-2026-09-18.json` | Two-case compare with the Claude-subscription arm |
| `compare-full-2026-09-18.json` | Twelve-case compare: Jev, Claude subscription, replay, keyword rules |

All cases are authored and synthetic. The files contain requests, responses, receipts and summaries, and nothing else: no key, no session token, no personal or company data. Receipt ids are random tokens issued by the server for that session.
