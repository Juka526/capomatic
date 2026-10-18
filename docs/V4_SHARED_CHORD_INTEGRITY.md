# Shared chord-integrity diagnosis and reference protocol

**Status: representation causes identified for three events; full V3 guard remains FAIL.** No production fix, guard waiver or acceptance change is implemented. This study does not validate recognition, source ink or rendering. It uses a new worktree based on comparison commit `974acba9ca4cd7eeb797a6522afbbedba13b07ac`; every verified worktree remains unchanged.

## Bounded findings

| Event, quarterLength offset | Source text → expected V1 target | In-memory guard cause | After XML export/read |
|---|---|---|---|
| bar 4 @ 2 | A7/C# → G7/B | `dominant-seventh` versus constructed `dominant` alias | Both read as `dominant-seventh`; this failure disappears |
| bar 20 @ 0 | C7 → Bb7 | Same kind alias | Same normalization; this failure disappears |
| bar 32 @ 3/4 | C7sus4 → Bb7sus4 | Different kind and degree construction | Difference persists; full guard still rejects |

The unchanged guard compares corrected-source XML against persisted-target XML: **33→33 measures, 274→274 events, 39→39 chords**, with the existing bar-32 issue only. The fresh in-memory transposition comparison fails bars 4, 20 and 32. A fresh serialization/read of that same transposition again fails only bar 32. These are different stages, not evidence of three new production defects. Production `core.py` compares parsed recognized/transposed exports, not the intermediate object.

Raw `audiveris.mxl`, pre-ledger XML and corrected recognized XML preserve the same three harmony profiles. The existing ledger repair changes notes, not these harmonies. All three events belong to the existing F→Eb region at −2 semitones. No new pitch-spelling or transposition implementation is used.

## Bar 32: representation equivalence and a separate library realization defect

The source XML has root C, kind `suspended-fourth` with display text `7sus4`, plus degree **add 7 / alter 0**. The target has root Bb, kind `dominant`, with **subtract 3 / add 4**, each alteration zero. These are different constructions of the same written degree profile after the requested root shift.

The external reference matters: for MusicXML `degree-type=add`, alteration is relative to a dominant basis, whose seventh is **minor**. It is not automatically a major-scale seventh. Kind `dominant` supplies a minor seventh; `suspended-fourth` supplies the fourth and fifth. See the authoritative [degree-alter rule](https://www.w3.org/2021/06/musicxml40/musicxml-reference/elements/degree-alter/) and [kind definitions](https://www.w3.org/2021/06/musicxml40/musicxml-reference/data-types/kind-value/).

A deliberately small, separate specification-based XML evaluator records source degrees `{1:0, 4:5, 5:7, 7:10}` and the identical target relative profile. Source chord pitch classes are C/F/G/Bb; the target is Bb/Eb/F/Ab. Root movement, written degree identity and explicit bass presence/movement agree. The bar-4 and bar-20 profiles also agree. The evaluator is authored within this study: its semantic basis is external to music21, but it is not an independent human reference annotation. This is stronger than comparing display text or unordered pitch-class sets, but it remains a whitelist-based three-event diagnostic, not a general harmony equivalence engine.

Installed **music21 9.9.1** instead realizes the source add-7/alter-0 chord as C/F/G/**B-natural**. Its `ChordSymbol._adjustPitchesForChordStepModifications`, nested `typeAdd`, starts from a major scale and enters its seventh adjustment only within the nonzero-alteration branch. At zero it leaves a major seventh, contrary to the cited XML rule. The exact inspected function SHA-256 is `028cc340cf5e9a287bfd698be816f39539b474ea229fc6852461005bc5459214`. The original source harmony is therefore **not shown malformed by that music21 pitch list**. Earlier interpretations that treated B-natural as proof of invalid source XML are superseded by this specification check; historical files are left intact.

There is another in-memory distinction: V3 `chord_symbol_from_text()` deliberately uses `updatePitches=False` when adding degree modifications. The newly constructed target's temporary pitch list retains the third until export/read realizes the modifications. For this case its temporary list is Bb/D/F/Ab, whereas the parsed target is Bb/Eb/F/Ab. This is not a trustworthy independent pitch oracle and does not establish a changed encoded chord. The helper captures it before export rather than silently replacing the observation with the round-trip result.

Classification:

- **Bars 4/20: serialization normalization of equivalent kind aliases**, HIGH confidence for these observed objects/exports. No mismatch in the checked root, degree and bass fields after the expected shift.
- **Bar 32: noncanonical but equivalent MusicXML harmony constructions**, HIGH confidence within the cited kind/degree/root/bass semantics. The strict structural guard detects a real representation difference; this study does not reinterpret that failure as a pass.
- **Additional identified cause: music21 9.9.1 add-seventh realization mismatch**, HIGH confidence from the independent specification, minimal synthetic reproduction and installed implementation. Its temporary `.pitches` values must not be used to dismiss XML equivalence or prove a source error.

These conclusions concern encoded harmony identity. They do not certify printed recognition, voicing/octave realization, engraving/readability or every chord on the page.

## Frozen reference experiment and independent evidence still required

The [reference protocol](V4_CHORD_REFERENCE_PROTOCOL.json), frozen with [its hash](V4_CHORD_REFERENCE_PROTOCOL.sha256), fixes the three previously reported cases, six representation stages, input hashes, independent MusicXML reference, genuine-semantic-change controls and fail-closed unsupported cases. It is a **replay protocol for already-observed forensic cases**, not a preregistered blind accuracy evaluation.

A later independent review must give two MusicXML-literate reviewers only source/target root/kind/degree/bass snippets and specification references, hiding music21 pitches, guard outcomes and this diagnosis. Each independently writes degree/bass interpretations, spelling and ambiguities; freeze both reviews before adjudication or unblinding. No such human reviews are claimed here. Future candidate import/export normalization must use a separately frozen encoding set with real degree changes, slash-bass changes, wrong intervals, equivalent aliases, and unsupported/microtonal cases. Unknown cases remain blocked; there is no new pass-rate threshold.

Next implementation recommendation: first review a narrow canonical harmony import/export boundary and a minimal dependency reproduction upstream. Preserve source degree semantics, root/bass/spelling and provenance; compare a canonical representation on both sides of the **unchanged full guard**. Do not simply delete kind/modification checks, substitute pitch-class-only acceptance, special-case these measures, or patch installed music21 in this task. A boundary proposal needs separate authorization, independent reference review and full negative regressions before production consideration. No candidate normalizer is implemented.

## Reproduction, artifacts and checks

The new offline helper is [chord_integrity_forensics.py](../scripts/omr_v4/chord_integrity_forensics.py). It reads the original 28 hash-bound artifacts and separately binds raw Audiveris MXL SHA-256 `087a7c77b993e76ca03c777191308c8821ea4e5bd7b426a0014119c3fb5f25fd`. It uses unchanged V3 functions, bounded entity-free XML inspection, existing V1 expected text, an in-memory MusicXML export/read, and the separate specification-based evaluator. No Audiveris, raster editing or rendering runs.

```sh
python -m scripts.omr_v4.chord_integrity_forensics \
  --inputs /private/tmp/capomatic-v4-dual-inputs.json \
  --out validation-integrity-output
```

Outputs remain untracked: `input-bindings.json`, `harmony-stages.json` and `manifest.json`. They retain full harmony snippets, figure/text/parsed quality/extensions, root/bass, kind/text, modifications, realized pitches, specification profiles, expected V1 text and all unchanged guard reports. Output must be new/empty and outside the evidence tree. All inputs are hash-checked after replay. No complete score image or new finished transposed score is emitted.

New tests independently exercise the minor seventh rule, equivalent sus/degree encodings, wrong degree and slash-bass changes, rational harmony offsets, unsupported kinds/microtones, entity rejection and dominant alias export/read. Relevant V4 plus V3 music/gate regressions are run; no Full Acceptance. Human reference review and broader canonicalization validation remain pending. This task changes no acceptance rules, source raster, verified branch, V1/V3 production code, API/frontend, renderer, merge or deployment state.

Validation: **295 passed, 1 skipped** across `tests/test_omr_v4_*.py`, `tests/test_omr_v3_music.py` and `tests/test_omr_v3_gate.py`; the existing skip is MuseScore unavailable. `git diff --check` passed. The final trace is under `validation-integrity-final/` (untracked); all three unchanged full-guard comparisons still fail as recorded above.
