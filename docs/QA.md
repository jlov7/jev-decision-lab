# Verification record and remaining risk

**Build date: September 17, 2026. Local prototype version: 0.3.0.**

## Executed

| Check | Result | Evidence |
|---|---|---|
| Python unit, policy, metrics, adapter, comparator, showcase, Claude arm, CLI, mock transport and real loopback HTTP tests | 161 tests passed, no skipped tests in the final run | `evidence/unit-final.txt` |
| Provider adapter interface and per-arm comparator | Two-track interface, public contract distinction between `boolean` and `noul`, provenance separation, retained failures and unavailable-not-zero reporting all pass | `tests/test_adapters.py`, `tests/test_comparator.py` |
| `compare` command and its live gate | Live arms are refused unless `--mode live` and `--allow-network` are both set; an unconsented arm makes no call, and a consented arm's own failure is retained verbatim | `tests/test_cli_compare.py` |
| Authored data generation | Rebuilt offline from versioned scripts | `scripts/setup_lab.py` |
| All twelve replay contracts and policy runs | Passed | `python3 -m jev_lab check` |
| JavaScript syntax | Passed | `node --check web/app.js` |
| UI interactions and rendering | Nine scripted checks passed; no page JavaScript errors | `evidence/browser-check.json` |
| Desktop and narrow-screen inspection | Screenshots inspected at 1440px and 390px viewport widths | `evidence/desktop.png`, `evidence/mobile.png` |
| Supplied frontier file scan | 29 mounted files; no literal Jev, TypeSafe or RLCD matches | `evidence/project-scan.json` |

The file scan is lexical evidence only. It does not establish that the conceptual direction was absent or that a live ingestion pipeline failed.

## Live lab (v0.3) — what was verified and how

| Check | Result | Evidence |
|---|---|---|
| Burst, playground validation, compare wrapper, Claude arm contract | Unit-tested with controlled responses: consent and configuration gates refuse before any call; attempt cap checked before a burst; one failure does not stop the others; distribution never fabricated; truncated or refused Claude output fails closed | `tests/test_showcase.py`, `tests/test_llm_arm.py`, `tests/test_server.py` |
| Real browser, real server, real CSP | Opened in the Claude desktop browser pane against the running stdlib server. The server's `style-src 'self'` policy **blocked** the first draft's inline `style` attributes; they were removed and stagger moved to CSS. Final check: zero `[style]` elements, no console errors, no document overflow at 375px | this record |
| Live-lab error paths in the browser | Burst in live mode without a key, playground without a key, compare without consent, compare with consent but no key: each shows the specific server refusal; the last retains twelve identical failures and fabricates nothing | this record |
| Claude SDK call shape | `anthropic` 1.6.0 installed via the `compare` extra; `messages.create` accepts `system`, `output_config` and the client accepts `max_retries=0`. No network call was made | this record |

The Claude arm and the live burst have **not** been run against a live route in this build. They will run the first time the account owner sets the keys and ticks consent. The first live result should be read for validator behaviour before any number from it is quoted.

## Browser limitation—do not hide this

The Browser plugin was not available. System Chromium was available through Playwright, but direct navigation to the local server returned `ERR_BLOCKED_BY_ADMINISTRATOR`. No administrator policy was disabled. The browser test therefore rendered the local HTML/CSS/JavaScript and used a test-only fetch bridge to the **actual loopback HTTP server**.

That verified real UI state changes and backend responses, but it did **not** verify ordinary browser-network routing or enforcement of the server’s CSP in a normal target-device session. The separate HTTP tests exercise origin/token handling and endpoint behavior. Codex must still open the actual server normally on the target device and confirm network/CSP behavior before calling that integration complete.

A later real-browser pass through the Playwright MCP did open the running server normally and confirmed all four tabs, the export receipt and the 390px layout (`scrollWidth` 390 against `clientWidth` 399, no document overflow). It also surfaced one cosmetic `favicon.ico` 404. That pass is supplementary evidence for the UI, not a substitute for a check on the target device.

## Gateway adapter boundary—do not hide this

`jev_lab/adapters.py` puts both providers behind one explicit interface, but they are not equally verified.

The native arm wraps the existing transport and inherits its HTTP tests. The **Gateway arm is a mapping layer only**. It is pinned to `ai@7.0.105`; it maps the AI SDK's `boolean` answer onto the native `noul` proposition while keeping the two names visibly distinct in provenance (`wire_type` `boolean` versus `noul`, `source` `provider_boolean` versus `provider_noul`); and it preserves the provider's `typesafe_confidence` statistic as a separate field rather than relabelling it as a class probability.

That arm has **never made a request**. Gateway evaluation is exposed only through the AI SDK (TypeScript, v7 or later) — not through the OpenAI-, Anthropic- or Cohere-compatible endpoints — so a standard-library Python prototype cannot call `experimental_evaluate` itself. With no approved transport configured, the arm records

> No approved Gateway transport is configured, so nothing was sent. Evaluation is exposed only through the AI SDK (TypeScript, v7 or later); supply a transport that performs that call. Do not guess the wire schema.

and `live_verified` is `false` in every report it produces. The request and response shapes in the adapter are transcribed from the vendor's own evaluation documentation and recorded in `docs/ACCESS_AND_TROUBLESHOOTING.md`; nothing about the wire format was inferred from third-party commentary.

One consequence is stated in the adapter rather than hidden: the AI SDK returns no probability distribution for Choice or Score answers, so a Gateway response cannot satisfy the native validator's distribution requirement. The adapter reports that mismatch instead of synthesizing a distribution to make validation pass.

## Interaction evidence

The script ran a replay case, inspected distributions, revoked simulated approval, held the action, expired evidence, replayed policy without a new call, exported a JSON receipt, mapped exact calculation to deterministic code, filtered the historical source chronology, evaluated all authored fixtures, and attempted unconfigured live mode. The live attempt failed explicitly and did not fall back to synthetic inference.

Visual inspection checked readable input/result hierarchy, persistent provenance labeling, case navigation, distribution controls, policy controls, action-gate copy, desktop alignment and narrow-screen flow. The narrow scenario selector intentionally scrolls horizontally; the whole document does not overflow.

## Not executed or established

No authenticated TypeSafe request; no Vercel evaluation request; no comparator run against a live arm; no real-world calibration or security-attack efficacy measurement; no full six-head independently adjudicated benchmark; no actual tracker ingestion-log replay; no real company/client data; no external action; no enterprise procurement approval; no production load/security test; no target macOS/Safari session.

A comparator now exists (`jev_lab/comparator.py`, `python3 -m jev_lab compare`). It has never evaluated a live arm. It is exercised only against the bundled synthetic replay arm and against deliberately failing arms. Its separation guarantees — per-arm evaluation, no pooled metrics, an absent distribution reported as unavailable rather than as zero, and every failure retained — are verified offline. Its ability to compare real provider behaviour is not verified at all.

The hosted CI workflow is provided. A local passing run is not proof that GitHub Actions ran successfully; inspect the PR checks and account billing/runner availability separately.

## Local environment

Python 3.13, Node 22, system Chromium, Python Playwright. Runtime itself uses only Python standard library and local browser assets. Other advertised Python 3.10+ environments need target-device verification. No real API key was used or bundled.

## Reproduce

```bash
uv run python3 scripts/setup_lab.py
uv run python3 -m unittest discover -s tests -v
node --check web/app.js
uv run python3 -m jev_lab check
uv run python3 -m jev_lab eval --out runs/replay-evaluation.json
uv run python3 -m jev_lab compare --arms replay --cases S01 --out runs/compare-replay.json
uv run python3 -m jev_lab
```

The `compare` run above uses only the synthetic replay arm and needs no credentials. A live arm additionally requires `--mode live --allow-network`, a configured provider credential in the server environment, and user consent; see `docs/EVALUATION.md`.

For the container-style bridged browser test, install Playwright as development tooling only and adapt `executable_path` in `scripts/browser_check.py` to the available Chromium binary. A normal target-device browser run is preferred to that fallback.
