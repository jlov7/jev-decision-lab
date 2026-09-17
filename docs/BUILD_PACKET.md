# Jev Decision Lab — build and continuation packet

**Version 0.2 · September 17, 2026**

## 1. Product decision

Build **one reusable laboratory with several enterprise lenses**, rather than a collection of unrelated demos. The shared object is a decision receipt: source state, typed predictions, explicit policy, evidence gaps and the before-action boundary. Supplier exceptions, service incidents and consultancy deliverable review make the same mechanism legible to different colleagues.

The application is already implemented as a local Python service with a dependency-free browser interface. It is not a blank PRD. This packet specifies what exists, what was tested, and the exact next stages for Codex.

### Selection rationale

These are subjective design-fit scores against this brief—not measured user preference, product quality, market value or the frontier portfolio’s formal evidence ratings. Scores are 1–5. Weights: learning 25%, business relevance 25%, mechanism visibility 20%, falsifiability 20%, local feasibility 10%.

| Candidate | Learning | Relevance | Mechanism | Falsifiability | Feasibility | Weighted /5 |
|---|---:|---:|---:|---:|---:|---:|
| Generic chatbot with a Jev router | 2 | 3 | 2 | 2 | 5 | 2.55 |
| Game-playing showcase | 3 | 1 | 4 | 2 | 3 | 2.50 |
| Standalone knowledge-work linter | 4 | 5 | 4 | 4 | 5 | 4.35 |
| Static model-garden selector | 3 | 4 | 2 | 3 | 5 | 3.25 |
| Integrated decision laboratory | 5 | 4 | 5 | 5 | 4 | 4.65 |

The integrated option wins this design exercise because it includes the linter use case while teaching policy, uncertainty, source freshness, architecture and evaluation. Its principal risk is excess scope. Control that risk by keeping all v0.2 external effects disabled and treating the garden/audit views as deterministic learning aids, not new autonomous agents.

The recommendation would change if colleagues only needed document review, or an existing internal tool already offered the workbench. Then extract the domain pack and adapter instead of maintaining another interface.

## 2. Product requirement document

### Purpose

Help an engineer or enterprise leader understand, inspect and challenge the role of a bounded judgment model in a workflow. Provide a reusable, safe-to-run scaffold for the first live call and a subsequent matched evaluation.

### Primary users

**Frontier lead:** runs a five-minute demonstration, explains why this matters and where the claim stops. **Engineer:** inspects payloads, changes a rubric in code, examines failure behavior and adds a provider. **Domain owner:** recognizes an exception, judges whether the routing contract matches the work, and identifies the costliest errors. **Platform or risk reviewer:** traces data egress, credential placement, model versions and authority boundaries.

### Required outcomes

A learner must be able to explain why a valid typed answer can be wrong; distinguish a predicted probability from measured calibration; identify when more evidence is preferable to more reasoning; explain why a previous recommendation is not current authorization; identify a workload that does not need an LLM; and name one piece of evidence required before a production claim.

### Non-goals

No autonomous business transactions, no company/client uploads, no model-weight training, no general-purpose chat, no live provider comparison presented without a run, no hidden use of an API, no certification or professional judgment, and no claim that the chronology is the actual tracker’s operating history.

## 3. Implemented user journeys

### Journey A — the first five minutes

Open the app. The first visible banner states synthetic replay, authored probabilities and no Jev call. Select Supplier disruption and S02. Run six judgments. Inspect the ordinary on-time case despite its “delay” wording. Expand the owner distribution. Raise its decision threshold or mark the evidence stale, then replay only the policy. The route changes with zero additional model calls. Export a receipt.

**Acceptance:** the raw response stays identical during policy replay; the policy decision, timestamp and receipt hash change. An original-input hash remains traceable. No old model output is silently labeled as fresh inference.

### Journey B — the confident wrong answer

Run S04. The fixture suggests operations with a 0.98 top probability despite the independent teaching label naming quality. Open Learn & measure and evaluate the fixtures. Observe that raising a threshold does not necessarily remove the confident error.

**Acceptance:** every screen and report says these are authored outputs. The product is not blamed for an error that was planted by the demo author. Evaluation reads separate labels; provider requests never contain them.

### Journey C — immediately before action

Run a case that receives a team recommendation. Recheck the action simulation with all current-state boxes true. Then remove current approval and recheck. The result is held. A high predicted probability cannot override an expired or missing grant.

**Acceptance:** the simulation always reports zero external actions and zero new model calls. Missing values hold. Truthy strings are rejected. The prior decision must also permit a recommendation; checking every box cannot turn a prior human-review route into an authorized action.

### Journey D — connecting an account

Open Connect Jev, create a provider key in the console, place it only in the terminal environment, enable live mode and restart. In the UI select live, check consent and run one bundled case. Inspect provider identity, token usage and client-observed latency.

**Acceptance:** loading a page makes no provider request. No key is accepted by the browser. An unconfigured live route produces an explicit error. An HTTP failure never silently produces a synthetic answer. A model version mismatch blocks reuse of the old policy assumptions.

### Journey E — model-garden teaching

Choose calculation with cloud disabled. The worksheet recommends deterministic computation and marks hosted Jev as not indicated. Choose classification with hosted inference permitted: the worksheet names a comparison set, not a winning vendor. Mark high consequences: human authority is required.

**Acceptance:** this is deterministic role mapping with zero inference calls. Eligibility is explicitly not procurement approval. No unsupported model rankings or invented availability statistics appear.

### Journey F — frontier audit

Choose an as-of date before launch and inspect the dated antecedents and direct company signals. Change the date to September 17 to see the product/integration events appear. Inspect date-basis caveats and actual-ingestion UNKNOWN.

**Acceptance:** later artifacts cannot appear in an earlier date view. A date filter never claims historical crawler access, recall or promotion. The seven-stage funnel remains a research question until operating logs are connected.

## 4. Current file structure and interfaces

```text
jev_lab/
  engine.py       request construction, contract validation, policy and receipts
  provider.py     native TypeSafe HTTP transport, replay, explicit call budget
  metrics.py      owner accuracy, Brier, log loss, ECE, risk/coverage
  strategy.py     before-action simulation and model-garden role mapping
  experiments.py same-state batch/serial/parallel comparison
  adapters.py     provider arm interface: replay, native, gateway (mapping only)
  llm_arm.py      Claude constrained-output baseline arm (optional SDK extra)
  comparator.py   per-arm comparison; never pooled, never ranked
  showcase.py     live burst, playground request validation, compare wrapper
  server.py       loopback API, strict fields, receipt store, static assets
  __main__.py     serve/check/smoke/eval/bench/compare commands
web/
  index.html      semantic, accessible application structure
  app.js          UI state, fetch calls, inspection and export
  style.css       desktop/mobile design system
scripts/
  seed_cases.py   reproducible authored data and separate gold labels
  seed_signals.py curated chronology with publication-basis caveats
  source_register.py bibliography metadata, no copied article corpus
  browser_check.py development QA (see environment caveat)
data/
  cases.json      synthetic input state and deterministic teaching facts
  packs.json      versioned task descriptions and allowed options
  replay.json     explicitly authored probability fixtures
  labels.json     separate evaluator-only teaching labels
  signals.json    retrospective public chronology, ingestion UNKNOWN
```

The versioned seed scripts are the source of truth for generated data. Run `python3 scripts/setup_lab.py` after cloning; the downloadable bundle also includes their generated outputs. This avoids maintaining duplicated fixture text as separate authority.

Runtime requires Python 3.10+ and its standard library. No npm install, framework build, model download or GPU is required. The browser uses local assets only. Playwright is optional development tooling, not a runtime dependency. The current tests were executed with Python 3.13; other supported interpreter versions remain to be exercised on the target machine.

Important callable interfaces:

```python
engine.request_for(case: dict) -> dict
engine.validate(request: dict, response: dict, live: bool = False) -> dict
engine.decide(case: dict, response: dict, threshold: float = .85,
              variant: str = 'original') -> dict
engine.run(case_id: str, mode: str = 'replay', threshold: float = .85,
           consent: bool = False) -> dict
engine.reconsider(receipt: dict, threshold: float,
                  variant: str = 'original') -> dict
engine.verify_receipt(receipt: dict) -> None
provider.live(payload: dict) -> tuple[dict, dict]
strategy.action_preview(receipt: dict, current: dict) -> dict
strategy.garden(task: str, allow_cloud: bool, consequence_high: bool) -> dict
metrics.evaluate(receipts: list[dict], labels: dict) -> dict
experiments.benchmark(case_id: str = 'S02', repeats: int = 1) -> dict
```

### HTTP contract

GET `/api/config` returns local mode configuration and a random same-session token, never the provider key. GET `/api/cases` returns bundled inputs and rubrics. GET `/api/signals` returns the curated chronology. Static asset paths are allowlisted.

All POST routes require same-origin checks, a session token in `X-Lab-Token`, JSON and at most 16,384 body bytes. Unknown body fields are rejected.

| Endpoint | Allowed body fields | Important boundary |
|---|---|---|
| `/api/run` | `case_id`, `mode`, `threshold`, `consent` | No arbitrary state or key field accepted |
| `/api/reconsider` | `receipt_id`, `threshold`, `variant` | Uses a server-held receipt, not a client-asserted result |
| `/api/action-preview` | `receipt_id`, `current` | Simulation only; no effect adapter |
| `/api/garden` | `task`, `allow_cloud`, `consequence_high` | No model call |
| `/api/evaluate` | none | Always authored replay; live evaluation is explicit CLI work |
| `/api/burst` | `mode`, `consent`, `case_ids`, `threshold` | Concurrent run over bundled cases; attempt cap checked before any call |
| `/api/playground` | `state`, `questions`, `consent` | User-typed synthetic text; live only; shape and size validated; nothing stored |
| `/api/compare` | `arms`, `case_ids`, `consent` | Per-arm report plus teaching labels; live arms need consent |

Receipts are stored only in process memory, capped at 200 and lost on restart. Exported files are user-controlled. This is intentional for a personal teaching tool; a production evidence store requires a separate retention and access design.

## 5. Native provider contract and invariants

The endpoint is fixed to TypeSafe’s native HTTPS service. Redirection is disabled so a bearer token is not forwarded to an unexpected host. The adapter does not use environment proxies; an approved enterprise deployment must explicitly design its proxy/egress behavior rather than copy this personal-lab choice silently.

The default model is `jev-1.13.0`. Responses must contain an identity, all and only the requested question IDs, correctly typed answers and nonnegative integer usage counts. Probabilities must use the exact option set, be finite and within [0,1], and sum to one within a small declared tolerance. The selected choice must be a maximum-probability option. Score means and legends are cross-checked. Missing fields are not invented.

A 16,000-byte outbound ceiling and a 20-attempt process cap limit accidental spending. These are **lab guardrails**, not vendor context limits or dollar guarantees. Attempts are reserved before sending and are never refunded on a timeout, because the request might already have been processed. There are no automatic retries. The user deliberately retries after inspecting a failure.

### Policy precedence

The first matching rule applies: source trust, source freshness, mandatory human review, critical-severity tail, material contradiction, evidence insufficiency, uncertain/other owner, then team recommendation. The thresholds .30, .50, .75 and .85 are teaching configuration, not empirically calibrated production limits. Cross-head inconsistency—evidence needed but selector says none—forces human review.

A useful later refinement is a domain-specific distinction between *stopping an action* and *alerting a human*. The current prototype is a recommendation workbench, not an emergency response system; a real safety-relevant workflow must not suppress an urgent alert simply because its evidence is unverified.

### Receipt semantics

A receipt binds the request, response, model/provenance, state facts, question version, policy source hash, policy result and timestamps. Policy replay records a parent receipt hash and zero new model calls. The hash is an integrity comparison, not a signature, execution attestation or proof that an event was never omitted. Do not market it as non-repudiation.

## 6. UI and UX specification

Use a white background, dark readable text and restrained teal accents. The app should look like an engineering workbench, not a marketing landing page. The critical hierarchy is source → judgments → policy → current action boundary. Keep replay/live provenance permanently visible.

The desktop view uses a left case queue, central evidence and right recommendation; lower sections contain distributions and policy. On narrow screens these become one readable column, with horizontally scrollable scenario choices but no document-level overflow. All inputs have visible labels; semantic headings, details/summary and meter controls support basic accessibility. Keyboard focus is explicit. Reduced-motion preferences are respected.

Do not add green “verified” badges to predicted judgments. Use verbs that match actual capabilities: recommend, hold, request evidence, inspect and simulate. When a live request fails, preserve any previous result only with an explicit message that it is old. Changing selected case clears the result. A receipt download is available only after a run.

The signal view must show date certainty and UNKNOWN ingestion. The garden must say that its output is an authored capability mapping, not model selection backed by benchmarks. No decorative dashboard metrics or invented savings should be added.

## 7. Build phases for Codex

### Phase 0 — reproduce the shipped local boundary

Read `README.md`, `AGENTS.md`, this packet and `QA.md`. Run `python3 scripts/setup_lab.py` to regenerate authored datasets and source metadata, then unit tests, JS syntax and offline validation. Open the actual server in a normal target-device browser and exercise every tab. The container’s managed Chromium blocked direct loopback navigation, so retained visual tests used local rendering bridged to the actual HTTP service. **Real browser-network/CSP integration is a target-device verification item, not already proven.**

Acceptance: no browser errors; exact same-origin API behavior; receipt export works; 390px and laptop layouts remain readable; live-disabled behavior never silently becomes replay.

### Phase 1 — one authenticated native smoke test

Use only a bundled synthetic case. The user supplies a key through the terminal environment. Run `python3 -m jev_lab smoke --mode live --allow-network --out runs/first-live.json`. Stop on the first failure. Compare the actual response to the documented wire schema, including returned model identity, Score probabilities/legend and usage.

Acceptance: an authentic response with recorded provenance, or a safely retained failure. Do not “fix” a schema mismatch by fabricating a missing distribution. Determine whether the docs, adapter or entitlement is wrong. No performance claim follows from one case.

### Phase 2 — request-shape experiment

Run one batched six-question request, six serial requests and six concurrent requests on the same state. The CLI uses 13 attempts per repetition and shuffles order. Three repetitions need 39 attempt slots. Keep every failure and partial-cost caveat.

Acceptance: all request payloads and responses retained, total tokens and client wall time reported, no inference of accuracy from latency, and no claim that this is a comparison with another provider.

### Phase 3 — fair provider comparison

Add provider adapters behind an explicit interface that returns both raw response and normalized predictions, along with model/configuration/usage/latency. Do not force every provider to generate a long explanation when the task needs only a category. Define two tracks: minimal actionable answer, and full comparable distributions. Report them separately.

Candidate arms: tuned deterministic baseline; an appropriate local zero-shot classifier; a cheap constrained-output generative model; Jev; and a stronger reasoning model. Include the always-escalate baseline when measuring operational loss. Use exact provider versions and dated prices. No adapter should be enabled by merely opening the page.

Acceptance: matched input evidence; tuning and final evaluation separated; all failures retained; parser failures count; label source independent of predictions. See `EVALUATION.md` before implementing a leaderboard.

### Phase 4 — real confidence engineering

Add reviewer-owned calibration artifacts keyed by model, question hash, dataset split and domain. Display selective error and coverage, reliability bins and costly-error counts. Separate uncalibrated raw probabilities from any post-hoc transform. Choose thresholds on validation data, then freeze them before the final test.

Acceptance: no hidden test labels reach a model or rubric optimizer; no repeated-case inflation; rejected and accepted paths both sampled; drift invalidates the calibration artifact instead of silently retaining its badge.

### Phase 5 — narrowly scoped incumbent integration

Choose one existing pod with a clear contract: for example, narrative checks after a financial validator or evidence sufficiency before case routing. Integrate the judgment adapter, not the entire lab UI. Reuse existing source-access controls, calculators, evidence stores and effect gateways. Operate in read-only shadow mode first.

Acceptance: a domain owner defines costly misses and review capacity; the control arm remains observable; full accepted-outcome cost is lower or quality improves at an acceptable cost; stopping criteria are honored. No client data or external effects before approval.

### Phase 6 — optional Vercel adapter

The alternate Gateway interface is documented, not part of the implemented native adapter. Use the actual AI SDK evaluation-model interface, pin its package version, map `boolean` versus `noul` and preserve provider-specific confidence metadata. Confirm the route’s privacy controls and logging behavior under the relevant agreement. Do not assume native response normalization applies unchanged. [S11]

Acceptance: contract tests against real route responses, documented provenance and provider options, no inferred privacy guarantee from a UI toggle alone.

## 8. Failure modes and required checks

| Failure | Current treatment | Required next-stage test |
|---|---|---|
| Wrong but confident answer | Deliberately demonstrated in S04 | Independently labeled shifted and adversarial examples |
| Out-of-menu reality | `other` route requires review | New domain/class, mixed and ambiguous cases |
| Conflicting question heads | Evidence-needed/none conflict holds | Contradictory owner, issue and consequence combinations |
| Prompt injection in source | Source marked untrusted; no authority granted | Paraphrased and obfuscated attacks, not one fixture |
| Stale evidence | Deterministic hold | Timestamp sources, clock skew, changed state after judgment |
| Expired or missing authority | Before-action simulation holds | Real signed grants, revocation, separation of duties |
| Schema drift/model change | Strict validation blocks | Actual provider migrations and alias changes |
| Timeout/rate limit | Explicit failure; no automatic retry | Account quotas, Retry-After, billing ambiguity |
| Review overload | Discussed but not modeled as a live queue | Service-level and capacity analysis |
| Leaked gold labels | Separate files and request tests | Data-loader and optimization boundary review |
| Fake benchmark win | Replay clearly labeled; no competitor numbers generated | Frozen matching and predeclared metrics |
| Forged receipt | Hash and server receipt ID checks | Signed storage, access control, completeness audit |
| Browser egress/key exposure | No key input and strict endpoints | Normal-browser CSP/network test on target device |

## 9. Release gates

The local teaching release is acceptable when tests and source review pass and limitations are visible. A live smoke release requires an authenticated contract check. A benchmark release requires a frozen protocol and independent labels. A client shadow release requires rights, procurement and a domain owner. An effectful release requires a separate authority/effect/recovery design.

These are different gates. A green unit suite cannot promote the application directly to client deployment. A successful provider request cannot validate the business thesis.
