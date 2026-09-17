# Verification record and remaining risk

**Build date: September 17, 2026. Local prototype version: 0.2.0.**

## Executed

| Check | Result | Evidence |
|---|---|---|
| Python unit, policy, metrics, mock transport and real loopback HTTP tests | 74 tests passed, no skipped tests in the final run | `evidence/unit-final.txt` |
| Authored data generation | Rebuilt offline from versioned scripts | `scripts/setup_lab.py` |
| All twelve replay contracts and policy runs | Passed | `python3 -m jev_lab check` |
| JavaScript syntax | Passed | `node --check web/app.js` |
| UI interactions and rendering | Nine scripted checks passed; no page JavaScript errors | `evidence/browser-check.json` |
| Desktop and narrow-screen inspection | Screenshots inspected at 1440px and 390px viewport widths | `evidence/desktop.png`, `evidence/mobile.png` |
| Supplied frontier file scan | 29 mounted files; no literal Jev, TypeSafe or RLCD matches | `evidence/project-scan.json` |

The file scan is lexical evidence only. It does not establish that the conceptual direction was absent or that a live ingestion pipeline failed.

## Browser limitation—do not hide this

The Browser plugin was not available. System Chromium was available through Playwright, but direct navigation to the local server returned `ERR_BLOCKED_BY_ADMINISTRATOR`. No administrator policy was disabled. The browser test therefore rendered the local HTML/CSS/JavaScript and used a test-only fetch bridge to the **actual loopback HTTP server**.

That verified real UI state changes and backend responses, but it did **not** verify ordinary browser-network routing or enforcement of the server’s CSP in a normal target-device session. The separate HTTP tests exercise origin/token handling and endpoint behavior. Codex must still open the actual server normally on the target device and confirm network/CSP behavior before calling that integration complete.

## Interaction evidence

The script ran a replay case, inspected distributions, revoked simulated approval, held the action, expired evidence, replayed policy without a new call, exported a JSON receipt, mapped exact calculation to deterministic code, filtered the historical source chronology, evaluated all authored fixtures, and attempted unconfigured live mode. The live attempt failed explicitly and did not fall back to synthetic inference.

Visual inspection checked readable input/result hierarchy, persistent provenance labeling, case navigation, distribution controls, policy controls, action-gate copy, desktop alignment and narrow-screen flow. The narrow scenario selector intentionally scrolls horizontally; the whole document does not overflow.

## Not executed or established

No authenticated TypeSafe request; no Vercel evaluation request; no live comparator; no real-world calibration or security-attack efficacy measurement; no full six-head independently adjudicated benchmark; no actual tracker ingestion-log replay; no real company/client data; no external action; no enterprise procurement approval; no production load/security test; no target macOS/Safari session.

The hosted CI workflow is provided. A local passing run is not proof that GitHub Actions ran successfully; inspect the PR checks and account billing/runner availability separately.

## Local environment

Python 3.13, Node 22, system Chromium, Python Playwright. Runtime itself uses only Python standard library and local browser assets. Other advertised Python 3.10+ environments need target-device verification. No real API key was used or bundled.

## Reproduce

```bash
python3 scripts/setup_lab.py
python3 -m unittest discover -s tests -v
node --check web/app.js
python3 -m jev_lab check
python3 -m jev_lab eval --out runs/replay-evaluation.json
python3 -m jev_lab
```

For the container-style bridged browser test, install Playwright as development tooling only and adapt `executable_path` in `scripts/browser_check.py` to the available Chromium binary. A normal target-device browser run is preferred to that fallback.
