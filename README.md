# Jev Decision Lab

**A model can judge. Your system must decide.**

An independent, local learning and experiment lab for TypeSafe's Jev. Understand typed judgments, inspect the evidence, challenge the boundaries, and design a test that can reject the idea—not just make a convincing demo.

**Version 0.6.0 · 20 September 2026.** No account is needed to start. No provider is called on startup. This is not a benchmark, production control system, or claim that Jev improves a business outcome.

## Start in five minutes

Python 3.10+ and a modern browser:

```bash
git clone https://github.com/jlov7/jev-decision-lab.git
cd jev-decision-lab
uv run jev-lab
```

Without `uv`, use `python3 -m jev_lab`. Open **http://127.0.0.1:8765**. The app generates its teaching data locally on first launch. Use the **Start** screen's three-step lesson:

1. Inspect an on-time delivery described with the word “delay.”
2. Withdraw approval and expire evidence. Code holds the simulated action or asks for fresh evidence, without a new model call.
3. Examine a deliberately confident, wrong **authored fixture**, then complete the teach-back.

The lesson exports its observations and your answers. A completed teach-back is a learning record, not independent usability evidence or a qualification.

## Three paths through the lab

| Your question | Begin here | What you leave with |
|---|---|---|
| What does a judgment model contribute? | **Start**, then **Learn & measure** | A clear distinction between output shape, correctness, calibration, policy, and authority |
| What could I build? | **Decision Studio**, then **Workbench** | A versioned request, an adverse example, deterministic boundaries, and an unrun study design |
| Does it improve this workflow? | **Decision Studio economics**, then **Live lab** | Explicit assumptions, matched-case observations, failed attempts, review-capacity constraints, and an experiment snapshot |

## Eight patterns, not eight performance claims

Decision Studio contains **16 synthetic situations**: a routine and adverse example for each pattern. It displays readable source text, typed questions, exact request bytes as JSON, a conventional baseline, and what must remain in code. These new examples have **no invented replay probabilities**. Request preview and study export are offline; an actual model observation requires an explicit live call.

| Pattern | Question for Jev | What code / people still own |
|---|---|---|
| Claim support | Does this source support the claim? | Exact quotation membership, source scope, independent review |
| Changed commitment | Did the meaning of the commitment weaken? | Version/expiry checks and new approval; no inherited authority |
| Verbatim extraction | Which pre-parsed candidate fits? | Exact source spans; the model cannot invent a candidate |
| Skill suggestion | Which skill fits, or does none fit? | Allowlist, least privilege, loading and execution |
| Entity alignment | Same entity, different entity, or ambiguous? | Identifier conflicts and approval before any merge |
| Retrieval triage | Supporting, contradictory, or irrelevant evidence? | Preserve contrary evidence; no “relevant = true” shortcut |
| Extraction check | Is an extracted fact supported? | Escalation policy; this is a check stage, not a complete model cascade |
| Taxonomy backoff | Which defensible category, including a broader one? | Category validity; this bounded example is not hierarchical beam search |

Patterns are informed by [official cookbooks and a dated research review](docs/review/RESEARCH.md). The lab's examples are newly authored, not reproductions of vendor benchmark results. See [the Studio guide](docs/STUDIO.md).

## What the existing surfaces do

**Workbench** retains twelve synthetic cases across supplier disruption, service incidents, and deliverable review. Run six typed questions, inspect distributions, replay policy, recheck simulated authority, and export a content-hashed receipt.

**Live lab** supports a twelve-case burst, a free-text synthetic playground, side-by-side comparison with rules and configured generative baselines, repeated-call probes, and evidence ablation. Failures remain in the denominator. Missing cost stays unknown. Comparison reports include a common answered subset without hiding failures or pretending all providers supply comparable distributions.

**Model garden** is a deterministic capability worksheet, not a model leaderboard. **Signal audit** retains the dated prelaunch chronology. **Learn & measure** teaches Choice, Score and Noul and demonstrates calibration machinery over authored fixtures—not measured Jev calibration.

## Make one live observation

Open **Connect Jev** and paste a TypeSafe key into the local connection dialog. It is sent to the loopback server and kept in process memory, not saved to disk. The server uses it to authenticate requests to TypeSafe. Connect does not itself run the model. Read the displayed request, explicitly authorize sending it, and choose **Run this request live**.

Alternatively keep the key in the terminal (the first line reads it without echo):

```bash
read -s TYPESAFE_API_KEY
export TYPESAFE_API_KEY JEV_ALLOW_LIVE=1
uv run jev-lab
```

The default native attempt cap is **20 per server process**. A Studio observation uses one slot; a twelve-case burst uses twelve. Set `JEV_MAX_LIVE_CALLS` before launch for a longer session. No automatic retries, no silent replay fallback. Forget the key in the dialog or stop the process when finished.

Optional comparison arms use an Anthropic API key (`uv sync --extra compare`), an OpenAI API key, or the owner's installed and signed-in Claude Code command. They require explicit consent and share `JEV_MAX_COMPARE_CALLS` (default 40). API charges and a subscription's list-price equivalent are different billing bases; they are not added into one total. Read the [evaluation protocol](docs/EVALUATION.md) and the maintained [CLI, HTTP API, policy and troubleshooting reference](docs/REFERENCE.md) for the endpoints, environment variables and error handling. Timing, pricing and model-availability examples in this README are dated, not current promises.

**Never paste company, client, personal-sensitive, or regulated material into this research app.** The free-text playground sends the text you provide after consent; exports may contain that text. Inspect exports before sharing. This repository does not contain or grant enterprise data-processing approval.

## Count the workflow, not just tokens

The economics worksheet separates attempted cases, provider failures, automated cases, reviewed cases, residual errors, model cost, human cost and period-matched overhead. Reviewers are not assumed perfect. Review capacity is a constraint, and four sensitivity scenarios expose the effect of changing error rate and review time.

All values are **assumptions**, not live measurements or an ROI forecast. A positive cost difference does not authorize deployment. Study designs remain `UNRUN` until a domain owner fixes the dataset, labels, baseline, error tolerances and review budget and actually runs the comparison.

## Inspect and verify

```bash
uv run python3 scripts/setup_lab.py
uv run python3 -m unittest discover -s tests -v
uv run python3 -m jev_lab check
node --test tests/evidence.test.cjs
for file in web/*.js; do node --check "$file"; done
```

Lint uses Ruff 0.16.8; browser QA uses Playwright 1.57.0 as a **development-only** dependency. The runtime has no third-party Python dependencies or external web assets. `python -m scripts.browser_check --output-dir runs/browser` exercises the running server, all seven surfaces, all sixteen new requests, downloads, phone layout and explicit transport-mock failure paths. It makes no real provider calls. An explicitly requested `--bridge` fallback does **not** establish browser-network/CSP correctness; CI uses real navigation.

The recovered upgrade has **259 Python tests and 7 JavaScript tests**. See the live PR checks for CI outcomes, [QA](docs/QA.md) for the verification boundary, and the [strict ten-category review](docs/review/RUBRIC.md) for what has and has not earned a high score. Passing tests are not independent user validation, model calibration, or a production security audit.

## Evidence and limits

The September 18 owner-recorded live observations in [`evidence/`](evidence/) are preserved unchanged. No new authenticated provider observation was collected while building v0.6. Probes and ablation exports now include self-contained audit receipts rather than depending only on expiring in-memory identifiers. HTML export is a **snapshot of the latest retained result on each surface**, not an append-only record of every run.

A receipt hash detects changed bytes; it is not a signature or proof of truth. Stable outputs can be wrong. Input ablation measures observed sensitivity, not hidden model reasoning or causal importance. Twelve teaching cases and sixteen new situations do not estimate enterprise error rates.

[Start here](docs/START_HERE.md) · [Design](docs/DESIGN.md) · [Studio](docs/STUDIO.md) · [Evaluation](docs/EVALUATION.md) · [Research update](docs/review/RESEARCH.md) · [Review rubric](docs/review/RUBRIC.md) · [Security](SECURITY.md) · [Contributing](CONTRIBUTING.md)

<sub>This is a personal research and development project. It is not affiliated with, endorsed by, or sponsored by my employer. Any views expressed are my own.</sub>
