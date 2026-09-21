# v0.6 recovery verification · 20 September 2026

This section is current for the upgrade. Older records below remain historical. Repository CI artifacts, not this paragraph, establish the result of any later commit.

## Local evidence

- Python 3.13.5: **259 tests passed**, including provider refusals, malformed outputs, incomplete probes, mixed versions, paired denominators, offline Studio requests, economics bounds/capacity, export custody and source-register regeneration.
- Node 22.16: **7 JavaScript tests passed**; each of the five browser JavaScript files passed a separate syntax check.
- Ruff 0.16.8: all configured lint checks passed. Twelve original teaching case contracts validated offline.
- Chromium/Playwright 1.57.0: all seven surfaces exercised at 1440×1100 and 375×812, including all sixteen Studio previews, lesson/teach-back downloads, comparison/probe/ablation snapshots, economics, keyboard navigation, phone pattern selection, and retained malformed transport-mock responses.

The local managed browser blocks real loopback navigation with `net::ERR_BLOCKED_BY_ADMINISTRATOR`. The explicit local `--bridge` run renders the real assets and calls the actual Python HTTP server, but **does not verify browser-network or CSP integration**. The CI browser job uses direct navigation with no bridge, checks actual CSP headers, and retains `browser-report.json` and screenshots. Inspect that job's result before merging. No policy was disabled to work around the local browser restriction.

The browser loop found and repaired an incorrect Studio answer-renderer invocation and populated Live lab mobile overflow. Test-code selector/hidden-detail reading errors were repaired as test errors, not counted as product defects. The runtime test fixture labels every simulated provider response `transport_mock`; these outputs are not Jev evidence.

## Reproduce

```bash
uv run python3 scripts/setup_lab.py
uv run python3 -m unittest discover -s tests -v
uv run python3 -m jev_lab check
node --test tests/evidence.test.cjs
for file in web/*.js; do node --check "$file"; done
ruff check jev_lab tests scripts
python3 -m scripts.browser_check --output-dir runs/browser
```

The recovery container ran Python commands with `uv run --no-project python3` to use its existing offline interpreter and tooling. This does not claim that a fresh `uv` package build was tested there. The CI matrix tests Ubuntu Python 3.10/3.13 and macOS Python 3.13. Browser evidence is Chromium-only; Safari, Firefox, Windows, real touch hardware and screen-reader behavior remain unverified.

## Remaining evidence limits

No new authenticated provider call, independent multi-agent review, human usability study, held-out domain benchmark or production security assessment was performed. Existing September 18 owner observations are unchanged. Local self-review cannot establish the requested independent 90+ standard in every category; see [the rubric](review/RUBRIC.md). A PR proposes code for review; it is not a deployment or public-release approval.

---

# Historical verification records

# Verification record

What has been checked, how, and what has not. Dates are 2026. Every live figure below is in a file under `evidence/`.

## How the suite is run

```bash
uv run python3 -m unittest discover -s tests -v    # 219 tests, about two seconds
uv run --with ruff ruff check jev_lab tests scripts
uv run jev-lab check                                # twelve fixtures validate, policy runs, no network
node --check web/app.js web/live.js web/report.js
```

CI runs the same steps on Python 3.10 and 3.13 on every push. The verbose log of the last local run is `evidence/unit-final.txt`.

## What the tests establish

| Area | Established |
|---|---|
| Contract | Question ids and types must match exactly; probabilities finite, in range and summing to one within the provider's two-decimal rounding; the chosen option is the argmax; a score matches the weighted level index within two rounding steps per level; legends match; usage counts are non-negative integers; a pinned model mismatch is refused; nothing missing is invented |
| Policy | Every rule and its precedence; stale, unverified and strict variants; the issue/owner consistency check; reconsideration makes zero model calls; the critical level is the top declared level whatever the scale |
| Receipts | Tampering with any field is detected; forged receipt ids are refused |
| Server | Cross-origin and missing-token requests get 403; unknown fields are refused; path traversal fails; oversized bodies are refused; the key never appears in config, in error bodies or in the failure log line |
| Connect | A pasted key enables live mode, is redacted from errors, shows only its last four characters, and is forgotten on request; a terminal key takes precedence and disables pasting; malformed keys are refused without being stored |
| Provider | Live disabled by default; consent required; per-process attempt cap with atomic holds; redirects blocked; HTTP errors mapped without retry; timeouts leave billing unknown; a refused answer keeps its raw response and cost |
| Arms and comparator | The two tracks are kept apart; arms are never pooled; unavailable is never zero; every failure is retained; the Gateway arm refuses without a transport; the live warning states whether authenticated calls were made |
| Generative baselines | Strict schema, prompt without labels, refusal and truncation fail closed, out-of-vocabulary answers refused, dated prices, key redaction; the Claude-subscription arm runs an argument list with tools disallowed and reports the CLI's own error text |
| Experiments | Probe holds slots before sending, reports per-option spread and route counts, and records the measured range; ablation runs edited copies and leaves the original untouched, marks movement under the noise floor as noise, and prefers a probe-measured floor for the same case |

## Real-browser checks

Run in a desktop browser against the loopback server, at desktop width and at 375 px.

| Date | Checked | Result |
|---|---|---|
| 17 Sep | Four tabs, receipt export, replay policy, before-action hold, 390 px layout | Passed. One cosmetic favicon 404, since fixed |
| 17 Sep | Live lab first build | A Content Security Policy violation from inline styles; fixed by moving styles to CSS and setting widths through the CSSOM. Zero inline style attributes since |
| 18 Sep | Strict policy variant, burst row click-through, compare with the rules arm, planted-error labelling | Passed, no console errors |
| 18 Sep | Teaching note shown only after a run; connect and forget flow; first-visit panel; experiments in replay; compare controls for three baselines | Passed, no console errors, no overflow at 375 px |
| 18 Sep | Session report built from live results, opened standalone from disk | Four sections, no external references, no session token, no console errors |

## Live runs on a TypeSafe account

All on 18 September, on the account owner's key, with per-run consent. Total spend about a third of a cent.

| Time (UTC) | Run | Result |
|---|---|---|
| 15:53 | Burst 1, twelve cases | 11 validated. S02 refused: a five-option distribution summed to more than 1.002 because the provider rounds to two decimals. p50 343 ms, p95 512 ms, about $0.0005 |
| 15:55 | Playground, one free-form incident | Outage 0.99, operations 0.93, next evidence telemetry, 368 ms |
| 16:05 | Burst 2, after the tolerance fix | 12 of 12 validated. p50 327 ms, p95 464 ms. Owner agreement with the labels 11 of 12 (Q02 "other"). Run-to-run drift over eleven common cases: top-owner probability within 0.03; one route flipped on Q02 because the next-evidence head changed |
| 16:10 to 16:25 | Four-case compares, three runs | Same owners each time. The rules arm fires "delivery" on S02's delay wording and gives up on T03 |
| 16:51 | Probe S02 ×8, S04 ×8; ablation S02, S04 | S02 owner 0.65–0.73, route stable 8 of 8; S04 owner quality 1.00 ×8. Removing S04's inspection excerpt moved sufficiency 0.35 → 0.22; removing the carrier note moved nothing. The default 0.03 noise floor was too tight for S02 (measured 0.08), so ablation now uses a probe-measured floor when one exists |
| 17:20 | Full four-arm compare on twelve cases | Jev 11 of 12 (T04 refused once on score versus weighted index; a re-run passed at 0.02), Claude subscription 12 of 12 at p50 26 s, replay and rules 12 of 12. Claude answered "sufficient: yes" on all twelve where Jev ranged 0.11 to 0.47 |

Evidence files: `first-live-2026-09-18.json`, `live-2026-09-18-run2.json`, `compare-live-2026-09-18.json`, `compare-live-2026-09-18-run2.json`, `experiments-live-2026-09-18.json`, `compare-claude-code-2026-09-18.json`, `compare-full-2026-09-18.json`.

## What the live runs changed in the code

- Validator tolerances derived from two-decimal rounding: one step per option for the sum, two per level for the weighted score.
- A live answer that fails validation is kept with its raw response, latency, usage and cost, in bursts, in compares and on the workbench.
- The native arm reports `live_verified`; the compare warning says whether authenticated calls were made.
- Ablation uses the widest range a live probe of the same case measured in that process, when larger than the default floor.
- The `claude` command's minimal mode skips sign-in, so the subscription arm does not use it.

## Not established

- Anything about accuracy. Twelve authored cases are a smoke test.
- The Anthropic and OpenAI API-key arms on a real account. They are tested against fake transports only.
- The Vercel AI Gateway arm. Its route is TypeScript-only; the arm is a documented mapping that refuses without a transport.
- Calibration. That needs independently labelled held-out cases, as [EVALUATION.md](EVALUATION.md) sets out.
