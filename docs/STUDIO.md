# Decision Studio: from useful question to defensible experiment

Version 0.6 · 20 September 2026. The patterns are authored teaching contracts. Request previews make zero model calls; live execution uses the existing native adapter after explicit consent. No external action, data upload, model training or automatic deployment is added.

## The contract

Every pattern has a stable identifier, contract version, routine and adverse source, typed questions, conventional baseline, deterministic boundary, source link and study design. Preview exports contain only the native model/state/questions request; study designs and live observations are different export types. A changed selection clears consent and the displayed observation so an old answer cannot silently describe a new input.

| ID | What the example actually implements | Deliberate limit |
|---|---|---|
| `citation` | Code checks exact quote membership in the provided source; a typed semantic question asks whether the source supports the claim | No claim that a quote absent here is fabricated everywhere |
| `commitment` | A semantic comparison of old/new commitment wording | Not a date calculator, approval service, or authoritative event store |
| `extraction` | Code enumerates exact email candidates and source spans; Jev selects an allowed ID or none | Not arbitrary extraction or permission to contact a person |
| `skills` | A bounded skill menu and an explicit no-fit option | Not the source cookbook's two-stage search of a large real roster |
| `entities` | Same/different/ambiguous judgment with a deterministic identifier-conflict hold | No automatic graph merge or independent truth about legal identity |
| `passages` | Supporting/contradictory/irrelevant classification and an instruction-like-content question | Not a prompt-injection defense or permission to suppress inconvenient evidence |
| `verification` | A source-bound check of an extracted value | Only the checking stage, not a measured end-to-end cheap/strong model cascade |
| `taxonomy` | A small category menu including broader/none options | Not hierarchical beam search or the source's benchmark reproduction |

Those differences are intentional scope disclosures. The [research review](review/RESEARCH.md) links the richer primary examples; this lab does not claim to implement or replicate every stage of each cookbook.

## Read a live result

The response contains provider outputs and usage, a request hash and the named contract. Cost is a dated estimate, not an invoice. Code checks are shown separately from the model answer. Live observation does not lift a code hold, execute a skill, merge an entity or approve a changed commitment.

An invalid or refused response remains a failure and retains available raw output and cost. A timeout may leave billing unknown. A model/version change invalidates comparability unless separately accounted for. No distribution is fabricated for a generative baseline that returns only a category.

## Economics definitions

For `n` attempted cases, failure fraction `f`, and automated fraction `a` of valid answers:

```
failed = n × f
automated = n × (1 − f) × a
reviewed = n − automated
review_hours = reviewed × review_minutes / 60
residual_errors = automated × auto_error_rate + reviewed × reviewer_error_rate
proposed_cost = n × model_cost_per_attempt + review_hours × hourly_cost
                + residual_errors × error_loss + overhead
baseline_cost = n × review_minutes / 60 × hourly_cost
                + n × baseline_error_rate × error_loss
difference = baseline_cost − proposed_cost
```

The baseline is the specified all-reviewed workflow, not the strongest baseline for every domain. Use the study design to nominate the actual incumbent. Automation share and selected-case error rate are separate assumptions; the worksheet does not convert an API probability into either. Failure processing uses the same review duration as other reviewed cases. Fractional expected cases are permitted. Tail losses, delay and recovery are not separately modeled and must not be inferred from the average-loss calculation.

The four sensitivity rows change one input at a time, not a joint stress test. The displayed break-even error rate may lie outside `[0,1]`: that means no feasible crossing or a crossing beyond this mathematical range, not a calibrated operating threshold. Available review hours apply to the proposed workflow; baseline staffing is not independently assessed.

## Study-design export

The export starts as `UNRUN`, with `results: null`. Before calling it a study result, a named domain owner must set the population, data rights, independent labels and adjudication, development/validation/test split, strongest practical baseline, tuning budget, reviewer time budget, costly-error tolerance and stop rule. Collect failed as well as successful attempts. Measure the routing-selected population, not only aggregate accuracy.

Do not optimize thresholds on the final test set. Do not multiply separate-question probabilities as though their errors were independent. A high-confidence wrong answer, an out-of-menu situation or review backlog can invalidate the intended workflow even when every JSON response validates.

## New local HTTP surfaces

`GET /api/studio` returns the public pattern catalog and economics defaults/bounds. All POST routes require the existing local session token, same-origin checks and exact allowed fields:

| Route | Fields | Network effect |
|---|---|---|
| `/api/studio-preview` | `pattern_id`, `variant` | None |
| `/api/studio-study` | `pattern_id` | None |
| `/api/studio-run` | `pattern_id`, `variant`, `consent` | At most one explicitly authorized native attempt |
| `/api/economics` | `assumptions` containing exactly twelve named values | None |

Unknown fields, invalid pattern/variant, non-finite numbers, booleans masquerading as numbers and out-of-range values are rejected. The Studio does not accept arbitrary pasted state; use the separately consented synthetic playground for authored text.
