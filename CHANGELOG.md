# Changelog

## 0.6.0 · 20 September 2026

- Add intent-led Start, an offline three-step lesson and a teach-back export.
- Add Decision Studio: eight source-linked judgment patterns, sixteen routine/adverse request previews, explicit-consent live observations and `UNRUN` study designs.
- Add assumption-only economics with all-attempt model cost, imperfect human review, residual-error loss, capacity and sensitivity.
- Preserve known failed-response costs across native, Anthropic, OpenAI and Claude Code paths; keep unknowns and billing bases distinct. Reject nonzero CLI exits even when a success-shaped envelope is present.
- Refuse mixed-model/question-contract calibration and false stability from incomplete probes. Scope descriptive variation by input/model; compare ablation against the same owner label without causal claims.
- Add common-answered-subset comparison alongside failure-inclusive denominators. Keep the planted S04 exclusion specific to authored replay.
- Make probe/ablation and experiment-snapshot exports self-contained and explicit about their coverage.
- Add UI accounting tests and real-navigation CI browser checks; fix the source generator that erased the dated September 18 live-evidence note.
- Preserve historical owner observations unchanged; record the interrupted-upload recovery and outstanding independent evaluation gates.


Dates are 2026. Versions follow the `lab_version` shown in the app header.

## 0.5.0 · 18 September

- Three generative baseline arms sharing one schema and one strict normaliser: Claude through the user's signed-in `claude` command (subscription-billed), Claude through an Anthropic API key, and OpenAI chat completions with a strict JSON schema.
- Full four-arm live compare recorded. Score tolerance widened to two rounding steps per level after one refused answer; refused answers inside compare now keep their response and cost.
- Session report export: one self-contained HTML file of everything the tab has seen.
- Repository prepared for public release: licence, security and contributing notes, internal planning documents removed.

## 0.4.0 · 18 September

- Paste-your-key Connect screen with an in-memory key, a Forget button and a terminal key that takes precedence.
- One-command start: `uv run jev-lab` rebuilds the datasets on first run.
- Experiments: stability probe and evidence ablation, with a noise floor measured by probing the same case.
- Plain-English README opening, `docs/START_HERE.md`, first-visit panel.

## 0.3.x · 17 to 18 September

- Live lab: burst, playground and compare. Claude comparison arm through the Anthropic SDK. Keyword-rules teaching arm. Prepaid attempt holds. Strict policy variant. Receipt endpoint.
- First authenticated calls. Validator tolerances derived from the provider's two-decimal rounding. Refused answers retained with their cost.

## 0.2 · 17 September

- Workbench, before-action simulation, model garden, signal audit, learn and measure. Twelve authored cases in three packs. Replay fixtures with one planted confident-wrong case.
