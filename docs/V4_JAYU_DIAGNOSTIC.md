# V4 jayu diagnostic: chord integrity and mapping

Scope: Phase 1 only, starting at `57ef624807565ec1267d6746ec61b3d730f382c3`.
No V3 runtime code, production guard, gate, transposition policy or matcher changes.

## Root cause: classification C

The Audiveris-derived harmony at **measure 32, offset 3/4 quarterLength** has a
conflict between its display label and its encoded chord degrees. Classification
**C: Audiveris chord representation issue**, exposed by the V4 diagnostic's
Audiveris-only chord path. It is not harmless serialization normalization (B).
The output agrees with the existing text transposition policy; it does not preserve
the contradictory source harmony's sounding pitch classes. The unchanged V3 guard
correctly reports that difference.

The retry retained raw `audiveris.mxl`; its measure-32 harmony has the same
suspended-fourth/add-seventh/alter-zero encoding, confirming that the conflict
precedes V4 cleanup.

The supplied failed-run files have SHA-256:

- `recognized.musicxml`: `c39c16308a69cdb1e5bc6a0bd222f0b5ede8cfd3a507e953e36d35b0271423fc`
- `transposed.musicxml`: `d27c94a8de4f288841792de20a5f2e619a53c7c7601c53ece83cf8fc2bb59b04`

The active key region is **F -> Eb**, shift **-2**. Calling
`transpose_chord_text('C7sus4', -2, original_key='F', target_key='Eb')` returns
`Bb7sus4`.

| Field | Source | Expected target after round trip | Actual target after round trip |
|---|---|---|---|
| figure | `Csus add 7` | `B-7 subtract 3 add 4` | same as expected |
| chord_text | `C7sus4` | `Bb7sus4` | same as expected |
| root / bass | `C2` / `C2` | `B-2` / `B-2` | same as expected |
| chordKind | `suspended-fourth` | `dominant-seventh` | same as expected |
| chordKindStr | `7sus4` | `7sus4` | same as expected |
| modifications (type, degree, alteration) | `(add, 7, 0)` | `(subtract, 3, 0)`, `(add, 4, 0)` | same as expected |
| parsed root | `C` | `Bb` | same as expected |
| parsed quality / extensions | empty / `7sus4` | empty / `7sus4` | same as expected |
| parsed bass / slash presence | `None` / false | `None` / false | same as expected |
| pitches | `C2 F2 G2 B3` | `Bb2 Eb3 F3 Ab3` | same as expected |
| pitch classes relative to root | **0, 5, 7, 11** | **0, 5, 7, 10** | same as expected |

`parse_chord` returns `Chord(root='C', quality='', extensions='7sus4', bass=None,
original='C7sus4')` for the source, and the same fields with root `Bb` and original
`Bb7sus4` for expected/actual targets. Thus the failing guard fields are the degree
modifications and chord kind, while parsed quality/extensions and slash presence
remain equal. Crucially, the seventh also changes relative pitch class: these
representations are not musically equivalent. Preserving the source's encoded
major seventh under a two-semitone descent would yield A-natural, not A-flat.

Source `<harmony>` (layout attributes omitted below):

```xml
<harmony>
  <root><root-step>C</root-step></root>
  <kind text="7sus4">suspended-fourth</kind>
  <degree>
    <degree-value>7</degree-value>
    <degree-alter>0</degree-alter>
    <degree-type>add</degree-type>
  </degree>
</harmony>
```

Expected and actual target `<harmony>`:

```xml
<harmony>
  <root><root-step>B</root-step><root-alter>-1</root-alter></root>
  <kind text="7sus4">dominant</kind>
  <degree>
    <degree-value>3</degree-value>
    <degree-alter>0</degree-alter>
    <degree-type>subtract</degree-type>
  </degree>
  <degree>
    <degree-value>4</degree-value>
    <degree-alter>0</degree-alter>
    <degree-type>add</degree-type>
  </degree>
</harmony>
```

An ordinary zero-shift write/read of the source passes the guard and preserves the
source discrepancy. A canonical source built with `chord_symbol_from_text('C7sus4')`
round-trips to relative pitch classes `0,5,7,10`. Rebuilding the original file's 39
chords through the existing `replace_chord_symbols(score, score_chords(score))`, then
transposing -2, passes the unchanged full guard. These are bounded in-memory/file
checks, not additional OMR runs.

The expected chord's pitches are checked **after write/read**: the V3 constructor
uses `updatePitches=False` while adding modifications, so its intermediate cached
`.pitches` must not be mistaken for the exported harmonic semantics.

## Production V3 comparison

`backend/api/main.py` supplies Paddle detection to V3. In `core.py`, when OCR items
are available and geometry aligns, `align_ocr_chords` and optional `merge_chords`
produce text placements. `replace_chord_symbols` removes the original ChordSymbols
and rebuilds every retained placement through `chord_symbol_from_text`, including
Audiveris fallback placements. V4's offline CLI does not execute this replacement.

The existing development evidence in
`docs/pr-assets/omr-v3/jayu/conversion-report_key-2.json` records
`paddleocr+audiveris`, 65 detected chords, 64 placed chords and **0 Audiveris additions**.
Its `recognized.musicxml` has **C7sus4 at measure 32, offset 0**, encoded as
`dominant-seventh`, subtract third/add fourth, pitches C/F/G/B-flat. In that observed
production-path run the offending Audiveris event was replaced, not retained at
3/4. This evidence and source inspection make another production OCR run unnecessary.

Production behavior is unchanged. If Paddle fails/is absent or geometry does not
align, V3 can retain the Audiveris encoding and still reject the discrepancy through
its existing fatal guard. This change neither fixes nor suppresses that production
rejection and does not reopen V3 acceptance.

## V4-only diagnostic policy

Option 2 is implemented in `backend/omr_v4/integrity.py`:

1. Invoke the unchanged full V3 guard separately for every part.
2. On independent copies, remove **only harmony ChordSymbols** and invoke the same
   guard again with all pitched notes, rests, rhythms, measures and keys retained.
3. Only explicit known chord-only issue messages may produce a warning. Unknown
   wording, unreadable semantics, changed part/measure/event counts, pitches,
   rhythms and keys remain fatal. The independent pass also catches later note
   failures hidden by the full guard's 20-issue report cap.
4. Preserve the failing full report. Write `semantic_integrity` into both JSON
   reports, add chord issues to plan blockers, and put a visible chord-integrity
   warning in the overlay's side legend. Fatal cases write a semantic report and
   stop before final ownership/planning or diagnostic rendering. Phase 1.7 additionally
   captures provisional raw matching evidence before the ledger repair; it cannot
   pass that evidence to a plan after a fatal integrity failure.

For this chord the independent result is 33/33 measures, 274/274 note/rest events,
zero chord symbols and no issues. The full report retains 39/39 harmonies and its
original failure. `note_rhythm_key: pass` proves preservation through transposition,
not recognition accuracy.

The matcher reads MusicXML pitched `<note>` events and their `<chord/>` grouping;
it does **not** read `<harmony>` chord labels/degrees. SIG `head-chord` membership is
note grouping, not a text ChordSymbol. A regression verifies that removing the
harmony leaves the extracted note semantics unchanged. No chord warning authorizes
pixel editing, final rendering, or release.

## Validation

Combined targeted run: **163 passed, 1 skipped** (67 V4 tests; 96 V3 music/gate tests;
one existing MuseScore-dependent test skipped). Tests cover the exact conflicting
harmony, warning continuation, fatal pitch/rhythm/key/count failures, unknown and
unreadable errors, capped-report concealment, no matcher call after fatal failure,
visible warning annotation and deterministic plan/summary/semantic JSON.

The guard's frozen SHA-256 remains
`9f27db149414fe38991b86230f4c15fae90c2ecd1bb5205ecfd56892fa992b43`; a regression locks
that baseline. No full acceptance corpus, fresh holdout, browser tests or workflow
runs were requested or launched.

## Single real-sheet retry

One Docker invocation of `jayu.pdf --semitones -2`, using the existing
`capomatic-v4-local:latest` image, with network disabled, 2 CPUs, 4 GiB RAM,
read-only repository mount and a separate writable output directory. Existing V3
raster/Audiveris command timeouts remain 60/300 seconds. Original failed-run files
are preserved in `v4-jayu-diagnostic/`; retry artifacts go to
`v4-jayu-diagnostic-retry/`. No matcher tuning is permitted based on this result.

The retry completed successfully, retaining `overall: warning`,
`note_rhythm_key: pass`, `chord: fail`, the original chord issue, and no fatal issues.
All four requested artifacts were generated, along with the source raster, raw
Audiveris export and .omr evidence. The overlay was visually checked and visibly
shows **CHORD INTEGRITY WARNING** outside the source page.

| Metric | Observed |
|---|---:|
| Semantic pitched notes | 249 |
| Visual heads | 249 |
| Matched | 244 |
| Ambiguous | 0 |
| Unmatched semantic / visual | 5 / 5 |
| Match rate | 97.99196787148594% |
| Protected-region intersection pairs | 30 |
| Beam groups total / uniform / mixed / unresolved | 66 / 64 / 0 / 2 |
| Slurs/ties linked / unlinked | 62 / 5 |
| Key regions mapped / unmapped | 8 / 0 |
| Nonfinite/invalid geometry | 0 |

Unsupported node categories retained for review: `articulation` (38), `barline`
(45), `dynamics` (1), `fermata` (2), `pedal` (1), `staff-barline` (41).

The five unmatched semantic events are C4 at measure/offset 1/1⁄2, 1/3⁄4, 9/0,
16/3⁄2 and 25/0. Each reports no head satisfying measure/staff/slot/source staff
pitch. No ambiguous match was promoted and no matcher changes were made. These
failures, conservative text intersections, unresolved beam groups and curve links
remain review blockers. The match rate measures correspondence, not recognition
accuracy or pixel-edit safety.

**NEEDS_MAPPING_FIXES**. Phase 2 is not authorized by this diagnostic. No merge,
deployment, runtime V4 route or production flag activation occurred.
