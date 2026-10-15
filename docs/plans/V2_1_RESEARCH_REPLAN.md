# V2 cm1: research-led custom OCR plan

Status: research preparation GO; S2 tuning/training and production candidate HOLD. Owner scope update: 2026-10-15. Base main remains `3929ed86a96d156377649c55714a45eb9c23d719`; retained cm1 source head `0724a9c4ed3b3d569f236a8d149f701889f044dd`.

This is the orchestrator's concise synthesis of the reviewed Claude CLOUD Sonnet research (`c1researchv2focus1`, corrected by `c1researchreview1`, cloud docs HEAD `36826c97ec0bd183d4af0e5c1d2d0d05a1e389c4`). It is not a byte-for-byte import of that cloud documentation commit. No model, server, training or candidate accuracy/latency result exists.

## Scope and decision

V2 concentrates on cm1 custom non-Paddle OCR and cm2 PDF compatibility. cm3 melody and cm4 tablet reader/ink/wink are deferred to V3. Use primary-source research and a discriminating experiment when a hypothesis fails; automatic Arena escalation is retired. Existing approved data, compatibility and performance gates in [the parent plan](V2_1_OCR_ENGINE.md) remain binding.

Investigate deterministic staff/band proposals plus a compact sequence recognizer with CTC, initially embedded in the existing API process. This reuses staff-aware OpenCV geometry and avoids extra image/RPC copies. A separate internal worker is an isolation alternative, with all RPC, memory and scheduling costs measured. A compact learned detector is an alternative only if independently labelled development data shows that deterministic proposals cannot recover enough occurrences. Whole-band recognition and residual-ink checks are diagnostics, never independent truth.

The candidate must import/use no Paddle weights, service or fallback. The separately selected baseline can retain Paddle. Unknown/manual title is already approved; keep `song_title` compatible and disclose reduced automatic title capability. PDF integration must handle unknown titles without assuming cm1 succeeds.

## Findings and rejected assumptions

- At the checked source head, `/detect` explicitly passes `use_ai_fallback=False`. The hybrid helper also defaults to `ai_provider="mock"`; its fallback Boolean alone does not imply an external AI request. Production runtime has not been measured or inspected here.
- The crop covers `max(prev_bottom, top - max_above) <= y < min(H, top + pad_below)` with image Y increasing downward. Its actual missed-chord rate is unmeasured. Do not reverse the boundary or infer a most-common failure from code alone.
- Existing source comments record lost small accidentals when downscaling more aggressively. That is a historical warning to preserve accidentals/extensions/slash bass, not a fresh measured improvement.
- A valid-looking grammar output can still be wrong. Confidence/abstention needs development-data calibration; no language-model or OCR output may create held-out truth.
- A retained processing share of 35% does not disprove a 50% elapsed-time target. Use paired per-request work and comparable end-to-end measurements; never subtract marginal medians. A lower bound must identify unavoidable retained work and its uncertainty. A timing failure of one model does not refute every possible architecture.
- A baseline above 98.5% still leaves the independent 99% precision/recall gate open. Stage recall products are diagnostics, not a universal per-stage accuracy requirement.

## Ordered work and evidence gates

| Stage | Work | Completion / stop condition |
| --- | --- | --- |
| S1.5 | Decompose baseline preprocessing, detection/recognition, title and outer API costs using existing timing fields. Use cleared synthetic diagnostics and fixed runtime/model hashes; no tuning. | Report paired samples, warm-up, failures, CPU quota, p50/p95 and dispersion. Controlled cloud CPU is distinct from production/HF. Missing models/host evidence means NOT RUN. A synthetic diagnostic cannot freeze the real accuracy baseline. |
| S1.6 | Independent Opus tester authors the occurrence/scorer contract and calibration cases, including repeats, duplicates, wrong accidentals/slash bass, geometry and page failures. | Second independent review before freezing matching/normalization and hashes; no production parser or model as oracle. Calibration is not musical accuracy. |
| Data readiness | Rights-cleared independent real recaptures; two independent human readers; frozen assets/labels and baseline. | At least 60 pages, 3,000 chord occurrences and 200 staff systems. Purchased/free-download scores are not assumed training permission. No owner score upload. |
| S2 | Only after readiness: own training sources, recognizer, decoder and any justified detector. Tune on development material only. | Missing rights/truth/baseline/scorer -> HOLD. No paid compute or hosting changes inferred. |
| S3 | Candidate inference/owned OCR service through the existing compatibility boundary; explicit limits and content-free errors. | Weight budget <=50 MiB; OCR process peak RSS <=1 GiB; validate real CPU/ABI/concurrency. API wiring stays cm2-owned. |
| S4 | Frozen candidate, one independent real holdout decision and paired timing. | Exact occurrence precision AND recall >=99%; warm end-to-end p50 <=0.50 x baseline, p95 <=baseline, unchanged per-sheet regression gate. Failure -> research/replan or HOLD; no tuning on holdout. |

All accuracy/time/RSS/proposal-recall values for the custom candidate are UNMEASURED. The historical single CI sheet Paddle result (12/12, 6.2 s) is not a held-out result or current production p50. Existing 91 independent preparation tests and green Ubuntu CI are evidence for preparation only.

## Primary sources and limits

Reviewed on 2026-10-15: [CRNN paper](https://arxiv.org/html/1507.05717v1) supports a convolutional/recurrent sequence-recognition design; [original CTC paper](https://www.cs.toronto.edu/~graves/icml_2006.pdf) defines alignment-based sequence labelling and approximate best-path decoding. Neither proves this project's accuracy or speed.

[ONNX Runtime thread guidance](https://onnxruntime.ai/docs/performance/tune-performance/threading.html) supports explicitly bounding thread pools and measuring the CPU cost of spinning. It does not establish our NumPy ABI or concurrent-session behavior. Exact package/wheel/model licenses and hashes remain adoption checks. Primary pages blocked in the research sandbox were separately checked by the orchestrator; no successful cloud fetch is invented.

## Policy and reporting

Do not edit privacy/terms in this feature. Map actual changes to privacy §§1-2 (purpose/items), §§4-5 (retention/destruction), §7 (no secondary training use), §§8-9 (actual processors/overseas routing), §10 (security/content-free telemetry), §§12/14 (any coordinated local storage/rights), and §20 (publication). No new external OCR recipient is proposed. Never put score images/text, titles, filenames, ink, camera content or credentials into errors, breadcrumbs or tags.

Keep PR #58 Draft. Report active cm1/cm2 PR progress, findings, recurring troubleshooting and noteworthy results in a short owner table. No merge, production deployment or history rewrite.
