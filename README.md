# Jev Decision Lab

A synthetic-first enterprise workbench for understanding typed judgment models, explicit policy and the boundary before action. Includes a detailed research report, an audit of prelaunch frontier signals, a model-garden worksheet and a Codex continuation packet.

## Run locally

```bash
python3 scripts/setup_lab.py
python3 -m unittest discover -s tests -v
python3 -m jev_lab check
python3 -m jev_lab
```

Open `http://127.0.0.1:8765`. Runtime uses Python 3.10+ standard library and local browser assets. No install, GPU or API key is needed for synthetic replay. Python 3.13 was tested in the build environment; validate your target interpreter and browser.

## Start here

Read [the package guide](docs/START_HERE.md), [research report](docs/RESEARCH_REPORT.md), [frontier miss audit](docs/FRONTIER_MISS_AUDIT.md) and [build packet](docs/BUILD_PACKET.md). The [Codex prompt](docs/CODEX_HANDOFF.md) explains the continuation sequence.

Three packs cover supplier disruption, service incidents and consultancy deliverable review. Inspect six typed questions, vary policy without a new model call, demonstrate a confident wrong answer, and recheck a simulated action after approval changes. The model-garden and source-timeline views are deterministic learning tools.

## Claims and limits

Replay outputs are authored teaching fixtures, not measured Jev results. The native TypeSafe adapter is implemented and mock-contract tested, but no authenticated Jev call was made during this build. There are no external actions and no real business-data uploads. The chronology does not establish actual tracker ingestion. Read [QA and remaining verification](docs/QA.md).

To connect your account, use the [access guide](docs/ACCESS_AND_TROUBLESHOOTING.md). Never paste an API key into the UI, a prompt or a repository. Personal-device access is not enterprise approval.

## Repository policy

Private research/prototype material. No open-source license is granted by this package. Third-party sources remain subject to their own terms; the bibliography links originals instead of redistributing them.
