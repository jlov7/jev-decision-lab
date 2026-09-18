# Verification record and remaining risk

**Build date: September 17, 2026. Local prototype version: 0.3.1.**

## Executed

| Check | Result | Evidence |
|---|---|---|
| Python unit, policy, metrics, adapter, comparator, showcase, Claude arm, CLI, mock transport and real loopback HTTP tests | 179 tests passed, no skipped tests in the final run | `evidence/unit-final.txt` |
| Provider adapter interface and per-arm comparator | Two-track interface, public contract distinction between `boolean` and `noul`, provenance separation, retained failures and unavailable-not-zero reporting all pass | `tests/test_adapters.py`, `tests/test_comparator.py` |
| `compare` command and its live gate | Live arms are refused unless `--mode live` and `--allow-network` are both set; an unconsented arm makes no call, and a consented arm's own failure is retained verbatim | `tests/test_cli_compare.py` |
| Authored data generation | Rebuilt offline from versioned scripts | `scripts/setup_lab.py` |
| All twelve replay contracts and policy runs | Passed | `uv run python3 -m jev_lab check` |
| JavaScript syntax | Passed | `node --check web/app.js web/live.js` |
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

## Version 0.3.1 review (Grok changes) — verified in a real browser

| Check | Result |
|---|---|
| Suite and CI | 179 tests pass locally; CI green on Python 3.10 and 3.13 |
| Strict policy variant | S04 default route Recommend a team; switching to *Hold on issue/owner disagreement* and replaying gives Human review with 0 new model calls |
| Burst row click-through | Replay burst renders 12 inspectable rows; clicking S02 opens its stored receipt on the workbench via `/api/receipt` |
| Compare with rules arm | Replay and rules arms render side by side; S04 marked as planted and excluded from agreement; rules arm shows the S02 delay trap (operations · delivery) |
| Browser hygiene | No console errors, zero inline `style` attributes under the CSP, no horizontal overflow at 375px |
| Prepaid holds | Unit tests cover atomic reservation, no double counting, and refusal before any send when slots are short; not exercised live |

Still not executed: any authenticated Jev or Claude call.

## Version 0.3.2 follow-ups (OpenCode review) — verified in a real browser

| Check | Result |
|---|---|
| Teaching note timing | Selecting S04 shows no teaching note; after *Run six judgments* the note and planted-error tag appear; switching to S02 clears it. Predict-first workshop exercise restored. `/api/cases` still carries the note for evaluators |
| Severity top level | `decide()` reads the highest declared level instead of the literal key `3`; regression test covers 3- and 5-level severity scales. Route results on the twelve cases unchanged |
| Live gate order | With no key, `run` and `burst` now report *Live mode disabled* before asking for consent, matching the playground |
| Suite | 181 tests pass; no console errors; zero inline `style` attributes |

## First live run — 18 September 2026, real account, real browser

| Check | Result |
|---|---|
| Burst, twelve cases, live | 11 validated, 1 refused by the validator (S02: five-option distribution summed to more than 1.002 because the provider rounds to two decimals). Model `jev-1.13.0` echoed on all answers. p50 343 ms, p95 512 ms, wall 938 ms, 11,902 input tokens, about $0.0005 |
| Playground, live | One free-form synthetic incident (badge readers rejecting cards after a deploy) answered: outage 0.99, operations 0.93, severity 1.2, next evidence telemetry. 1,018 input tokens, 368 ms |
| Owner agreement | 10 of 11 validated cases matched the teaching label. S04 live answer was quality at 1.00 (the fixture plants operations). Q02 owner split other 0.56 / assurance 0.36, held for a person |
| Follow-up fixes | Validator tolerances derived from two-decimal rounding; live answers that fail validation are retained with raw response, usage and cost; server prints one structured stderr line per failed request; workbench and burst rows show the retained answer |
| Burst 2, after the validator fix | 12 of 12 validated. p50 327 ms, p95 464 ms, wall 802 ms, 12,977 input tokens, about $0.00055. Owner agreement 11 of 12 (Q02 again "other"). Run-to-run drift across eleven common cases: top-owner probability within 0.03, severity within 0.05; Q02 route moved from Human review to Repair the evidence because the next-evidence head changed from "none" to a named type |
| Compare, live, four cases | Native Jev beside replay and keyword rules on S02, S04, T03, Q02. Rules fired "delivery" on S02's delay wording and "other" on T03; Jev answered routine 0.72 and outage. Native arm now reports `live_verified: true`; the compare warning states that authenticated calls were made instead of denying it |
| Compare, live, after restart on fef9726 | Two more four-case compares on the restarted server (one from the browser pane, one end to end in headless Chromium). Same owners every time: S02 operations, S04 quality, T03 operations, Q02 other. Footer now reads "came from authenticated calls"; native arm `live_verified: true`. Zero console errors. Second report saved as `evidence/compare-live-2026-09-18-run2.json` |
| Screenshots | `docs/images/live-burst.png` is rendered from the saved burst 2 evidence through the current UI code without new calls. `docs/images/compare.png` is a direct capture of the live server on fef9726 during the headless compare above |
| Attempt cap lesson | The Live lab compare button always runs all twelve cases, so one compare plus one burst exhausts the 20-slot default. A browser-automation crash mid-request still consumed its twelve slots server-side. Raise `JEV_MAX_LIVE_CALLS` for longer sessions |
| Evidence | `evidence/first-live-2026-09-18.json`, `evidence/live-2026-09-18-run2.json` and `evidence/compare-live-2026-09-18.json` hold the summaries and receipts. No credential appears in them |

## Phase 1 onboarding (0.4) — verified in a real browser

| Check | Result |
|---|---|
| One-command start | Fresh `git clone` into a scratch directory, then `uv run jev-lab check`: datasets rebuilt on first run, 12 cases validate. No manual setup step |
| Paste-a-key connect | Fake key pasted in the Connect screen on an offline scratch server: header shows *Connected · ····CDEF*, Live lab flips to *Live · jev-1.13.0*, burst mode defaults to live, paste field cleared, Forget returns everything to offline. No console errors, zero inline styles, no overflow at 375px |
| Key never leaves the process | `/api/config` carries only `key_source` and the last four characters; tests assert the key string is absent from config, from error bodies and from the failure log line (which prints "rejected" for `/api/connect`). Terminal key takes precedence and disables the paste box |
| Suite | 193 tests |

## Phase 2 experiments (0.4) — verified in a real browser, replay mode

| Check | Result |
|---|---|
| Stability probe | Replay probe on S02 with 6 repeats renders six question blocks and twenty range rows, route "Recommend a team in 6 of 6", widest range 0.00, replay warning shown, export enabled. Unit tests with a wobbling live stand-in report a 0.02 owner range, hold all slots before sending, refuse without consent or slots |
| Evidence ablation | Replay ablation on S02 renders baseline plus two variants, replay warning shown. Unit tests confirm variants are edited copies (original case untouched, different case hash), deltas below the 0.03 noise floor are marked noise, a 0.20 drop in sufficiency is marked above noise |
| Suite | 201 tests, three consecutive runs green (the fixture counter is lock-protected because the probe runs concurrently) |
| Live run, 16:51 UTC | Server restarted with `JEV_MAX_LIVE_CALLS=100`. Probe S02 ×8: owner operations 0.65–0.73, route stable 8 of 8, p50 326 ms, about 0.036 cents. Probe S04 ×8: owner quality 1.00 ×8, widest range 0.06 on next evidence. Ablation S04: removing the inspection excerpt moved sufficiency 0.35 → 0.22 (above noise), removing the carrier note moved nothing. Ablation S02: both excerpts moved sufficiency by about 0.08. 22 attempts, zero console errors. Saved to `evidence/experiments-live-2026-09-18.json`; `docs/images/experiments.png` rendered from that file through the current UI |
| Refinement from the live data | S02's measured range (0.08) exceeded the default 0.03 floor, so ablation now uses the widest range a live probe of the same case has measured in this process when larger, and reports the source. Test covers the switch and that other cases keep the default |

## Phase 3 plain English (0.4) — verified in a real browser

| Check | Result |
|---|---|
| First-visit panel | Shows on a fresh visit, hides on *Got it*, stays hidden after reload via a guarded localStorage flag; page still works when storage is unavailable |
| Copy pass | README opening and plain-English section rewritten for a first-time reader; `docs/START_HERE.md` added as the one page to hand someone; no em dashes remain in README, START_HERE or the app |

## Phase 4 session report (0.4) — verified with headless Chromium on current code

| Check | Result |
|---|---|
| Builder | `buildSessionReport()` run in the real app with the saved burst 2, probe S02, ablation S04 and compare run 2 loaded: 13 KB, four sections, zero external references, session token absent, no key-like strings |
| Standalone render | The exported file opened from disk with no console errors and no failed requests; screenshot at `docs/images/session-report.png`; example committed as `docs/example-session-report.html` |
| Not yet executed | Clicking the button in the desktop browser pane, which triggers a file download the pane does not expose. The live server process predates `report.js` in its static allow-list and needs a restart to serve it |

## Generative baselines (0.5) — one live run through the Claude subscription

| Check | Result |
|---|---|
| Claude subscription arm | `claude -p` with `--json-schema`, tools disallowed, no session persistence. First attempt with `--bare` failed as "Not logged in" because minimal mode skips sign-in; removed. Then S02 → routine/operations, S04 → quality/quality, about 28 s per call, billed to the subscription, structured output parsed from the envelope. Report saved as `evidence/compare-claude-code-2026-09-18.json` |
| OpenAI and Anthropic API arms | Unit-tested against fake transports (strict schema, refusal, truncation, redaction, dated prices); not called live on this account |
| Budget | All three generative arms share `JEV_MAX_COMPARE_CALLS`; prepare_arms refuses before sending when the pool cannot cover every arm |
| Suite | 218 tests |

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
node --check web/app.js web/live.js
uv run python3 -m jev_lab check
uv run python3 -m jev_lab eval --out runs/replay-evaluation.json
uv run python3 -m jev_lab compare --arms replay --cases S01 --out runs/compare-replay.json
uv run python3 -m jev_lab
```

The `compare` run above uses only the synthetic replay arm and needs no credentials. A live arm additionally requires `--mode live --allow-network`, a configured provider credential in the server environment, and user consent; see `docs/EVALUATION.md`.

For the container-style bridged browser test, install Playwright as development tooling only and adapt `executable_path` in `scripts/browser_check.py` to the available Chromium binary. A normal target-device browser run is preferred to that fallback.
