# Diagnostic written-harmony boundary

**Status: BLOCKED_FOR_RUNTIME_UNVALIDATED_REALIZATION. Bar 32 is not fixed.** This new offline experiment neither changes nor replaces the V3 full guard. All prior reports, frozen protocols and score artifacts remain unchanged. Its output is coordinator-only and must not be distributed as reference answers to annotators.

## What the diagnostic implements

[The helper](../scripts/omr_v4/harmony_boundary_diagnostic.py) converts a limited MusicXML harmony to an immutable written record: exact root step/alteration, explicit bass step/alteration or absence, and ordered written degree identities with dominant-relative alterations. It keeps C# distinct from Db, degree 2 distinct from 9, natural seventh distinct from minor seventh, and an absent bass distinct from an explicitly supplied root bass. The original XML is retained as a witness; canonicalization is not a replacement chord-text parser or spelling engine.

The accepted base kinds are major, minor, dominant, major-seventh, minor-seventh, suspended-fourth and suspended-second. Fully explicit `other` is supported only with unique `add` elements including unaltered degree 1. Degrees are integral 1–13; root/bass and degree alterations are limited to ±2 semitones. Unsupported semantic children/kinds, microtones, duplicate roots, repeated modifications to one degree, impossible operations, missing roots and contradictory/ambiguous inversions are rejected. A finite display-suffix allowlist rejects unknown or contradictory text rather than silently discarding it. The scope is intentionally smaller than MusicXML; rejection is not a claim that an encoding is invalid in the full standard.

The diagnostic emits a `kind=other` XML witness with one explicit `add` per normalized degree, then parses it back into the same written record. This **self round-trip is a mechanical consistency check**, not independent semantic validation or an engraving output. Presentation attributes remain in the original witness; canonical XML does not establish printed-name, spacing or typographic equivalence. It never enters the production pipeline.

For the degree reference, added alterations use the dominant basis, including a minor seventh at zero alteration. Base kinds and `other` are interpreted according to the authoritative [MusicXML degree rule](https://www.w3.org/2021/06/musicxml40/musicxml-reference/elements/degree-alter/) and [kind definitions](https://www.w3.org/2021/06/musicxml40/musicxml-reference/data-types/kind-value/). External specifications support this bounded interpretation; our authored normalizer is not an independent human reference set.

## Actual three-event findings

The helper reads the same 28 hash-bound jayu artifacts, checks the existing frozen chord protocol, and evaluates source and target at bars 4 @ 2, 20 @ 0 and 32 @ 3/4. Expected target root/bass spelling comes from the existing V1/V3 chord transposition functions and the saved F→Eb key region. No new transposition algorithm is introduced.

| Check | Observed result |
|---|---|
| Written source→target degree shape, chromatic root/bass shift and expected V1 spelling | Agree with the existing implementation for all three events; not independent correctness proof |
| Written canonical XML self round-trip | 6/6 source/target records preserved |
| Canonical music21 pitch-class realization versus specification record | 0/6 agree in this experiment |
| Original versus canonical realized spelled pitches and octaves | 0/6 equal |
| Existing full V3 guard before and after diagnostic | Identical FAIL: bar 32 chord semantics changed at 3/4 |

The pitch-class predicate compares sets: it ignores octave, order and duplicate tones. The full realized predicate compares sorted multisets of spelled pitches and MIDI values: order is ignored, while duplicates, spelling and octaves remain significant. Counts describe these six observed harmony objects, not general accuracy. MusicXML harmony symbols do not specify a unique piano voicing; the spelled-pitch/octave comparison is an observation of music21's object realization, not a claim that the XML fixes an intended octave voicing or a measurement of audio/rendering.

The explicit-degree form moves even ordinary dominant sevenths into `add 7 / alter 0`, exposing the already identified **music21 9.9.1** major-versus-minor added-seventh mismatch. Its realization also contains duplicated tones/different octaves in these explicit `other` constructions. The existing bar-32 source already shows the seventh mismatch; its ordinary dominant-based target realizes the expected pitch classes before this diagnostic normalization. The original and canonical pitch lists, specification pitch classes and separate booleans are all retained. Written XML equivalence must not be promoted to actual library realization equivalence.

We deliberately do not change a written alteration to compensate for a library bug: doing so could corrupt the MusicXML meaning. This normal form can support **diagnostic comparison and independent review**, but is not a safe runtime interchange candidate. No canonical score is fed to the guard and no apparent guard pass is manufactured. The minimal dependency reproduction in the earlier report isolates `music21.harmony.ChordSymbol._adjustPitchesForChordStepModifications`: its added-degree path uses the major scale, while the nonzero-alteration branch supplies the seventh correction. Zero alteration misses that correction. The recorded function SHA-256 is `028cc340cf5e9a287bfd698be816f39539b474ea229fc6852461005bc5459214`. The earlier [shared root-cause report](V4_SHARED_CHORD_INTEGRITY.md) remains the bounded source/serialization diagnosis.

## Negative controls and limits

Twelve declared synthetic controls are recorded in `boundary-report.json`: six genuine changes (major/minor, minor/major seventh, added-seventh alteration, changed/lost slash bass and wrong root), one distinct written degree identity with the same pitch classes, one equivalent sus construction and four unsupported/ambiguous encodings. All meet their declared expectations. Tests additionally check enharmonic spelling, root/bass/alteration preservation, inversion contradictions, repeated pitch-class inversion ambiguity, unsupported XML and deterministic normal-form bytes. These are conformance controls, not annotations, a holdout or an acceptance metric.

Unsupported or ambiguous source events abort the diagnostic; original files are retained and no partially converted score is emitted. The report binds schema `capomatic.harmony-boundary/1`, helper SHA, MusicXML 4.0 interpretation, dependency version and input hashes.

No independent human harmony reviews have been collected. The frozen reference protocol still requires reviewers to interpret source snippets without these answers, library pitches or guard outcomes. Independent review must separately establish written root/bass/degree identity and its MusicXML interpretation, then compare downstream realized pitch classes; voicing, printing and playback require their own evidence and must not substitute for written identity. Broader kinds, microtones, degree interactions, voicing, actual printing and interoperability remain unresolved. No claims are made from normalized pitch-class equality alone.

## Reproduce and next step

```sh
python -m scripts.omr_v4.harmony_boundary_diagnostic \
  --inputs /private/tmp/capomatic-v4-dual-inputs.json \
  --out harmony-boundary-complete
```

Use a new/empty output directory outside original evidence. `boundary-report.json` includes original and canonical XML witnesses, normalized data, separate written/realized comparisons, controls, helper/input/protocol hashes and the unchanged full-guard reports. Local outputs are untracked, coordinator-only diagnostics, not source-only annotation packets.

The next recommendation is independent MusicXML reference review plus a narrowly scoped dependency reproduction. Any later boundary candidate must prove both written semantics and downstream behavior with genuine-change controls before a separate production proposal. Leave the existing V3 guard, transposer, parser and all acceptance rules unchanged. No compensating alteration patch, normalizer integration, renderer/B2, API/frontend, merge or deployment is authorized here.

Validation: targeted V4 plus frozen V3 music/gate regressions: **325 passed, 1 skipped** (existing external MuseScore dependency unavailable). `git diff --check` is required before commit. Actual outputs: untracked `harmony-boundary-complete/boundary-report.json`; no human labels or runtime acceptance result are created.
