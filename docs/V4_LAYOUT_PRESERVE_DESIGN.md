# V4 Phase 1: layout-preserving selective reconstruction

Status: **offline graph/mapping foundation only**. V3 engineering acceptance remains
CLOSED / PASS; public production release remains HOLD. This work adds no route,
frontend, production flag, replacement-symbol renderer, erasing, merge, or deployment.
The starting revision is `11c686b080260b804d91b7035e232f37a818d429` (merged PR #62).
V1 and V3 runtime files are unchanged.

## Goal and output boundary

The original page is the visual source of truth. Preserve its title, composer,
lyrics, copyright, watermark, footer, margins, line breaks, typography and spacing.
Only music objects whose appearance must change with transposition will eventually
be reconstructed. MuseScore's full-page re-engraving changes those layout details;
it remains the existing V3 output and a future fallback, not the V4 output.

Phase 1 establishes whether recognized semantic events can be linked reliably to
visual objects before any pixel editing is attempted:

```
V3 validation/rasterization -> V3 Audiveris -> recognized MusicXML + .omr
                                                 |                 |
                              V3 cleanup/transposition       VisualScoreGraph
                                                 |                 |
                                           semantic/visual matcher
                                                      |
                                           immutable LayoutEditPlan
                                                      |
                                     JSON + developer annotation overlay
```

Coordinates refer to the exact raster supplied to Audiveris. This may be a V3
300-dpi PDF raster or an upscaled image; it is not necessarily the upload's native
pixel grid. Phase 1 keeps that raster, checks its dimensions, and never rescales
coordinates onto another image. A future native-resolution output needs an explicit,
verified inverse raster transform.

## VisualScoreGraph and Audiveris evidence

`backend/omr_v4/visual_graph.py` defines typed pages, systems, staves, measure stacks,
slots, symbols, relations and protected regions. Symbol keys are sheet-qualified
Audiveris IDs, so IDs reused on another sheet cannot collide. Systems, measures,
parts, staves and slots have separate identity domains. Duplicate IDs fail closed.

Implemented visual categories:

- Heads and head-chords, including staff pitch, shape, bounds/pivot, grade and
  contextual grade; stems; beams, beam hooks, small beams and beam groups; flags.
- Accidentals, augmentation dots, ledgers, keys/key alters, clefs and available
  time signatures. Rest nodes are retained but are not pitched-note candidates.
- Slurs/ties with their original cubic control points, endpoint relations and
  extension references.
- Words, sentences, lyric items/lines, locations, explicit text roles and bounds.

Staff lines remain full polylines. Local interline is derived from the five staff
lines rather than applying the sheet's scale to small staves. System bounds enclose
staff lines; measure bounds combine stack left/right with system vertical bounds.
Slot times are exact `Fraction` quarter lengths (Audiveris stores whole-note units).
The original staff and measure/stack XML is retained, including ledger lists and
headers; symbol and relation XML retains fields not yet interpreted.

The parser was checked against the V3-pinned Audiveris commit `7a36078`, particularly
[SigValue](https://github.com/Audiveris/audiveris/blob/7a36078/app/src/main/java/org/audiveris/omr/sig/SigValue.java),
[Measure](https://github.com/Audiveris/audiveris/blob/7a36078/app/src/main/java/org/audiveris/omr/sheet/rhythm/Measure.java),
[SlotVoice](https://github.com/Audiveris/audiveris/blob/7a36078/app/src/main/java/org/audiveris/omr/sheet/rhythm/SlotVoice.java),
and [Jaxb geometry adapters](https://github.com/Audiveris/audiveris/blob/7a36078/app/src/main/java/org/audiveris/omr/util/Jaxb.java).
Current SIG `inters` and `containment` edges are supported, along with legacy
`inter-defs`, inline measure definitions and explicit notes/beams/stem reference lists.
`head-stem`, `beam-stem`, `alter-head`, `augmentation`, `double-dot`, `flag-stem` and
`slur-head` relations are preserved. Unknown relation types and unknown SIG nodes
remain inspectable; unknown node categories are reported.

All definitions are indexed before relations are resolved. Staff numbering is derived
from Audiveris staff IDs within a part, not the XML child order. Measure IDs join
stacks explicitly; there is no positional fallback when IDs disagree. Voice slot
`BEGIN` entries establish onsets; `CONTINUE` entries never create new note onsets.

Limits: 64 MiB per XML member, 256 MiB archive/uncompressed aggregate, 200 archive
members, bounded XML depth/node count, and V3's 40-million-pixel raster limit. No
archive paths are extracted. DTDs/entities, alternate-encoding bypasses, duplicate
identities, malformed dimensions and unusable archive structure are rejected.
Invalid optional geometry is quarantined and counted, never partly reused as valid
geometry. Missing optional geometry remains missing and yields diagnostics. Raw XML
is evidence only, never a fallback source of unchecked coordinates.

## Semantic-to-visual matching

`matcher.py` reads V3's recognized MusicXML into pitched events with part, original
part ID, measure number and index, staff, voice, exact offset/duration, written pitch,
chord membership and member index. It handles divisions, backup/forward, clefs,
chords and staff-specific key attributes. music21 supplies written pitch names and
diatonic note numbers. The clef establishes the expected Audiveris staff pitch;
there is no assumption that every staff is treble clef.

Evidence is applied in this order:

1. Exact measure/stack number and explicit `P<number>` logical part ID (or an
   unambiguous single-part score). Arbitrary multi-part export IDs remain unresolved.
2. Staff identity within that part.
3. A unique nonsuspicious `BEGIN` slot with the exact time offset.
4. Complete head-chord membership, including all chord members' staff pitches.
5. The source note's written diatonic staff position under its clef.
6. X ordering for deterministic candidate presentation, followed by the head's
   contextual grade (or grade) as a reported confidence value.

A confident result requires one complete candidate and no competing plausible
candidate. A global collision pass prevents two semantic notes claiming the same
head, including conflicts with unresolved candidates. Candidates with incomplete
slot/chord evidence remain AMBIGUOUS even if there is only one. An event with no candidate is
UNMATCHED. Every unused visual head is reported, including ambiguous candidates.
No Euclidean-nearest fallback, grade tiebreak, or greedy assignment is used.

Voice IDs are recorded but advisory: their export correspondence is not yet proven
strong enough to disambiguate unisons. X proximity also cannot resolve a musical
tie. Grades are Audiveris recognition scores, **not calibrated match probabilities**.
Written chromatic spelling comes from MusicXML; staff pitch checks its diatonic
position, not the independent correctness of each accidental. A match is evidence
of correspondence, not proof that OMR recognized the score correctly.

## Transposition and immutable edit intent

`plan.py` receives the recognized and V3-transposed semantic streams. It rejects
changed event identity, rhythm, staff or chord membership before pairing notes.
It never chooses an interval or an enharmonic spelling itself. For each matched note:

```
diatonic_steps = target.diatonicNoteNum - source.diatonicNoteNum
target_x = source_x
target_y = source_y - diatonic_steps * staff_interline / 2
```

A chromatic change can therefore have zero vertical displacement (e.g. F-sharp to
F in D -> D-flat). Per-note displacements can differ across key regions and cannot
be replaced with one page-wide vertical translation. V4.0 has no horizontal reflow.

Frozen dataclasses and tuples carry note moves, beam components, slurs/ties, key
regions, protected regions, intersections and metrics. Sorted plan serialization has no
timestamps; the CLI replaces unstable export part IDs with deterministic labels, uses rational strings and rejects NaN/Infinity.
The page dimensions are included. A plan never authorizes pixel editing.

Note plans retain adjacent heads/chords, stems, beams, flags, dots, accidentals,
ledger candidates and curves, with conservative source and swept bounding regions.
Audiveris has no serialized direct ledger-to-head relation; horizontal/staff overlap
is recorded as a candidate association with an explicit blocker, not asserted as a
semantic match. These bounding regions are deliberately broader than future masks.

Beam components follow only musical connectivity edges, not text or slur edges.
Each includes heads, stems, beams and per-head pixel deltas. Complete equal deltas
produce `UNIFORM_DELTA`; complete unequal deltas produce `RECONSTRUCT_REQUIRED`;
missing head correspondence produces `UNRESOLVED`. Uniform displacement alone is
not permission to translate a beam: geometry and attachments still need validation.

Slur/tie plans retain cubic curves unchanged and record LEFT/RIGHT endpoint source
positions, target positions and deltas. Missing endpoints and cross-system
extensions remain unlinked. Key plans join visual measure membership, staff and
source fifths to semantic regions, recording the target key/fifths from V3 output.
Missing visual C-major signatures are explicit unmapped regions. Repeated system
signatures may map to an active semantic key without creating a new key change.

## Protected pixels and future rendering

Every recognized lyric and non-chord text object is protected. Explicit roles
identify title/composer/copyright/footer where Audiveris provides them; otherwise
text stays conservatively protected. Only an explicit chord-name classification
exempts chord text. Missing text bounds block future approval. Unrecognized text,
watermarks and other unmodeled pixels remain a known protection gap.

**No edit mask may touch a protected region. Pixels outside approved edit masks
must remain unchanged.** Phase 1 reports intersections between conservative source/
target sweep regions and text bounds. Counts are edit-region/protected-region pairs,
so a lyric item and its enclosing line can produce separate intersections. An empty
intersection list does not prove safe rendering: these are diagnostic envelopes,
not segmentation masks, and OMR may miss text.

Future implementation steps, intentionally absent here:

- **Editable/protected masks:** derive object-specific masks from verified symbols,
  union all required connected objects, subtract protected regions, then reject any
  incomplete or conflicting mask. Retain exact pixel hashes/diffs outside masks.
- **Staff-aware inpainting:** recover background/staff ink locally using original
  staff polylines and nearby pixels. Restore interrupted staff lines without
  altering lyrics or background texture. A white rectangle is not a general eraser.
- **Local symbol rendering:** evaluate SMuFL-compatible Bravura glyphs at the local
  interline and source weight. Align anchors and account for stroke widths. No font
  binary is added in Phase 1.
- **Stems, beams and flags:** reconstruct complete groups when head deltas differ;
  enforce stem directions/lengths and beam slope/attachment constraints. Uniform
  groups still need collision checks and source-style matching.
- **Accidentals and key signatures:** use the existing semantic target spelling and
  key regions, then determine required cancellation/placement and collisions. Zero
  vertical movement can still require a changed accidental or signature.
- **Ledger lines:** establish explicit head association, remove obsolete segments,
  generate newly required segments and avoid merging unrelated notes' ledgers.
- **Ties/slurs:** transform Bézier endpoint/control geometry subject to attached
  note movement, tangent/clearance constraints and cross-system continuity. Never
  translate a curve merely because one endpoint moved.
- **Chord symbols:** use the existing V1 chord parser/transposer and V3 chord-text
  semantics. Preserve anchors and original layout; do not invent a second chord
  grammar. Visual chord mapping/rendering is a later step.

## Fail-closed architecture and limitations

The intended future fallback chain is:

```
layout_preserved (V4) -> full_score (V3) -> chord_only -> explicit 422
```

This chain is **not implemented or registered in the API**. Future V4 output must
be withheld when mapping, protected masks, group reconstruction or pixel integrity
cannot be established. V3 thresholds, recognition, transposition and integrity
logic remain frozen and unchanged.

Current unsupported or intentionally unresolved cases include:

- Grace timing, hidden heads/stems, tablature/non-five-line staves, percussion and
  unsupported clefs; unknown SIG constructs are retained rather than interpreted.
- Split/continuation measures, repeated page-local measure numbers, reordered or
  omitted logical parts, arbitrary multi-part export IDs, and other cases without a
  unique measure/part join. music21 rewrites part IDs: the CLI normalizes them to
  stable `V4PartN` labels, which deliberately do not claim Audiveris lineage. Thus
  multi-part CLI matching remains unresolved until that lineage is verified. The
  one-page CLI avoids claiming a multi-page semantic alignment contract.
- Cross-staff chords with unclear staff ownership, duplicate unisons/voices,
  missing/suspicious slots, dangling references and incomplete chord membership.
- Tuplet identity/duration verification on the visual side, visual accidental
  semantics independent of MusicXML, and source rhythmic recognition accuracy.
- Empty signatures needing insertion, ambiguous mid-measure key regions,
  cross-system slur extensions and reliable ledger-to-head ownership.
- Text missed entirely by recognition, exact ink masks, arbitrary perspective
  distortion, curve collision checks, native upload-coordinate transforms, and
  all final reconstruction/rendering.

Unknown nodes are counted in `unsupported_constructs`; unresolved matching reasons
and dangling edges are reported separately. No real-sheet unsupported-construct
inventory can be claimed until a real diagnostic is run.

## Developer CLI and outputs

With V3's Audiveris and rasterization tools available:

```bash
python -m scripts.omr_v4.inspect_layout \
  tests/omr_v3_eval/scores/jayu.pdf --semitones -1 --out /tmp/v4-jayu
```

The output directory must be empty/new. The script uses V3 validation,
rasterization and the isolated Audiveris runner (60-second rasterization command
limits, 300-second Audiveris limit). It reuses V3 cleanup and semantic transposition,
then runs the unchanged V3 integrity guard separately for each exported part. It
skips the optional spatial cleanup if geometry is invalid. It never invokes MuseScore,
Paddle, the API, browser tests, a gate/acceptance run or a deployment.

Outputs:

- `plan.json`: complete immutable edit intent, event statuses/reasons and metrics.
- `graph-summary.json`: node/relation categories, geometry issues, unsupported
  constructs and all planning/matching metrics.
- `diagnostic-overlay.png`: original raster plus colored annotations, with a legend
  outside the page. Source heads are green, target markers blue, ambiguities orange,
  unused heads red, protected text magenta, beams teal, curves violet and keys brown.
  Unlocated semantic events appear in the side legend and fully in JSON.
- `diagnostic-annotations.png`: separate transparent annotation layer.
- `source.png`, `recognized.omr`, `recognized.musicxml`, `transposed.musicxml`, and
  `semantic-report.json`: local review/reproduction evidence. Semantic files are
  developer evidence, not a new downloadable product output.

Both principal JSON files report semantic/visual counts, MATCHED/AMBIGUOUS/UNMATCHED
counts, unmatched visual heads, match rate, protected intersections, beam uniform/
mixed/unresolved counts, linked/unlinked slurs/ties, mapped/unmapped key regions and
invalid geometry count. No accuracy threshold is imposed or implied.

## Validation and next gate

Small XML/.omr unit fixtures require no Audiveris and cover shuffled XML order,
modern/legacy references, polylines, music/text geometry, ambiguous/unmatched events,
structural target checks, V3 diatonic displacement, beam classes, protection conflicts,
deterministic serialization, unsafe XML/archive inputs and annotation-only output.
An offline integration test exercises the recognized-artifact CLI path with V3
cleanup/transposition/integrity. V3 music/gate tests are run because those functions
are imported. No V3 runtime changes are needed. Validation completed: **52 V4 tests passed**;
**96 V3 music/gate tests passed, 1 skipped** because MuseScore is not installed.
`git diff --check` passed. The constructed two-note fixture produced 2 matches,
0 ambiguous/unmatched notes, 6 conservative protected-region intersections,
1 uniform beam group, 1 linked tie and 1 mapped key region. Those are fixture
results, not a measured real-sheet match rate.

Docker was unavailable on this development machine, so **no real-sheet diagnostic
was run**. Unit fixture results are not real-sheet recognition evidence. Before
Phase 2, run one bounded development-sheet diagnostic, manually audit mapping
failures without tuning on that result, verify part/measure/voice contracts and
resolve protection/geometry gaps. Then define mask and outside-mask pixel-integrity
tests before implementing any erasure or local renderer.

## Licensing

Audiveris remains the **AGPL-3.0 dependency already present in V3**. This architecture
does not change or resolve its deployment, corresponding-source or other licensing
obligations. Public release remains HOLD under the existing V3 decision.

[Bravura](https://github.com/steinbergmedia/bravura) following
[SMuFL](https://www.smufl.org/) is the preferred candidate for future local symbol
rendering. A separate implementation step must bundle the applicable
[SIL Open Font License](https://github.com/steinbergmedia/bravura/blob/master/LICENSE.txt)
and required notices and review distribution obligations. No Bravura/font binary is
bundled by this phase.
