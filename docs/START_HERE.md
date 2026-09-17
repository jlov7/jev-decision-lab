# Start here

## Read, run, then test the proposition

The package has two distinct deliverables: a source-grounded research/audit report, and an implemented local learning laboratory. The latter uses authored fixtures by default. It is not a live Jev benchmark or a production control system.

Start with [RESEARCH_REPORT.md](RESEARCH_REPORT.md) for the product explanation, technical limits, boss-hypothesis validation, model-garden framing, practitioner evidence, sector applications and incubation recommendation. Read [FRONTIER_MISS_AUDIT.md](FRONTIER_MISS_AUDIT.md) for the dated antecedents and the boundary between a visible direction and an unproven pipeline failure.

Run the lab using the root README. Then use [WORKSHOP.md](WORKSHOP.md) for a five-minute demonstration or an engineer session. The deliberately confident wrong case is important: do not remove it to make the presentation look better.

[BUILD_PACKET.md](BUILD_PACKET.md) defines the existing architecture, exact interfaces, user journeys, failure modes and continuation phases. [EVALUATION.md](EVALUATION.md) specifies what must be measured before a claim. [ACCESS_AND_TROUBLESHOOTING.md](ACCESS_AND_TROUBLESHOOTING.md) takes an account to a first native call and distinguishes the Vercel route. [CODEX_HANDOFF.md](CODEX_HANDOFF.md) is the paste-ready continuation prompt. [QA.md](QA.md) states the tests and remaining verification. [SOURCES.md](SOURCES.md) links original evidence and explains inspection limits.

## Immediate sequence

```bash
python3 scripts/setup_lab.py
python3 -m unittest discover -s tests -v
python3 -m jev_lab check
python3 -m jev_lab
```

Open `http://127.0.0.1:8765`. Try S02, expired evidence, removed approval, then S04. No provider key is needed.

## What exists

Three scenario packs, twelve teaching cases, six typed questions, a native HTTP adapter, strict response validation, policy replay, content-hashed receipts, a before-action simulation, a model-garden worksheet, a dated source chronology, evaluation metrics, a request-shape experiment CLI and tests.

## What does not yet exist

An authenticated Jev run, a live competitor comparison, a representative domain calibration result, an actual ingestion-log audit, enterprise approval, a real effect/authority service or a production deployment. These are explicit next stages, not hidden claims.
