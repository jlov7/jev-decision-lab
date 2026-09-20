# Ten-category review rubric and assessment

**Assessment date: 20 September 2026. Scope: local educational and experimental software, not a production control system.** Base code: `93c076302e6fdf4891e08e8d4fa71bef9c63f3a1`. Each category is scored out of 100; the requested threshold is **90 in every category**, not a compensating average.

## Review method and independence

This review applies ten disciplinary perspectives to actual source, failure tests, rendered journeys, retained observations and documentation. They are perspectives of one assistant, **not ten independently dispatched agents or an independent tribunal**. No actual independent agent review was available in this run. An assistant editing the artifact also has an evaluator conflict; passing its own rubric cannot eliminate that conflict.

The scores below are evidence-bounded reviewer judgments, not probabilities, benchmark scores or measured user satisfaction. Their purpose is to expose the remaining work, not certify a release. The criterion definitions were applied consistently to the baseline and reconstructed upgrade. The original interrupted scoring process cannot be reconstructed as a frozen independent evaluation; this document does not claim otherwise.

### Anchors

**0–49:** a central promise fails or is seriously misleading. **50–69:** useful prototype with substantial uncovered behavior or user burden. **70–79:** coherent functionality but important evidence or experience gaps. **80–89:** strong implementation within its scope; independent or cross-environment acceptance incomplete. **90–94:** excellent within a defined scope, with direct acceptance evidence and no material known blocker. **95–100:** adds strong independent replication and sustained maintenance evidence; not earned by adding features or tests alone.

Every category has five dimensions worth 20 points each. A hard cap overrides their sum. An untested external claim stays untested; rewriting a disclaimer is not equivalent to obtaining evidence.

## Criteria, baseline and upgrade

| Category / reviewing perspective | Five dimensions, 20 points each | Baseline /100 | Upgrade /100 | Why the upgrade is still below 90 |
|---|---|---:|---:|---|
| 1. First-use comprehension / unfamiliar enterprise leader | Clear purpose; no-key setup; first useful result; concept separation; demonstrated comprehension | 61 | 84 | Guided lesson and teach-back now exist, but no independent first-time human completed a comprehension study. |
| 2. Interaction and accessibility / designer and assistive-technology user | Navigation; state feedback; recovery; keyboard/semantic controls; device and assistive-tech coverage | 65 | 85 | Desktop and phone Chromium flows exercised; Safari, Firefox, real touch and screen-reader acceptance remain unrun. |
| 3. Visual clarity / design reviewer | Hierarchy; readable density; responsive layout; consistent controls; useful information encoding | 71 | 86 | Actual overflow and answer rendering fixed. Independent visual review and broader display/zoom coverage are missing. |
| 4. Technical and research accuracy / skeptical ML engineer | Exact model contract; versioning; source-to-claim mapping; limits; independent verification | 76 | 87 | Known vendor limits and scope are clearer. Fresh native-model retesting and external technical review remain missing. |
| 5. Measurement integrity / evaluation scientist | Denominators; comparable cohorts; failure accounting; uncertainty semantics; held-out outcomes | 56 | 83 | Several real accounting/probe defects fixed. Only the owner head has the existing synthetic measurement demonstration; no full independently adjudicated held-out evaluation. |
| 6. Usefulness and domain relevance / workflow owner | Recognizable task; appropriate baseline; adverse cases; reusable contract; demonstrated decision value | 67 | 84 | Eight patterns broaden practical exploration but are authored teaching contracts, not domain-validated outcomes. |
| 7. Ambition and differentiation / builder and frontier strategist | Distinct problem; composition depth; falsifiability; reusable assets; comparison with alternatives | 63 | 85 | Contract plus economics is a stronger thesis. Full cascades, large skill selection and comparative user value are not established. |
| 8. Safety and data boundaries / platform-risk reviewer | Credentials; consent/budget; egress; authority separation; adversarial verification | 82 | 88 | Existing local controls preserved and malformed responses retained. No independent security assessment or production threat-model validation. |
| 9. Engineering and reproducibility / maintainer | Tests; modularity; failure behavior; environment reproducibility; artifact custody | 75 | 88 | 259 Python and 7 JS tests, direct-navigation CI definition, retained export evidence. Final CI and fresh packaging must be inspected; independent maintainer review absent. |
| 10. Documentation and evidence handoff / prospective contributor | Quick start; architecture/API; examples; source/QA traceability; release and continuation clarity | 66 | 87 | Short front door and scope-specific guides now replace overload. Complete external link maintenance and independent clean-machine onboarding remain unmeasured. |

**Upgrade dimensions sum:** 84, 85, 86, 87, 83, 84, 85, 88, 88, 87. These provisional values must not be described as an independent panel result. No weighted overall score is used because it would conceal failed category gates.

### Explicit caps

Unmeasured human comprehension caps category 1 at 89. Missing assistive-technology acceptance caps category 2 at 89. Missing independent source/technical review caps category 4 at 89. No independently adjudicated held-out domain outcome caps categories 5 and 6 at 89. Missing independent security review caps category 8 at 89. Unverified final CI or missing fresh-install evidence caps category 9 at 89. A fabricated measurement or concealed material defect would instead cap its affected category below 50 and block release.

## Verified defects and repair cycles

| Cycle | Observable defect or missing behavior | Repair and direct evidence |
|---|---|---|
| Measurement | An incomplete probe could appear stable. Noul variation could be absent from the widest-change summary. | Stable verdict withheld for incomplete/mixed runs; Noul included; regression tests fail on the baseline and pass after repair. |
| Cost accounting | Failed comparisons could disappear from cost/usage summaries. Non-finite or mixed-billing quantities could mislead exports. | All attempts retained; unknown distinguished from zero; billing bases displayed separately; Python and JS regressions. |
| Ablation | Comparing different winning labels and using “noise” or causal influence language overstated the experiment. | Same-label delta; descriptive range; reference scoped by case, state, question and model. No causal claim. |
| Comparison | Unequal answered cohorts and duplicate requests could distort agreement. | Common answered subset exposed beside all-attempt denominator; duplicate cases/arms rejected; planted replay exception explicitly scoped. |
| Provider failures | Generative refusal/invalid output could lose a parseable raw response and billable usage. | Claude, OpenAI and Claude Code failures retain raw envelope/provenance; nonzero CLI exit fails closed. No retries. |
| Export custody | A snapshot could point only to an expiring in-memory receipt. | Full audit receipts retained for probes/ablations and canonical requests/raw outputs retained for comparisons. |
| First-use/Studio | No coherent entry lesson or bounded pattern exploration. | Start lesson, eight patterns/sixteen previews, explicit live consent and unrun study exports. Offline by default. |
| Browser | Wrong Studio answer-renderer arguments and populated mobile Live lab overflow. | Correct invocation and responsive constraints; rendered regression journeys. |
| Reproducibility | Setup could regenerate an outdated source-register note. | Generator corrected, repeatable output tested, CI checks generated-file drift. |

A repaired bug is one closed failure class, not proof that all classes have been covered. The [QA record](../QA.md) gives the environment, commands, historical observations and untested surfaces. The actual final commit's CI checks supersede a static statement about local execution.

## What would genuinely clear the 90 threshold

For first-use and design, obtain observed task completion and teach-back from unfamiliar leaders, engineers and risk reviewers; test keyboard, screen-reader, zoom, Safari and phone interaction. Define acceptable errors before the sessions.

For technical accuracy, measurement and usefulness, have an independent engineer review the model contract, cost/custody paths and failure tests. Conduct a small rights-cleared domain study with independently adjudicated labels and strong matched baselines. Estimate uncertainty and costly misses without tuning on the final holdout. Re-run the exact native integration on a consenting account, retaining all responses and failures.

For safety, have an independent reviewer test the loopback service's origin/token/credential/budget boundary and document the residual local-user threat model. Do not expand to a public service without a separate architecture and authorization decision.

For engineering and handoff, require final green platform and real-navigation CI, exact remote-tree read-back, and a clean-machine installation by someone other than the author. Preserve failures and update the score only for new evidence.

## Release decision

**Materially improved, software-review candidate; universal 90+ acceptance is not established.** Open the PR for inspection with explicit remaining gates rather than label it perfect, automatically merge it, deploy it publicly, or keep editing until a self-score becomes flattering. A negative or unresolved gate is evidence, not a reason to lower the standard.
