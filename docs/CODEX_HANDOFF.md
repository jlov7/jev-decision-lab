# Codex continuation prompt

Paste the following into a coding session opened on this repository.

---

You are continuing Jev Decision Lab, an existing synthetic-first enterprise judgment workbench. Do not start a new app or replace it with a chatbot. Read `AGENTS.md`, `docs/START_HERE.md`, `docs/BUILD_PACKET.md`, `docs/RESEARCH_REPORT.md`, `docs/FRONTIER_MISS_AUDIT.md`, `docs/EVALUATION.md`, and `docs/QA.md` before editing.

The user is an enterprise frontier strategist. The purpose is learning plus discriminating experimentation, not a flattering product demo. Three enterprise scenario packs share typed judgment, explicit policy, evidence repair, receipts and a before-action simulation. The model-garden and signal-audit views are deterministic teaching aids. No real company/client data or effects are authorized. Use “consultancies,” not a named employer.

First reproduce the local tests and run the actual server in a normal browser on the target device. The retained container browser check had a specific limitation: managed Chromium blocked direct loopback navigation, so it rendered local assets with a fetch bridge to the real Python HTTP server. Do not describe that as proof of normal-browser CSP/network integration. Verify that integration now.

Do not assume a provider key exists. Never request it in chat or write it into files. The user can set `TYPESAFE_API_KEY` and `JEV_ALLOW_LIVE=1` in the local process environment. A live call needs explicit UI consent or CLI `--mode live --allow-network`. Start with one bundled synthetic case. Inspect the actual model identity, Score probability and legend shape, Noul shape and token usage. Preserve a safe failure rather than inventing fields or switching to replay.

Then follow phases in the build packet. The native adapter is implemented; the Vercel AI Gateway adapter and live comparator suite are not. Native `noul` and Gateway `boolean` are not interchangeable wire schemas. Recheck current official documentation and pin exact versions before adding either adapter. Do not silently install unreviewed third-party skills.

Add each change through a failing test, implement it, rerun tests, inspect the UI and retain the result. Keep business logic out of the browser. No provider payload may contain gold labels, expected routes or teaching notes. Do not multiply question probabilities as independent events. Model scores never grant permissions. Unknown, expired or changed authority holds the action. Policy-only replay may reuse a model result only while its original evidence/question meaning remains unchanged.

Do not add a fake leaderboard. Before performance claims, freeze independently reviewed labels, development/validation/test splits, provider configurations, full-cost accounting and consequential-error metrics. Compare tuned rules and a cheap constrained-output baseline as well as a strong model. Keep minimal-answer and full-probability tracks separate. Account for rejected/failed cases and human review.

Preserve the previous receipt, source hashes and version lineage. A hash is not a signature. The local server is not internet-facing production software; deployment requires authentication, persistent access-controlled storage, real authority/effect/recovery services, approval and separate security review.

Work on the feature branch and open a reviewable PR. Do not force-push or merge main without approval. At handoff state exactly what was changed, what commands ran, which tests passed, which API calls actually occurred and what remains untested. A clean negative experiment is a valid result.

---

## First commands

```bash
python3 scripts/setup_lab.py
python3 -m unittest discover -s tests -v
node --check web/app.js
python3 -m jev_lab check
python3 -m jev_lab
```

Node is only needed for the optional JavaScript syntax check, not for runtime. The source files and documentation are already present; no paid model call is needed to run the teaching application.
