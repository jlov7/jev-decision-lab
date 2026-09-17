# Jev Decision Lab

A local workbench for seeing what TypeSafe's Jev judgment model actually does: how fast it answers, what it costs, what typed answers and distributions it returns, and what your own code must still decide. It ships with three synthetic enterprise scenario packs, a live burst console, a free-form playground, a side-by-side comparison against a constrained-output Claude baseline, explicit policy replay, content-hashed receipts, a model-garden worksheet, a prelaunch signal audit and a research report.

## Run locally

```bash
uv run python3 scripts/setup_lab.py
uv run python3 -m unittest discover -s tests -v
uv run python3 -m jev_lab check
uv run python3 -m jev_lab
```

Open `http://127.0.0.1:8765`. The runtime is Python 3.10+ standard library plus local browser assets; `uv` is only a convenience for a clean interpreter. No API key is needed for synthetic replay. Python 3.13 was tested.

## Connect your Jev account

Create an API key in the TypeSafe console, then start the server from a terminal so the key lives only in that process:

```bash
read -s TYPESAFE_API_KEY && export TYPESAFE_API_KEY
export JEV_ALLOW_LIVE=1
uv run python3 -m jev_lab
```

Open **Live lab**, tick consent, and fire the burst: twelve cases, seventy-two typed judgments, concurrent, with client-observed latency and an estimated cost per run. Then ask your own questions in the playground. For the Claude comparison arm, also export `ANTHROPIC_API_KEY` and run `uv sync --extra compare` once. Every live path requires the server-side key, the enable flag and per-run consent; nothing retries and nothing falls back to replay.

For a terminal-only first call:

```bash
uv run python3 -m jev_lab smoke --mode live --allow-network --out runs/first-live.json
```

## Start here

Read [the package guide](docs/START_HERE.md), [research report](docs/RESEARCH_REPORT.md), [frontier miss audit](docs/FRONTIER_MISS_AUDIT.md) and [build packet](docs/BUILD_PACKET.md). The [Codex prompt](docs/CODEX_HANDOFF.md) explains the continuation sequence.

Three packs cover supplier disruption, service incidents and consultancy deliverable review. Inspect six typed questions, vary policy without a new model call, demonstrate a confident wrong answer, and recheck a simulated action after approval changes. The model-garden and source-timeline views are deterministic learning tools.

## Claims and limits

Replay outputs are authored teaching fixtures, not measured Jev results. The native TypeSafe adapter and the Claude comparison arm are contract-tested against the official documentation with controlled responses; no authenticated call was made during the build itself, so the first live burst on your account is the first real measurement. Twelve synthetic cases are a smoke test, not a benchmark. There are no external actions. The playground sends only text you type, live, after consent; it is not a channel for company or client data. The chronology does not establish actual tracker ingestion. Read [QA and remaining verification](docs/QA.md).

To connect your account, use the [access guide](docs/ACCESS_AND_TROUBLESHOOTING.md). Never paste an API key into the UI, a prompt or a repository. Personal-device access is not enterprise approval.

## Repository policy

Private research/prototype material. No open-source license is granted by this package. Third-party sources remain subject to their own terms; the bibliography links originals instead of redistributing them.
