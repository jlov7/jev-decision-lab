# Design contract

Version 0.6 · 20 September 2026 · A teaching and evaluation prototype, not production software.

## Goal

Show engineers and leaders what a bounded, probabilistic judgment model contributes to a real workflow, and what it does not. Every screen keeps four things visibly apart: the model's opinion, the evidence it had, the policy decision made in code, and the permission to act.

## What it is

One local application, one process, no build step. Twelve authored synthetic cases in three enterprise packs (supplier disruption, service incidents, deliverable review) share six typed questions, a policy trace and a receipt format. Replay mode teaches the mechanics offline from authored fixtures. Live mode calls Jev on the user's own key after per-run consent.

Surfaces:

- Start: intent-led onboarding, an offline three-step lesson and a teach-back record.
- Decision Studio: eight versioned patterns with sixteen synthetic situations, exact request preview, optional explicit-consent live observation, unrun study designs and assumption-only workflow economics.

Existing surfaces:

1. Workbench: pick a case, run six judgments, inspect distributions, replay the policy under different facts with no new call, export a receipt.
2. Before action: change simulated authority or freshness, recheck without a model call, watch the action hold.
3. Live lab: burst all twelve cases, ask Jev about text you wrote, compare Jev with generative baselines and a keyword rule, probe one case repeatedly, remove evidence one excerpt at a time, export a session report.
4. Model garden: a deterministic worksheet on which kind of capability a task needs.
5. Signal audit: a dated chronology of public signals before the launch.
6. Learn and measure: the three primitives, the planted confident-wrong case, and calibration metrics over the fixtures.

## Invariants

- Only authored synthetic records, or text the user typed after consent, ever reach a provider.
- Replay output is never presented as measured model output. The global banner describes the local lab; each result states its own mode. A previous workbench receipt cannot label another surface.
- Live calls need a key in the server process (pasted or from the terminal), the consent box, and a free attempt slot. Nothing retries. Nothing falls back to replay.
- Provider payloads never contain labels, expected routes, teaching notes or policy facts. A test enforces this.
- Responses are validated strictly. A response that breaks the contract is refused and retained with its cost; nothing is invented to fill a gap.
- Policy decides the route in code. A probability cannot grant permission. Before any simulated action, authority and freshness are rechecked without the model.
- Receipts record request, response, versions and decision under a content hash. A hash proves integrity, not truth.
- The server binds to loopback only, allows an explicit field set per endpoint, and sends a strict Content Security Policy. No telemetry, no third-party assets.
- Arms in a comparison are reported side by side, never pooled or ranked. A distribution a provider did not return is unavailable, not zero.

## Non-goals

Not a benchmark, not a production control system, not a channel for company or client data, not a claim about Jev's accuracy. Not a game, not a generic classifier dashboard, not an autonomous process.

## Acceptance

Unit, transport-mock and loopback HTTP tests; a JavaScript syntax check; lint; a real-browser interaction pass at desktop and phone widths. No live claim without a recorded live receipt. See [QA.md](QA.md) for the verification record and [EVALUATION.md](EVALUATION.md) for what a real evaluation would need.
