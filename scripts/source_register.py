"""Bibliographic metadata and explicit evidence ceilings; no copied source corpus."""
import json
from pathlib import Path

rows=[
('S01','TypeSafe: Introducing System One Models & Jev','https://typesafe.ai/blog/introducing-system-one-models-and-jev','2026-09-15','vendor launch','Full HTML inspected. Architecture and performance are vendor claims; schema safety is not semantic correctness.'),
('S02','TypeSafe quick start','https://docs.typesafe.ai/introduction/quickstart',None,'official documentation','Native account, Playground and API setup. Account-specific entitlements were not inspected.'),
('S03','TypeSafe API reference','https://docs.typesafe.ai/api',None,'official documentation','Native wire contract inspected; no authenticated live response obtained.'),
('S04','TypeSafe models and prices','https://docs.typesafe.ai/models',None,'official documentation','Observed 2026-09-17; prices, limits and aliases can change.'),
('S05','TypeSafe confidence semantics','https://docs.typesafe.ai/confidence',None,'official documentation','Distribution-derived confidence is distinct from probability and measured calibration.'),
('S06','TypeSafe Choice primitive','https://docs.typesafe.ai/primitives/choice',None,'official documentation','Categorical request and response semantics.'),
('S07','TypeSafe Score primitive','https://docs.typesafe.ai/primitives/score',None,'official documentation','Ordered descriptions, weighted level index and distribution; not expected monetary loss.'),
('S08','TypeSafe Noul primitive','https://docs.typesafe.ai/primitives/noul',None,'official documentation','Probability of yes; no separate confidence field.'),
('S09','How to build with TypeSafe','https://docs.typesafe.ai/concepts/how-to-build-with-system-one',None,'official documentation','Workflow decomposition and native integration; not production outcome evidence.'),
('S10','TypeSafe machine-learning primer','https://docs.typesafe.ai/introduction/machine-learning-primer',None,'official documentation','Vendor framing of post-training objectives; not a full RLCD technical report.'),
('S11','Vercel: Jev available on AI Gateway','https://vercel.com/changelog/typesafe-ai-jev-now-available-on-ai-gateway','2026-09-16','official integration release','AI SDK 7.0.105+ experimental evaluate; route-specific privacy controls. Not tested here.'),
('S12','TypeSafe privacy policy','https://typesafe.ai/legal/privacy-policy','2025-11-19','provider legal text','Current policy inspected; no-training promise differs from retention and data-location commitments.'),
('S13','TypeSafe website terms','https://typesafe.ai/legal/terms','2026-09-14','provider legal text','Site terms are not a substitute for the actual API/commercial agreement.'),
('S14','Every: Mini-Vibe Check of Jev','https://every.to/also-true-for-humans/mini-vibe-check-typesafe-s-jev-judged-everything-i-ve-written-in-0-7-seconds','2026-09-15','first-person practitioner test','Small, selected writing tests; concurrent document requests; no enterprise-general result.'),
('S15','Near Here: Jev, Mistral and Gemini event validation','https://nearhere.events/blog/typesafe-jev-mistral-gemini-event-validation','2026-09-16','first-person practitioner test','Prompt selection, assistant-written labels, narrow additional set, unequal output/reasoning settings limit conclusions.'),
('S16','Sean Goedecke: structured output is interesting again','https://www.seangoedecke.com/jev-means-structured-output-is-interesting-again/','2026-09-16','practitioner engineering commentary','Reasoned interpretation, not a measured trial.'),
('S17','Hacker News Jev launch discussion','https://news.ycombinator.com/item?id=49717558','2026-09-15','discussion and founder comments','Discovery, objections and founder clarifications. Comments are not independent replication.'),
('S18','Founders You Should Know: March 25 recap','https://newsletter.foundersysk.com/p/founders-you-should-know-march-25th','2026-04-01','organizer first-party recap','March 25 event; direct TypeSafe automation direction. Current page, not archived historical bytes.'),
('S19','AI Engineer: What’s next after RLHF?','https://ai.engineer/talks/cJ0EOzey--o-whats-next-after-rlhf',None,'organizer-hosted founder transcript','Timestamped content verified; July 31 upload timing is secondary-corroborated, not independently retrieved from raw YouTube metadata.'),
('S20','TypeSafe: AI too good to be true, too bad to be useful','https://typesafe.ai/blog/ai-too-good-to-be-true-too-bad-to-be-useful-typesafe-ai','2026-06-19','vendor talk page','Current page date; embedded-video transcript not independently obtained.'),
('S21','TypeSafe: The Bitterest Lesson','https://typesafe.ai/blog/bitterest-lesson','2026-09-10','founder thesis','Task-first framing; does not disclose the full Jev implementation.'),
('S22','Guo et al.: On Calibration of Modern Neural Networks','https://proceedings.mlr.press/v70/guo17a.html','2017','research paper','Historical calibration research; no claimed direct lineage to Jev.'),
('S23','Yin et al.: Benchmarking Zero-shot Text Classification','https://arxiv.org/abs/1909.00161','2019-08-31','research paper','Primary abstract and submission record inspected; earlier label-fully-unseen classification.'),
('S24','Bani-Harouni et al.: Rewarding Doubt','https://arxiv.org/abs/2503.02623','2025-03-04','research paper','v1 date; current v6 is February 28, 2026. Abstract supports logarithmic calibration reward, not TypeSafe lineage.'),
('S25','Damani et al.: Beyond Binary Rewards / RLCR','https://arxiv.org/abs/2507.16806','2025-07-22','research paper','v1 date; current v2 May 15, 2026. Correctness plus Brier calibration reward; not TypeSafe RLCD.'),
('S26','Stepanov et al.: GLiClass','https://arxiv.org/abs/2508.07662v1','2025-08-11','research paper','Primary abstract: flexible lightweight zero/few-shot classification and PPO adaptation. No matched Jev benchmark.'),
('S27','RouteLLM','https://arxiv.org/abs/2406.18665','2024','research paper','Earlier model-routing work; no Jev-specific inference.'),
('S28','Anthropic: Constitutional Classifiers','https://www.anthropic.com/research/constitutional-classifiers','2025','first-party research','Earlier classifier-mediated controls; not a universal defense or zero-shot Jev equivalent.'),
('S29','Language Models (Mostly) Know What They Know','https://arxiv.org/abs/2207.05221','2022','research paper','Earlier model uncertainty work; not deployment calibration proof.'),
('S30','RLCD: Reinforcement Learning from Contrastive Distillation','https://arxiv.org/abs/2307.12950','2023','research paper','Acronym collision: different expansion and work from TypeSafe RLCD.'),
('S31','Thinking Machines: Introducing Inkling','https://thinkingmachines.ai/news/introducing-inkling/','2026-07-15','official model release','Inkling is a model; Tinker is a customization platform. “Tinder” being a typo is only an interpretation.'),
('S32','TypeSafe System One adapter Python repository','https://github.com/typesafe-ai/system-one-adapter-python',None,'official repository','Repository contents inspected through GitHub connector; contains source, tests and docs, not only a README. Not installed or benchmarked here.'),
('S33','StartupHub: Beyond RLHF','https://www.startuphub.ai/ai-news/ai-research/2026/beyond-rlhf-the-future-of-ai-automation','2026-08-01','secondary chronology corroboration','Supports an early-August public-discussion trail; not primary algorithm evidence.'),
('S34','Sumz-up: What’s next after RLHF?','https://sumz-up.com/analysis/cj0eozey--o','2026-08-02','secondary chronology corroboration','Lists July 31 video date. Not an authoritative upload timestamp or independent technical evidence.'),
('S35','TypeSafe shared state','https://docs.typesafe.ai/concepts/state',None,'official documentation','State representation and context selection; no account-specific context maximum verified.'),
('S36','TypeSafe fan-out pattern','https://docs.typesafe.ai/patterns/fan-out',None,'official documentation','Multiple independent questions; not statistical independence of errors.'),
]
root=Path(__file__).resolve().parents[1]
items=[dict(id=i,title=t,url=u,published=d,kind=k,accessed='2026-09-17',boundary=b) for i,t,u,d,k,b in rows]
(root/'docs/source-register.json').write_text(json.dumps(items,indent=2)+'\n')
text='# Sources and inspection boundaries\n\nResearch cutoff: September 17, 2026. References are primary wherever possible. Dates distinguish an initial submission from a later revision. No full third-party articles or transcripts are redistributed.\n\n'
for r in items:
    text+=f"## {r['id']}: {r['title']}\n\n{r['url']}\n\n**Type:** {r['kind']}. **Date:** {r['published'] or 'undated/current documentation'}. **Accessed:** {r['accessed']}.\n\n{r['boundary']}\n\n"
text+='## Search coverage\n\nOfficial docs and launch materials, founder talks, academic antecedents, GitHub source availability, a long Hacker News thread, first-person practitioner reports, and targeted X/Reddit searches were examined. Direct indexed X/Reddit coverage was incomplete. No verified direct Jev article by Simon Willison was identified; Sean Goedecke is a different author. Reposts and aggregate pages were not counted as independent trials. This is a bounded source review, not an exhaustive census of social discussion.\n'
(root/'docs/SOURCES.md').write_text(text)
