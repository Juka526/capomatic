# GT-15A: source-only owner confirmation packet

The packet is prepared for review, with **zero owner answers received**. It neither changes GT-15 predictions nor promotes OMR or agent candidates. All 20 note/rest events remain `OMR_PROVISIONAL`; lyric, chord and continuation interpretations remain `AGENT_VISUAL_CANDIDATE`.

Base: `08a9af470907f7bb54733585a18f7bd7d509752e`.
Branch: `experiment/v4-gt15a-owner-review`.
Worktree: `/private/tmp/capomatic-v4-gt15a`.
The commit containing this report is the research revision. The task is understood as preparing evidence for explicit source-owner decisions, not generating approvals, new transposed previews or independent ground truth.

## Review scope

The fixed source is the original Bb PDF page 2, printed measures 9–12. Source PNG SHA-256 is `eced6bfc4481924efad36d5be300c40f568e3f8678df568940cd5fad894a43de` (2520×3564 RGB). The existing OMR and visual-graph hashes are verified against GT-15 input bindings. No A/G reference page is read; target prediction bytes are hashed only for historical-preservation checks, not inspected for source reconstruction.

The compact checklist contains **72 unanswered items**:

| Category | Items | Evidence retained |
|---|---:|---|
| Music events | 20 | Pitch/rest, onset, duration, voice, physical bbox, stems, beams, flags, accidental and tie observations; original component geometry and SIG relations |
| Chord or absence review | 4 | m10 Eb, m12 F; m9/m11 no newly printed chord candidates; suffix/bass/alteration and placement remain reviewable |
| Syllable-to-note associations | 20 | Ten upper and ten lower syllables, proposed onsets and head IDs |
| Continuation strokes | 11 | Each individually numbered, native source window, frozen diagnostic dark-support bbox and proposed tie/syllable context |
| Disputed SIG objects | 5 | TENUTO 5833/5841/5902/5903 and ACCENT 5896; unchanged raw observations and relations |
| Tie relationships | 6 | Original curve geometry, chronological START/STOP endpoint candidates and unmodified raw relation order |
| Additional/missing source content | 4 | One explicit completeness question per measure |
| Negative observation | 1 | m10 upper onset 1 has no observed dash; not copied from the lower row |
| Ending/repeat relationship | 1 | Source m8 first ending/backward repeat and m9 open-right second ending; proposed repeat path remains unverified |

A disputed SIG object and a continuation item may refer to the **same physical stroke**. The checklist cross-references their overlapping windows; it does not count them as separate new marks or decide their classification. The five individual object crops and eleven continuation crops contain source pixels only. Exact music articulation versus lyric classification remains unanswered.

The lyric and continuation associations are candidates based on frozen source evidence. Same-pitch OMR tie endpoints help identify the proposed context but do not prove the lyric association. The source review may correct or reject any candidate, identify extra content, or remain uncertain. No source completeness claim follows from internal event totals.

## Packet location and use

Authoritative local packet:

`/private/tmp/capomatic-v4-gt15a/gt15a-owner-packet/`

Start with:

1. `source-only-owner-review-sheet.png`: the existing native third-system crop copied byte-for-byte, with no added marks.
2. `OWNER_REVIEW.md`: Korean checklist, with an empty answer/correction/uncertainty column for every item.
3. `frozen/source-measure-9.png` through `source-measure-12.png`: unchanged source context per measure.
4. `continuation-01.png` through `continuation-11.png`: native individual stroke windows, mapped by `crop-map.json`.
5. `frozen/source-ambiguous-5833.png`, `5841`, `5896`, `5902`, `5903`: original frozen individual object crops.
6. `first-second-ending-native.png`, `m8-first-ending-native.png`, `m9-second-ending-native.png`: native page context and focused ending views.

`owner-approval-checklist.json` contains the structured unanswered review. `per-measure-inventory.json` retains the original per-measure observations plus item-specific evidence. `evidence-verification.json` records the verified inputs and preservation results. `packet-freeze.json` binds every packet file; `docs/V4_GT15A_VALIDATION.json` records its hash without committing score images.

All review crops preserve source pixel values; no target notation or owner answers were added. Previously frozen labeled context sheets are retained unchanged alongside the plain native crops. **The candidate checklist is not blinded:** it intentionally shows OMR observations and agent transcription proposals for owner review. This is not the independent-reader protocol. The owner here means the project owner who explicitly supplies a source-review response in this conversation or an attributable submission. In a later, separately initiated continuation, the actual response must be retained verbatim with its real submission context and bound to this packet. It must not rewrite frozen candidates or manufacture an independent reviewer/signature/timestamp. No response collection or approval promotion occurs in this task.

Suggested Korean response format: `항목 ID: 확인 / 수정(정정 내용) / 불확실(이유)`. A group response must explicitly name the covered item IDs and distinguish confirmed, corrected and uncertain subsets. Blank fields and preparing a packet never count as approval. The owner need not edit JSON.

## Coordinates and preservation

Original page coordinates use x right/y down; integer crop coordinates are source pixel indices, with right/bottom-exclusive crop boxes. Raw OMR floating geometry is preserved separately. All native crops have scale 1, original RGB mode, exact source-region dimensions and byte-identical decoded pixels. Cropping creates diagnostic files only; no source pixel is edited.

The original GT-15 owner packet is copied intact into `frozen/`, including its earlier manifest and metadata. The standalone review sheet has the same file SHA as the original third-system native crop. New native crops have their own hashes and page-coordinate maps. Diagnostic dark-support bounds are not exact lyric ownership or removal masks.

GT-14E and GT-15 prediction freeze files, GT-15 validation bindings, source PNG/OMR/graph hashes and original owner-packet hashes are verified before generation. Complete historical output-directory hashes are compared before and after generation. The source and historical render masks/predictions remain unchanged. No historical renderer is executed.

To reproduce in a fresh directory, with preserved local historical inputs available:

```sh
cd /private/tmp/capomatic-v4-gt15a
/private/tmp/capomatic-v4-venv/bin/python -m scripts.research.gt15a_owner_review \
  --out /private/tmp/gt15a-new-owner-packet
```

The helper rejects an existing output path and mismatched hashes before preparing the packet. No dependency downloads, OCR, Audiveris execution or new A/G rendering occur. Earlier local development packet directories are not the authoritative packet above and remain untracked.

## Validation and limits

Final targeted suite: **471 passed, 1 skipped**, including nine new synthetic tests. They check fixed coverage, empty answer fields, deterministic checklist generation, immutable input dictionaries, chronological tie ordering without rewriting raw relations, overlap cross-references, fail-closed inconsistent/promoted candidates and rejection of a tampered frozen input before creating output. Native crop hashes/pixel equality and historical preservation are also checked against actual local evidence.

```sh
/private/tmp/capomatic-v4-venv/bin/python -m pytest \
  tests/test_v4_ground_truth_*.py tests/test_v4_paired_ground_truth_01.py \
  tests/test_omr_v3_music.py tests/test_omr_v3_gate.py tests/test_omr_v4_integrity.py -q
```

The skip is the existing external MuseScore-dependent test. V3 regression/guard code is unchanged. No new target semantics or transposition is created in this packet-only phase; historical GT-15 full V3 results are preserved, not relabeled as new human confirmation. Full Acceptance was not run.

The source sheet, first-ending detail and disputed-object 5896 crop were viewed to check packet usability. This was agent inspection of presentation, not a new source classification or independent musical/optical validation.

Status: **OWNER_REVIEW_PENDING**. New owner confirmations: **0**. Independent human labels: **0**. Source recognition completeness remains **UNVERIFIED**. The next action is owner review of this fixed packet; rendering of newly confirmed content requires a separate continuation. No source ink removal, protection-mask changes, ownership promotion, production changes, merge or deployment occurred.
