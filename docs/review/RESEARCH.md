# Jev research update and implementation decisions

**As of 20 September 2026.** This is an engineering synthesis for a local teaching and experiment lab, not a benchmark, vendor endorsement or exhaustive literature review. The September 17 [research report](../RESEARCH_REPORT.md) and [source register](../SOURCES.md) remain the historical foundation. September 18 owner observations in `evidence/` are unchanged; no fresh authenticated inference was performed for this upgrade.

## What changes the build

The useful extension is not a longer list of classifiers. It is an inspectable contract for each judgment: the bounded question, permitted evidence, adverse input, deterministic check, baseline, and observation that could disprove its usefulness. That is our design judgment, rather than a claim that this architecture is unique.

| Finding from sources | Implemented response | Claim that remains unsupported |
|---|---|---|
| TypeSafe documents literal interpretation, numerical/date limitations, adversarial steering, distraction and non-guaranteed cross-question identities (R01). | Small explicit questions; arithmetic and exact checks in code; adverse inputs; no model permission to act. | General prompt-injection immunity, numerical reasoning competence or semantic infallibility. |
| Its cookbooks compose judgment with ordinary code instead of delegating whole processes (R02–R08). | Eight Studio contracts with sixteen authored inputs, exact request previews and exportable unrun study plans. | Replication of the cookbooks' complete systems or measurements. |
| Its skill example separates relative selection from whether any option is suitable (R02). | An allowlisted skill-or-none contract; no automatic invocation. | A deployed or evaluated two-stage 182-skill selector. |
| Its SDE example is a multistage verification arrangement (R08). | A check-stage selector and study design, labelled as a component. | A complete operating cascade or demonstrated cost reduction. |
| Founder/practitioner media emphasizes software-facing judgment and decomposed questions (R09–R11). | A guided three-step lesson and visible separation of output, evidence, policy and authority. | Independent validation of speed, accuracy, learning outcomes or economics. |
| Practitioner objections question schema/meaning conflation, baseline quality and evidence transparency (R12). | Matched answered-subset disclosure, retained failures and costs, descriptive rather than causal ablation language. | A strong held-out model comparison; the keyword arm is not a tuned discriminative baseline. |

## Primary product and engineering sources

All entries distinguish source publication/version information from this review's September 20 inspection date. A current web page is not an immutable historical snapshot. Links remain external references, not runtime dependencies.

| ID | Source and inspection level | What it supports and its limit |
|---|---|---|
| R01 | [Jev 1.13 jaggedness](https://docs.typesafe.ai/model-jaggedness/jev-1.13), full official page, last reviewed by vendor September 17. | A version-specific list of known limitations and guidance. It does not quantify real-world failure prevalence or establish that the lab controls defeat every failure. |
| R02 | [Skill suggestion](https://docs.typesafe.ai/cookbooks/skill_suggestion), full official cookbook. | Two-stage shortlist/selection plus a suitability gate. Published cached results use Jev 1.12 and a specified comparator; they are not measurements of this lab's Jev 1.13 integration. |
| R03 | [Citation check](https://docs.typesafe.ai/cookbooks/citation_check), full official cookbook. | Exact quote membership belongs in code, followed by a semantic support judgment. A literal quote can still be irrelevant, incomplete or from an unreliable source. |
| R04 | [Pre-parsed value extraction](https://docs.typesafe.ai/cookbooks/pre_parsed_value_extraction_cookbook), full official cookbook. | Select among extracted candidates rather than invent a value. Candidate extraction itself can miss the correct value. |
| R05 | [Entity alignment](https://docs.typesafe.ai/cookbooks/entity_alignment), full official cookbook. | Bounded semantic matching with explicit records. Identity resolution still needs hard identifiers and an ambiguity route. |
| R06 | [Classifying RAG passages](https://docs.typesafe.ai/cookbooks/classifying_rag_passages), full official cookbook. | Passage-level judgments before downstream generation. Classification is not evidence verification or a complete injection defense. |
| R07 | [Hierarchical classification](https://docs.typesafe.ai/cookbooks/hierarchical_classification), full official cookbook. | Decomposition of a large taxonomy. Our Studio illustrates a bounded node, not the complete traversal or beam search. |
| R08 | [SDE cascade](https://docs.typesafe.ai/cookbooks/sde_cascade), full official cookbook. | A multistage engineering pattern whose complete costs and failure paths matter. Our check-stage selector is not a replication of the cascade. |
| R09 | [How to build with System One](https://docs.typesafe.ai/concepts/how-to-build-with-system-one), full official guidance. | Decompose work and integrate bounded judgments into code. Guidance is not a production outcome study. |
| R10 | [AI Engineer: What's next after RLHF?](https://ai.engineer/talks/cJ0EOzey--o-whats-next-after-rlhf), organizer-hosted timestamped founder transcript. | Useful passages at approximately 1:36, 4:29–5:15 and 9:43–12:19 concern decisions, assistance versus automation, and software integration. This is a thesis/talk, not a reproducible RLCD training report. Raw YouTube upload-date metadata was not independently obtained. |
| R11 | [ThursdAI, September 17](https://thursdai.news/ep/sep-17-2026), full organizer-hosted episode transcript with video links. | Jev discussion includes vendor representative Allie Laabs from 1:38:48. Around 1:53:43–1:58:26 the discussion stresses meaningful criteria and splitting compound questions. Around 2:04:53 the panel distinguishes typed validity from being right; 2:08:19 contains host demos. These are explanations and first-person demonstrations, not matched evaluations. |
| R12 | [Hacker News launch discussion](https://news.ycombinator.com/item?id=49717558), thread inspected. | Questions about disclosure, ordinary classifier baselines, bounded scope and schema-versus-semantic correctness informed adversarial review. Anonymous architecture guesses and reported experiences were not adopted as technical facts. |
| R13 | [TypeSafe launch](https://typesafe.ai/blog/introducing-system-one-models-and-jev), September 15 official announcement, inspected. | Product existence and the vendor's architecture, parallel sampling and RLCD framing. Headline comparisons do not supply independent domain labels or a complete reproducible training recipe. |
| R14 | [Vercel Jev availability](https://vercel.com/changelog/typesafe-ai-jev-now-available-on-ai-gateway), September 16 official integration announcement; historical register S11. | A separate AI Gateway integration path exists. This Python lab still does not implement or live-verify the Gateway transport. |
| R15 | [Vercel Jev launch usage account](https://vercel.com/blog/ai-gateway-jev-model-launch), September 18 operator account, inspected. | Early platform usage is an operator observation, not retention, accepted outcomes or independent business value. |

### Terminology that must survive marketing

Native Choice supplies a distribution over declared alternatives. Native Score supplies an ordered-level distribution and a weighted index, not a monetary loss estimate. Noul is a probability for a proposition, not a severity scale. The separate Choice/Score confidence statistic is not the same as top-option probability or measured local calibration. See the official [Choice](https://docs.typesafe.ai/primitives/choice), [Score](https://docs.typesafe.ai/primitives/score), [Noul](https://docs.typesafe.ai/primitives/noul), and historical source register for the contract.

Output shape, semantic correctness, empirical calibration, policy compliance and authorization are five distinct claims. A content hash demonstrates integrity relative to retained bytes; it does not demonstrate that a judgment was true or that omitted events never occurred.

## Broader media and practitioner discovery: what was actually acquired

This census is intentionally not described as complete. Many pages repeat the same launch. Independence is about origin and method, not the number of links.

| Route | Acquired material | Evidence boundary |
|---|---|---|
| Startup Ideas Podcast, September 18, “Jev is here. How to use it.” | [Episode metadata](https://podfollow.com/the-startup-ideas-podcast/episode/c56a7821ffd9fa5790843984fd4cac0cef3e5ea6/view) and [full third-party transcript](https://podscripts.co/podcasts/the-startup-ideas-podcast/jev-is-here-how-to-use-it). Relevant themes include email triage around 4:32, workflow components around 7:19 and information queues around 15:46. | Transcript mirror, not manually checked audio. Speculative trading, clipping and browser examples are not adopted as demonstrated capability. |
| Riley Brown, September 18, “JEV: How It Works and What You Can Build” | [Chapter/summary discovery](https://podwise.ai/episodes/8949281); video ID `o1CogAtWdBk`. | No independently inspected full original transcript. Summary claims of determinism or context size were not used to overwrite official documentation. |
| RepoChad, September 16, schema-safe automation | [Video description discovery](https://readpodcast.ai/en/youtube/repochad-cUCtyEhOTxGx45sljlfryc6jw/jev-the-schema-safe-ai-that-could-change-automation-forever-vRPpQacmBe4A). | Description, not a watched or transcribed test. |
| AI Daily Brief, September 16 | [Public transcript excerpt](https://podcastrex.com/shows/the-ai-daily-brief-artificial-intelligence-news-and-analysis/why-a-new-class-of-ai-judgment-models-could-have-big-business-implications/transcript). | The accessible excerpt does not establish inspection of the entire episode. |
| Near Here / Every / Sean Goedecke | Prior inspected practitioner articles retained in S14–S16 of [SOURCES.md](../SOURCES.md). | Narrow selected tests or engineering commentary. Labels, prompt selection, configurations and denominators limit conclusions. These were not rerun. |
| Public GitHub builders | Discovery of [hfiguera/typesafe_ai](https://github.com/hfiguera/typesafe_ai), [nickthompson480/typesafe-ai-playground](https://github.com/nickthompson480/typesafe-ai-playground), [geilt/typesafe-cli](https://github.com/geilt/typesafe-cli), and [valentynkit/awesome-jev-typesafe](https://github.com/valentynkit/awesome-jev-typesafe). Official Python adapter remains historical S32. | Discovery is not a code audit, safe dependency recommendation or independent performance replication. No community code was imported into this lab. |
| X | Exact launch, host-demo and Cua posts linked from ThursdAI were followed; direct retrieval failed. | The accessible podcast transcript supports its own discussion. It is not a substitute for inspection of the original post/video or a complete X search. |
| Reddit and practitioner forums | Targeted Jev/TypeSafe searches did not yield an inspectable relevant Reddit thread in the acquired set. The vendor documentation links a Discord community. | No private Discord access or complete forum archive was obtained. This says nothing about how much discussion exists elsewhere. |

## What to investigate next—not silently claim implemented

A two-stage large skill catalogue with a reject-all gate; a complete staged verification cascade; a traversable taxonomy with error propagation; and matched discriminative-model baselines are defensible next experiments. They should not be bolted onto the first-use path merely to increase feature count.

For an enterprise trial, select one consequential but reversible decision. Freeze the evidence/label rules and develop, validate and test on separate case families. Use domain-qualified adjudication, a tuned conventional baseline, Jev and a matched constrained-output baseline. Count unavailable answers, costly misses, reviewer work, capacity and total accepted-outcome cost. A result that rejects Jev is an acceptable result. The Studio exports the study design; it does not invent the study's results.

The product direction is therefore **judgment-contract engineering with falsifiable workflow economics**, not an assertion that this repository proves a new model architecture, model superiority, universal guardrails or a validated consultancy service.
