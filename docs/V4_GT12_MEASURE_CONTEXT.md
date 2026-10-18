# GT-12: source-only measure-context review

**Combined rendering: BLOCKED — WAITING_FOR_OWNER_SOURCE_CONFIRMATION.** The complete source review materials are prepared. No A/G chord-and-lyric canvases were generated. This is the authorized fallback when source confirmation is unavailable, not a completed context renderer.

## Scope and provenance

Base: `9d83c868b350b4435a8d775be655e0b23fc6cedd` (GT-11). Branch: `experiment/v4-gt12-measure-context`; worktree: `/private/tmp/capomatic-v4-gt12`. The final immutable commit SHA is provided in delivery. No experiment branches were merged.

Fixed source: original Bb PDF page 2, printed measure 3. Targets remain A major (-1 semitone) and G major (-3). No target reference-page content was used to read, repair or position source material. No PDF extraction, recognition or OCR rerun was needed.

The original RGB source raster remains 2520×3564, SHA-256 `eced6bfc4481924efad36d5be300c40f568e3f8678df568940cd5fad894a43de`. GT-11's inventory and all frozen prediction hashes were verified, and the full GT-11 output file tree was hash-compared before/after this preparation. The local GT-12 validation summary binds every GT-11 output hash; it does not overwrite historical evidence.

## Original-resolution review image

The new crop is page bbox **[1300,330,1860,720)**, 560×390 pixels, containing the full measure's horizontal bounds [1374,1782], chord region, both visible Korean lyric rows, neighboring notation on both sides and margin below the lyric baseline. This fixes GT-11's lower-row clipping without editing any historical crop. Bounds were selected from source pixels only, not reference targets.

`original-bb.png` is the exact source crop. `source-review-sheet.png` adds an 82px header outside it; the source image below that header remains pixel-identical and unscaled. Crop-local `(x,y)` maps to original page `(x+1300,y+330)`. Review-sheet source pixels start at sheet y=82. This crop is review context, not a text-ownership or protection mask. The agent opened the actual sheet and confirmed both visible lyric rows fit inside it; that inspection is not independent human transcription.

## Source checklist and evidence boundaries

| Item | OMR / agent observation | Owner-confirmed |
|---|---|---|
| Rest | Quarter rest, onset 0, duration 1 | Pending |
| First note | Bb3 (`B-3`), onset 1, duration 1 | Pending |
| Second note | C4, onset 2, duration 1 | Pending |
| Third note | F4, onset 3, duration 1 | Pending |
| Attachments / additional symbols | No extra required attachment identified in recognized stream; owner must check visible source | Pending |
| Chord | Agent reads candidate F; selected-measure OMR harmonies: 0 | Pending, including quality/inversion/alteration |
| Upper lyric row | Agent candidate: 주 / 님 / 의 | Pending |
| Lower lyric row | Agent candidate: 사 / 막 / 의 | Pending |
| Lyric association | Candidate: each row maps left-to-right to the three notes, not the rest | Pending |

Durations/onsets above are quarterLength values from GT-11's recognized stream. Four units do not independently establish the printed time signature. Source event IDs, unspecified voice, detected physical positions and unverified status are retained in `source-checklist.json`.

Owner replies retained as unverified review candidates: **1**. Visually confirmed source submissions: **0**; no source fields are visually confirmed. The owner explicitly returned `OWNER_REVIEW_CANDIDATE`, `SOURCE_COMPLETENESS_UNVERIFIED`, `F_MAJOR_CANDIDATE / EXACT_SUFFIX_UNVERIFIED`, both lyric rows as `OWNER_PROPOSED_NOT_VISUALLY_VERIFIED`, and `OWNER_VERIFIED_SOURCE: PENDING_VISUAL_CONFIRMATION`. The reply is retained verbatim as untracked `owner-review-candidate.txt`, with its SHA bound in the checklist. It confirms no source event, exact chord suffix, lyric reading or absence of additional printed symbols. No blank form, agent observation, candidate reply or OMR agreement is promoted to a visually confirmed human source label.

Any later visual confirmation must also be retained as received and bound to this image/checklist identity, without replacing the candidate reply. Its normalized confirmed fields must remain separate from candidates and OMR. A sufficiently confirmed reply could carry **OWNER_VERIFIED_SOURCE**, never **INDEPENDENT_GROUND_TRUTH**. Independent ground-truth labels remain 0. This uncertain reply leaves all confirmed source fields unresolved.

## Chord and lyric rendering gate

`chord-audit.json` records the missing OMR chord candidate and pending human confirmation. The conditional F→E / F→D mapping is the requested future transposition, not a recovered source chord or a rendered prediction. Quality, bass and alterations must be confirmed before using that mapping.

`lyric-audit.json` records zero selected-measure MusicXML lyric items and the unconfirmed agent candidates. Exact syllables, both rows and syllable-to-note associations are required human inputs. A later authorized standalone canvas would newly typeset confirmed Korean text; it would **not preserve original lyric pixels**. No missing words are completed, inferred from targets, translated or paraphrased.

Current three-level state:

| Level | Result |
|---|---|
| SOURCE_RECOGNITION_COMPLETENESS | UNVERIFIED; four recognized events, no owner-confirmed events |
| RENDERING_COMPLETENESS for GT-12 combined canvas | BLOCKED; no combined prediction exists |
| VISUAL_QUALITY for GT-12 combined canvas | UNVERIFIED; no combined image to inspect |

The GT-11 music-layer renderer and its contracts are unchanged and available for reuse after sufficient source review. Newly typeset Korean font/baseline placement, chord width/placement and their collisions have not yet been validated or implemented in this preparation pass. Any additional owner-identified notation must also be accounted for before a complete-rendering claim.

Text verification would not authorize source ink removal, protection-envelope relaxation, lyric-pixel compositing or promotion of Track A PARTIAL ownership. No GT-13/14 or production milestone is authorized by these review materials.

## Normalized review awaiting explicit owner confirmation

A subsequent submitted review is classified **ASSISTANT_VISUAL_REVIEW / NOT_INDEPENDENT_GROUND_TRUTH**. It is retained separately, without changing the original owner candidate or prior GT-12 artifacts. It is not an owner confirmation. The source review sheet SHA-256 is `3ff4e49da99865ee93dcd1bea483d267cdfedc0377ef7bb84673ef78943e2ccf`; its image bytes remain unchanged.

The normalized checklist at `gt12-output/owner-confirmation/normalized-source-checklist.json` presents these items for explicit owner confirmation:

| Scope | Review statement, still pending owner confirmation |
|---|---|
| Events | Quarter rest, Bb3, C4, F4, each quarterLength 1; frozen OMR onsets 0, 1, 2, 3 |
| Pitch context | Absolute names rely on existing source clef/key context, not visible within this crop |
| Chord | Visible F, interpreted as major; no visible suffix, slash bass or alteration |
| Chord placement | Preserve its source location near the measure beginning; do not attach it automatically to the first pitched note. Exact source placement coordinates still require source-only measurement. |
| Upper lyrics | 주 / 님 / 의, associated respectively with the three pitched notes |
| Lower lyrics | 사 / 막 / 의, associated respectively with the three pitched notes |
| Initial rest | No associated syllable in either row |
| Additional notation | No accidental, tie, slur, beam, flag or articulation identified in the visible target measure; neighboring measure content is excluded |

The exact submitted assistant review, the normalized record and a preservation check are retained under the untracked `owner-confirmation/` directory. All previous GT-12 file hashes, including the original owner candidate, remain unchanged. Every normalized owner-confirmation field is false/pending; independent ground-truth labels remain 0. The F→E/D mapping remains conditional, and neither predicted image is generated. A later explicit owner confirmation may establish OWNER_VERIFIED_SOURCE within its stated scope; it cannot establish independent ground truth or authorize source ink removal.

## Outputs and use

Untracked output directory: `/private/tmp/capomatic-v4-gt12/gt12-output/`.

- `source-review-sheet.png`: labeled native-resolution source review.
- `original-bb.png`: untouched source crop.
- `source-checklist.json`: separated OMR, agent and pending owner fields.
- `owner-review-candidate.txt`: actual owner candidate reply, not a source-confirmation attestation.
- `chord-audit.json`, `lyric-audit.json`, `completeness-report.json`: blockers and missing source recognition.
- `semantic-regression.json`, `validation-summary.json`: regression results and historical hash binding.

`predicted-a.png`, `predicted-g.png` and `comparison-contact-sheet.png` are deliberately absent because source verification is pending. An earlier exploratory source-only crop is preserved untracked in `gt12-initial-source-review/`; the pre-reply packet is retained in `gt12-pre-owner-review/`. Final review images have the same bytes as the pre-reply packet; only candidate-submission provenance was added to the final checklist/audits.

Reproduce preparation only into a new output directory, with the frozen local GT-11 artifacts present:

```sh
python -m scripts.research.gt12_measure_context --out NEW-review-output
# Optional: retain an actual candidate reply without accepting it as confirmation.
python -m scripts.research.gt12_measure_context --out NEW-review-with-candidate --owner-candidate ACTUAL-reply.txt
```

The helper refuses to overwrite an existing directory. It prepares evidence only: it neither authenticates a filled form as visually confirmed human evidence nor unlocks rendering. To continue GT-12, obtain actual visual confirmation, retain that reply separately, validate its complete scope, then implement and test the confirmed chord/Korean-text layer using GT-11's unchanged note masks. Reference targets must not supply any missing source answers.

## Validation and preservation

Targeted regressions: **187 passed, 1 skipped** (existing external MuseScore dependency). The test command covered GT-12, GT-11, GT-04, GT-05A, GT-06, both GT-07 flag suites, and V3 music/gate regressions. New tests check pending/fabricated forms cannot authorize rendering, verbatim candidate-byte retention without source confirmation, fixed measure identity, native crop/sheet pixel equality, deterministic images, explicit image mode, invalid crop geometry and refusal to overwrite evidence.

Unchanged V3 transposition and full musical-integrity guards were also executed for A/G in memory and against the frozen GT-11 serialized targets. All passed: 37/37 measures, 169/169 recognized events, 7/7 recognized harmonies, no issues. These results do not validate an F chord missing from recognition or certify source completeness. No new score prediction or renderer run was performed. Historical hashes remained unchanged. `git diff --check` and research Python formatting are checked before commit; no Full Acceptance.

No V1/V3 or API/frontend changes, source PDF/raster edits, original music erasure, protection-mask changes, Track A promotion, integrity-gate relaxation, production B2, merge or deployment occurred.
