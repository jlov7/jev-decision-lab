# Contributing

Thanks for looking. This is a small project with a clear shape, so contributions that keep that shape are the easiest to take.

## Setting up

```bash
git clone https://github.com/jlov7/jev-decision-lab.git
cd jev-decision-lab
uv run python3 -m unittest discover -s tests -v
uv run --with ruff ruff check jev_lab tests scripts
node --check web/app.js web/live.js web/report.js
uv run jev-lab
```

Python 3.10 or newer. The application itself has no dependencies; the Anthropic SDK is an optional extra for one comparison arm.

## What keeps the shape

Read [docs/DESIGN.md](docs/DESIGN.md) first. The invariants there are not up for negotiation in a pull request: authored fixtures are never called measured output, keys never leave the server process, provider payloads never carry labels, responses are validated strictly and refused answers retained, and policy decides in code.

## Making a change

- Write the failing test first. Every module has a test file next to it in `tests/`.
- Keep the change small and say why in the commit message, in the imperative.
- If you touch the UI, check it in a real browser at desktop width and at 375 px, and note what you saw in [docs/QA.md](docs/QA.md).
- If you touch the provider contract, say what live response prompted it and keep the evidence under `evidence/`.
- Do not add a dependency for something the standard library does in fifty lines.
- Do not add company, client or personal data to fixtures, examples or documentation.

## Reporting a problem

Open an issue with the version (shown in the app header), what you did, what you expected and what happened. For anything that looks like a key leaving the process or content acting as instructions, see [SECURITY.md](SECURITY.md) instead.
