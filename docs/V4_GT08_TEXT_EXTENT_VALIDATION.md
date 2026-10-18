# GT-08 independent text extent validation

**WAITING_FOR_HUMAN_REVIEW.** The user confirmed that Reader A, Reader B and an independent adjudicator are not assigned. Actual human submissions collected: **0**. Verified primary freezes: **0**. Actual adjudications: **0**. Collection is stopped; no blank form, synthetic unit fixture, software check, OMR support or coordinator observation is counted as human ground truth.

Branch `experiment/v4-gt08-text-extent-validation`, worktree `/private/tmp/capomatic-v4-gt08-text`. Exact starting revision **`feeb33bec47b73d5e32f042bc9a5561944ed6314`** (GT-07A). GT-07B **`f3b808d3fb072d521f516ef9e8f50ef54bd59756`** is read-only input, not merged. [Review contract](V4_GT08_REVIEW_CONTRACT.json) was committed as `14f42e3` before workflow construction. Core validation implementation and exact input identities were committed as `30090379ac6dd8e4e93e7be22800a8a63c97fcda`; the later blank-custody-template addition is included with this report; the final report SHA is in the final handoff and local validation manifest. Use `git log -1 --format=%H -- docs/V4_GT08_TEXT_EXTENT_VALIDATION.md` to identify the report revision.

## Verified frozen evidence

[Evidence binding](V4_GT08_EVIDENCE_BINDING.json) records **39 consumed historical files** and their SHA-256s, with no copyrighted image content. Verification includes:

- Original Bb raster SHA-256 **`eced6bfc4481924efad36d5be300c40f568e3f8678df568940cd5fad894a43de`**, signed GT-01 baseline/reference manifests and existing artifacts.
- GT-07A persisted text-lineage report, source OMR hash, private case linkage, source-support diagnostics and all eight files of the original five-case packet.
- Exact original pixel equality between every existing packet crop and its hash-bound source raster region; images are copied, never re-encoded or reselected.
- GT-06 and GT-07B prediction freezes, source selections, integrity results, unchanged protection definitions and recorded envelope counts.
- GT-07B post-freeze text-support contact report and its 47-coordinate/233-envelope set relationships.

Neither old prediction pixels nor their hashes are regenerated. Source and reference pages are not used to supply review answers. This is post-reference-access workflow preparation, not a blinded accuracy experiment. Historical recognition agreement remains algorithmic evidence, not an independent label denominator.

## Operational source-only handoff

New untracked root: `/private/tmp/capomatic-v4-gt08-text/gt08-output/`.

`reviewer-handoff/source-only-packet/` contains **the same five case IDs and original PNG bytes**, neutral instructions and a new manifest. Native dimensions remain 430×503, 345×423, 109×380, 51×420 and 42×420. The new manifest SHA-256 is **`0fa69a361b41a713979b5736c2b30dae5037e3af30e10dfdef3d4771bb10a217`**. The historical GT-07 packet is unchanged; the new GT-08 response envelope is separate from its old forms, rather than an automatic conversion of old labels.

Three role folders, `A/`, `B/` and `ADJUDICATOR/`, contain distinct blank templates and handoff instructions. The custodian distributes **only the source-only packet plus the recipient's role folder**. Do not distribute this report, evidence bindings, private case map, collision records, OMR data, predictions or other readers' drafts. An adjudicator must not start until both independent primary exports have frozen. No messages were sent and no reviewers received materials during this task.

The private `custodian-receipt-template.json` is a blank form outside reviewer materials and actual-submission directories: all human identity, verification and attestation fields are null. It is not a collected receipt. The private `custodian-case-map.json` retains original page linkage; reviewers receive only crop-local coordinates. The five crops overlap and target a previously selected forensic region. They are not five independent random accuracy samples and do not establish whole-score accuracy.

The response categories are:

| Category | Reader observation |
| --- | --- |
| CONFIRMED_TEXT | Confidently observed printed text-ink pixels |
| CONFIRMED_NON_TEXT | Confidently non-text pixels, including music or background; never editing permission |
| MIXED | Shared/inseparable observed content |
| UNKNOWN | Unreadable, unworked, uncertain boundary/fringe or otherwise unconfident |

Coordinates are native crop-local pixel-index centers: first center (0,0), x right/y down. Runs are **`[row, left, right_exclusive]`** with integer coordinates. Every pixel must have exactly one explicit category; omitted pixels, overlaps, nonfinite/fractional coordinates and implicit rescaling are rejected. `uncertainty_status` and a nonempty explanation are mandatory. MIXED/UNKNOWN must have explicit runs; a no-uncertainty assertion is also explicit. Annotation software may encode a human's own observations but must not infer/classify them. No annotation GUI is supplied; an external human annotation/export workflow is still needed. Manually painting reviewed regions and exporting those observations as RLE is permitted; OCR, threshold-based classification and AI-generated categories are not human observations.

## What submission validation proves

[Review validator](../scripts/research/gt08_review.py) separates three stages:

1. **Schema/geometry validation:** exact packet identity, all five cases once, valid categories, original dimensions, complete explicit pixel coverage, uncertainty and source-only independence declarations. A valid JSON result says **SCHEMA_VALID_NOT_HUMAN_AUTHENTICATED**. An origin string is not proof of personhood.
2. **External human custody:** a real human custodian checks identities, eligibility, exposure/exclusions, separate work and absence of automated classification. A detached signature binds their attestation to the exact raw submission, packet, role, pseudonymous reviewer and external verification-record hash. The trusted public-key fingerprint must be registered externally by the human task owner; the agent must not create keys, attestations or observations. The live policy fingerprint is **null**, so no submission can be frozen now.
3. **Immutable primary/adjudication chain:** raw input bytes, custody attestation, signature and public key are copied unchanged into new role-specific freeze directories. Files are created exclusively/read-only; a repeat cannot overwrite them. Hash/signature checks detect subsequent modification. A/B identities must differ; a third adjudicator must differ from both and the custodian, reference both actual freeze hashes and sign after both freezes. Original A/B observations remain intact.

Cryptography proves custody under the externally trusted custodian, **not** that a person exists, reviewed independently or classified correctly. Those facts require external human verification and independently retained receipts. A self-signed key chosen by the agent, fabricated human declaration or software-generated score labels are not admissible. This task registers no trust key and supplies no human attestations.

Overlapping-case contradictions are counted rather than silently resolved. MIXED/UNKNOWN and conflicts keep adjudicated extents partial/unresolved. No blank fields or observations are silently filled. Synthetic test identities, ephemeral keys and toy colored images exist only inside temporary unit-test directories, never the live collection or score packet.

## Commands and current collection state

Preparation was run once:

```bash
python -m scripts.research.gt08_prepare --out gt08-output
python -m scripts.research.gt08_review status \
  --root gt08-output \
  --packet gt08-output/reviewer-handoff/source-only-packet
```

It returns WAITING_FOR_HUMAN_REVIEW, zero verified primaries/adjudications, no collision audit and no composition authorization. `submitted-labels/` and `adjudication/` are **empty**. Blank templates live only under reviewer-handoff and are rejected as submissions.

For a future, separately authorized real-human collection, the human task owner first registers an externally verified custodian key fingerprint in `collection-policy.json` (currently deliberately read-only/null). Preserve its prior version and independently retain the registration. Do not let an agent populate trust, identities or observations. Raw signed exports and private identity evidence stay outside commits. The receipt fields are validated by `signed_custody` and include packet/submission hashes, role/person/custodian tokens, UTC verification time, explicit human/independence/non-automation checks and an external verification-evidence hash. The human custodian can sign the exact receipt bytes externally using:

```bash
openssl dgst -sha256 -sign CUSTODIAN_PRIVATE.pem \
  -out HUMAN_RECEIPT.sig HUMAN_RECEIPT.json
```

This was **not executed for any real submission**. Private keys never belong in this repository. Future validation/freezing commands are:

```bash
python -m scripts.research.gt08_review validate \
  --root gt08-output --packet gt08-output/reviewer-handoff/source-only-packet \
  --role A --submission ACTUAL_RAW_READER_A.json
python -m scripts.research.gt08_review freeze \
  --root gt08-output --packet gt08-output/reviewer-handoff/source-only-packet \
  --role A --submission ACTUAL_RAW_READER_A.json \
  --receipt HUMAN_RECEIPT.json --signature HUMAN_RECEIPT.sig \
  --public-key EXTERNALLY_VERIFIED_CUSTODIAN_PUBLIC.pem
```

Repeat separately for B. Only after both freezes may the independent adjudicator receive both unchanged originals and source-only images, then use role ADJUDICATOR with its own actual export/receipt. These commands are a runbook, **not permission to invent or run collection now**. Invalid exports remain at their original locations for human correction/versioning; the tool does not normalize or overwrite originals. A partial/failed freeze is not accepted merely because a directory exists.

## Collision audit remains pending

`collision-audit/pending.json` preserves the verified historical envelope measurements:

| Frozen target | Envelope pixels awaiting independent classification | Confirmed text | Confirmed non-text | Ambiguous contacts |
| --- | ---: | --- | --- | --- |
| GT-06 A | 1,982 | UNKNOWN | UNKNOWN | UNKNOWN |
| GT-06 G | 2,026 | UNKNOWN | UNKNOWN | UNKNOWN |
| GT-07B A | 24 | UNKNOWN | UNKNOWN | UNKNOWN |
| GT-07B G | 233 | UNKNOWN | UNKNOWN | UNKNOWN |

GT-07B G's **47 source text-support candidate coordinates** remain processed evidence, not independently confirmed text. No adjudicated raster comparison was executed. The status tool intentionally never turns valid schema or custody into contact counts. A later actual post-adjudication run must resolve page mapping/overlapping observations conservatively and compare real adjudicated extents against the unchanged frozen masks, retaining UNKNOWN/conflicts. That conditional comparison is not completed or claimed here.

## Composition readiness: two independent requirements

**Original text preservation: UNPROVEN.** No independently verified extent labels exist; absence of labels is not a vacuous preservation pass. Confirmed-text contacts remain UNKNOWN.

**Old music removal/replacement: NOT AUTHORIZED.** Text observations cannot prove ownership of heads/stems/beams, staff crossings or residual source music. Track A still requires COMPLETE ownership; PARTIAL groups gain nothing from text classification. No envelope is tightened, shrunk, removed or bypassed. Even later fully adjudicated text would not authorize erasure or composition. A future trial needs its own explicit authorization, preregistration, complete source-removal evidence and outside-mask pixel-integrity proof.

## Validation and next action

Final targeted GT-01–08/V4/V3 music/gate tests: **416 passed, 1 skipped** (existing external MuseScore dependency). Thirty-four new GT-08 tests use only synthetic images/identities/keys: packet/coordinate binding, coverage, uncertainty, no defaults, AI/exposure rejection, external trust/signatures, raw-byte preservation, independent freezes/adjudicator chronology and overlap conflicts. Mechanical custody tests do not establish real human evidence. No Audiveris, OCR/model, renderer, Full Acceptance or historical prediction rerun.

Formatting and `git diff --check` pass. Local validation metadata records final SHA, test log and handoff hashes. Final preservation checks cover the historical GT-02 111-case packet and GT-03 14-case pilot; neither is rewritten or distributed with prototype answers. No copyrighted score image or identifying reviewer information is committed.

Before collection, the human task owner must establish reviewer eligibility and document expertise, identity checks and exclusions. Required declarations exclude project/coordinator participation, prior prediction/OMR/coordinator exposure, automated classification and premature access to another reader’s labels. The custodian must independently verify these declarations; a checked form alone is insufficient. An annotation/export tool, external trust-registration procedure and registration-record location remain operational prerequisites, not completed work. No automated trust-registration command is supplied.

After actual adjudication, a separately executed collision-audit implementation and its acceptance review are still required; no end-to-end composition-readiness workflow is claimed. Local status and preservation metadata are at `gt08-output/validation-summary.json`; run commands from the worktree stated above.

Next action is outside the algorithm: assign eligible independent Reader A/B and a separate adjudicator, establish the real human custodian and controlled source-only distribution, then obtain actual raw submissions. Until then the exact decision stays **WAITING_FOR_HUMAN_REVIEW**.

No V1/V3 production behavior, integrity gate, protection mask, source PDF/raster, ownership rule, production B2, V4 API/frontend/runtime route, merge or deployment is changed. No composition or original-music removal is authorized.
