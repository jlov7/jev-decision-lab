# Changelog

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
