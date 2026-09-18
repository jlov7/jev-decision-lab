# Notes for coding agents

Read `README.md`, `docs/DESIGN.md` and `docs/EVALUATION.md` before changing anything.

Invariants that must survive every change:

- Replay probabilities are authored. Never present them as measured model output, and never fabricate live results, latency, cost, calibration or authorisation.
- No key in a prompt, browser page, file, log or commit. Keys live in the server process only, pasted or from the terminal. Live calls need consent, a free attempt slot, no retries and no replay fallback.
- Provider payloads carry state and questions only. Labels, expected routes, teaching notes and policy facts never leave the server. A test enforces this.
- Responses are validated strictly and refused answers are retained, never patched.
- Policy decides in code. A probability cannot grant permission.
- Loopback only. No telemetry, no third-party assets, no company or client data in fixtures or examples.

Write the failing test first. Run the full suite, lint and the JavaScript syntax check before committing. Keep `docs/QA.md` honest about what was and was not verified. Use `uv run python3`; the project has no other package manager.
