# GT-13A.6 cross-system tie source verification

**FULL_SYSTEM_INCOMPLETE — awaiting explicit destination confirmation.** Raw persisted OMR, the frozen graph and MusicXML agree on the m4→m5 tie candidate. Source-only review images and one owner confirmation question are prepared. No real-score continuation or completed tie is rendered while the destination remains unconfirmed.

Base `20af28ea54d45d980da57ec3084790a2001b4d4e`; branch `experiment/v4-gt13a6-cross-system-tie`; worktree `/private/tmp/capomatic-v4-gt13a6`. Final SHA is supplied with delivery. This is offline research, not production B2 or source-ink replacement.

## Separate verdicts

| Level | Result |
|---|---|
| SOURCE_VERIFICATION | OMR_SUPPORTED_CANDIDATE_PENDING_OWNER; outgoing start previously owner-confirmed, destination not yet confirmed |
| TIE_RENDERING_COMPLETENESS | BLOCKED_REAL_SCORE_CONTINUATION; synthetic split-segment geometry tested only |
| VISUAL_QUALITY | UNVERIFIED for actual target-score ties; source review packet and synthetic control inspected by assistant |

No new independent human ground-truth labels exist. The previous owner response **“아직 미확인 — 목적지는 보류”** remains unchanged. One new source-only question asks whether the final Bb3 in printed m4 ties to the first Bb3 whole note in printed m5. The collection permits OWNER_CONFIRMED, OWNER_REJECTED or OWNER_UNCERTAIN; no answer is manufactured or inferred from silence. If a response arrives later, it must be preserved verbatim and bound to this packet in a separate record, leaving the pending checklist immutable.

## Original-record evidence

Original Bb PDF page 2 raster SHA-256:
`eced6bfc4481924efad36d5be300c40f568e3f8678df568940cd5fad894a43de`.
Original PDF SHA-256 (rechecked against the retained PDF):
`1cc64756c0ce47b1db0ea6ac21eefe4685097a04cd4589f954afc712afb605fd`.
The retained provenance identifies page 2, rasterized at 72 dpi to 2520×3564 pixels. The PDF page is 2520×3564 points; native crop here means unchanged frozen raster pixels, not a newly rendered higher-DPI PDF. The original frozen raster and OMR input have the same hash. No PDF page was rerendered and no A/G reference image was opened for this review.
Existing recognized.omr SHA-256:
`857c787b23d4244cb17fbcc9de80c8a3bbfe7de606aabf818643be1fbf9f6638`.

The extractor reads `sheet#1/sheet#1.xml` directly from that archive and compares its attributes and cubic control points to the frozen visual graph. It does not rely solely on an earlier JSON summary:

- `slur id=4818`, `tie=true`, `above=false`, `right-extension=4798`. Raw slur-head relation: source4818→head1852, side LEFT. Head1852 is staff1, pitch-position7, NOTEHEAD_BLACK, bounds `[2346,534,2371,554)`.
- `slur id=4798`, `tie=true`, `above=false`, `left-extension=4818`. Raw slur-head relation: source4798→head1923, side RIGHT. Head1923 is staff2, pitch-position7, WHOLE_NOTE, bounds `[303,884,338,904)`.
- Extension identities are reciprocal attributes of the persisted slurs. They are distinguished from graph-derived extension-edge records; no separate Java relation is invented.
- Outgoing cubic: `(2359.9,557.1), (2368.5,566.5), (2383.4,566.4), (2391.8,556.9)`.
- Incoming cubic: `(276,907), (286.3,918), (303.7,918), (313.9,906.9)`.

This supports a continuation interpretation but does not independently certify printed musical meaning. The original source start/stop notes and two short curves are visible in the packet; assistant observation is not owner confirmation.

The graph-to-semantic mapping uniquely identifies m4 index3, onset15/4, duration1/4, Bb3 START, followed by m5 index4, onset0, duration4, Bb3 STOP. The source context is treble with two flats. Music21 writes Bb3 as `B-3`. Target checks require A3/A3 for −1 and G3/G3 for −3, preserving both durations and START/STOP roles. Frozen serialized target MusicXML agrees with fresh in-memory transposition.

An initial diagnostic comparison included music21's automatic container object IDs, which differ between parses. Those unstable in-memory identifiers were removed from the comparison before packet generation. Endpoint identity is instead based on the bound graph head, physical measure mapping, onset, duration, pitch and tie role; no musical data or guard was changed.

## Source-only review packet

All raw crop files retain native RGB pixels with no scaling, overlay or annotation. Their dimensions, page-coordinate bounds and hashes are recorded in `tie-owner-checklist.json` and checked against exact source crop bytes:

| File | Page bbox, right/bottom exclusive | Size |
|---|---|---|
| source-outgoing-tie.png | [140,390,2430,720] | 2290×330 |
| source-incoming-tie.png | [140,750,1050,1080] | 910×330 |
| source-outgoing-closeup.png | [2300,480,2420,600] | 120×120 |
| source-incoming-closeup.png | [245,840,390,960] | 145×120 |

`source-tie-review-sheet.png` places the unchanged system crops side by side on a 3280×650 labeled review canvas at 1:1 resolution, with both closeups below. It includes clef/key context, the full first system, beginning of the next system and neighboring notes. No A/G reference image or predicted notation appears. The checklist records the current sheet hash and exact placement rectangles; every pasted region is checked for pixel equality. The older stacked review packet remains unchanged in `gt13a6-output/` and is not the current owner review sheet.

For owner review, locate the rightmost note in the left crop (end of the first system), then the first whole note after the clef/key in the right crop (start of the next system). The crop does not print measure-number labels; m4/m5 are the physical measure mapping described above. Inspect the printed curves at those two notes rather than inferring a tie from matching pitches. Answer the single checklist question in the chat with OWNER_CONFIRMED, OWNER_REJECTED or OWNER_UNCERTAIN. The current checklist remains pending; any later answer must be stored in a separate record bound to its review-sheet hash.

## Separately tested renderer contract

[Protocol](V4_GT13A6_TIE_PROTOCOL.json) fixes a research-only geometry contract. The implementation reuses GT-13A.2's `translated_curve` and `curve_mask`: 65-point cubic sampling, width2. It creates **two separate alpha masks**, outgoing and incoming, confined to vertically separated system viewports. It never draws one line across the physical gap.

Each segment needs a declared head anchor and a source-supported attachment offset. The outgoing curve's first point and incoming curve's last point must agree with those declared attachments within 0.5px per axis. Only below-tie direction is supported here. Nonfinite geometry, wrong role, clipping, attachment mismatch and actual alpha contact with supplied unrelated obstacles fail closed. All control points have stroke margin within the viewport, and the output gap is checked for zero ink.

Synthetic tests exercise integer/fractional and positive/negative vertical displacements, deterministic masks, preservation of input geometry, exact attachment residuals, no gap bridge and collision/clipping rejection. These are declared-anchor checks, **not independent optical validation**. The synthetic canvas is labeled SYNTHETIC and is kept outside the owner source packet.

The low-level renderer is a research primitive, not an authorization service. `require_owner_confirmation` explicitly rejects pending/uncertain/rejected/OMR-only statuses before any future real-source caller. This run has no real-source rendering caller. Thus even passing synthetic tests cannot promote the candidate or complete the actual tie.

After destination confirmation, actual target use still needs a validated **incoming whole-note rendering/anchor** and a two-system composition/obstacle contract. Head centers, semantic staff coordinates and actual font attachment anchors must remain separate. A translated source bbox alone does not establish that glyph contract. Existing GT-13A.5 music/lyric masks and the 0.5px notehead criterion remain untouched; no new target notehead is rendered or remeasured in this task.

## Validation

**325 passed, 1 skipped**: all `test_v4_ground_truth_*.py`, paired-ground-truth tests, V3 music/gate tests and V4 integrity tests. Existing skip is external MuseScore availability. No Full Acceptance. The packet generator was also run successfully against the retained inputs, including PDF hash, reciprocal raw relations, endpoint checks, full V3 guards, crop/sheet pixel equality and frozen historical directory checks.

Unchanged full V3 guard passes for A/G in-memory transposition and the frozen serialized targets; full lyric signatures remain equal. Endpoint pitch, order, onset, duration and tie roles are separately checked. A failing semantic control rejects changed pitch, duration or STOP role.

Frozen GT-13A.5 and GT-13A.4 manifests match; their entire artifact directories are hashed before/after. Original source PNG, OMR archive and review crop pixels remain unchanged. `review-freeze.json` binds packet/evidence bytes; later synthetic controls and final validation are explicitly separate follow-up artifacts. Formatting and `git diff --check` pass.

## Outputs and next step

Current delivery directory: `/Users/juahnkim/Documents/Codex/2026-10-19/referenced-chatgpt-conversation-this-is-an-2/outputs/gt13a6-source-review/`.
Required outputs are present: review sheet, outgoing/incoming crops, `tie-source-evidence.json` and pending `tie-owner-checklist.json`. Additional native closeups, semantic results, validation summary and input/review freezes are included. The current packet contains no synthetic-control images or transposed target PNGs. The earlier untracked `gt13a6-output/` directory is preserved separately.

Reproduce with retained historical local inputs, using a fresh output directory:

```bash
/private/tmp/capomatic-v4-venv/bin/python -m scripts.research.gt13a6_tie_review --out gt13a6-new-review
```

Next action is the single requested owner source review. If uncertain or rejected, preserve that result and stop promotion. If confirmed, bind the actual answer to the frozen packet and validate incoming whole-note anchoring before a separately frozen real continuation trial. No full-system completion is claimed.

No source edit, original ink removal, lyric-pixel compositing, protection-mask change, Track A promotion, V1/V3 production change, API/frontend work, merge or deployment. Only research helpers, tests, protocol and report are committed; copyrighted source crops and diagnostic artifacts remain untracked.
