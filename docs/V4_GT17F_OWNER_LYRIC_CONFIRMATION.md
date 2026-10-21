# GT-17F — final 39 owner-approved lyric-onset associations

All **167 recognized Korean syllable-to-event/onset associations** now have owner confirmation. This is a field-specific evidence update: musical content, original OMR, MusicXML and rendered images remain unchanged. Source completeness remains **UNVERIFIED**, independent ground truth remains **0**, and all previews remain **DEVELOPER-ONLY / INCOMPLETE / NOT FOR PERFORMANCE OR PRINTING**.

Base: `ad0a249e3621d4755b70ee82dbd20e79f48a1c7a`. Branch: `experiment/v4-gt17f-owner-lyric-confirmation`. Worktree: `/private/tmp/capomatic-v4-gt17f`. The containing commit is the implementation revision; its SHA is supplied at delivery.

Understood as: approve exactly the three remaining LYRIC_ONSET groups, preserving all earlier approvals and every unrelated uncertainty. This does not approve unrecognized/missing printed content or prove full source transcription accuracy.

## Approval provenance and exact scope

The current user instruction explicitly supplies these exact owner decisions:

> SYS7_LYRIC_ONSET: CONFIRM
>
> SYS8_LYRIC_ONSET: CONFIRM
>
> SYS9_LYRIC_ONSET: CONFIRM

`owner-approval-record.json` preserves those strings and the verbatim user-supplied approval context, including the field restriction and group counts. The origin is the current instruction quoting actual owner decisions; no separate submission, signature, timestamp or reviewer is invented.

| GT-17E review group | Exact associations | Printed measures |
|---|---:|---|
| SYS7_LYRIC_ONSET |16 |25–29 |
| SYS8_LYRIC_ONSET |16 |30–33 |
| SYS9_LYRIC_ONSET |7 |34–37 |

The record embeds every original review case and source lyric record. It binds the GT-17E remaining-owner summary, remaining plan, interpretation layer, coverage matrix, approval record and output freeze by path/SHA-256. Each case retains its exact ID, original wording, lyric row, candidate onset, source event ID, raw object ID, source window and frozen source-crop hash. Original source PNG, OMR and visual graph hashes are also bound.

Only the **syllable-to-event and exact onset association** is promoted to `OWNER_VERIFIED_SOURCE`. Previously approved wording and rows are retained, not rewritten or submitted for repeated approval. No continuation mark, held-syllable ancestry, raw SIG classification, repeat traversal or XML extender meaning is approved by association approval.

## Validation and field-level preservation

The existing GT-17E lyric resolver now accepts explicit group/count/measure scope; its original SYS6 defaults and validation contract remain unchanged. GT-17E regressions still pass. The new caller requires all three approved groups and exactly the 39 pending case IDs, validates unique group/case/source-event identities, and rejects missing, duplicate, mismatched, already-approved or ambiguous candidates before writing any new interpretation artifact.

Every selected candidate must match the frozen inventory's wording, row, printed measure and onset. Its source event must be a unique pitched event with matching raw source identity; its crop hash must match. The corrected source MusicXML and both frozen A/G targets must contain exactly that text/row association on the unique event at the approved onset. These are consistency checks against the frozen interpretation, not independent optical validation.

The new layer copies the existing GT-17E overrides and adds only 39 lyric-association records. The previous 40 SYS6 records remain identical; the earlier 88 approvals remain inherited through the unchanged coverage and provenance chain. Thus **88 + 40 + 39 = 167**. The 169 event-core coverage records and all prior event overrides remain identical. No MusicXML, PNG or PDF is generated, copied or rewritten.

| Field | Owner approved | Still provisional / unresolved |
|---|---:|---:|
| Recognized note/rest cores |169 |0 |
| Chords |24 |No new decision |
| Korean wording / row assignments |167 |No new wording decision |
| Exact lyric-onset associations |167 |0 |
| Lyric continuation marks |30 |20 |
| Raw SIG cases |No new classification |27 |
| m28 held-syllable ancestry |Not approved |UNRESOLVED |
| Full repeat playback |Not approved |UNRESOLVED |

The pending 20 continuation questions include m28; it is not an additional twenty-first continuation. Remaining review is **20 continuations + 27 SIG cases + 1 playback decision = 48 field questions in 13 groups**. Overlapping source objects/questions are retained as such, not counted as independent musical errors. The remaining summary excludes all approved EVENT and LYRIC_ONSET groups and leaves every owner answer blank.

The owner-approved 4867 ‘되’ interpretation and false-slur removal remain intact. The approved m21→22 tie, m31 unequal-pitch slur, m33 tie and m35 tie pass source/A/G endpoint relationship checks. Unchanged V3 full semantic guards pass corrected-source→A (−1) and corrected-source→G (−3). Existing MusicXML lyric-extender serialization is unchanged and remains unresolved; no new `<extend>` records are introduced.

## Frozen evidence and tests

All GT-17E delivered artifact hashes and its exact freeze identity are checked before integration. Its previously recorded historical directory snapshots are verified before/after, together with GT-17E itself. This preserves original-side evidence, historical MusicXML/PNG/PDF files, GT-16C optical layouts, earlier approval records and frozen predictions. Original source PNG/OMR/graph hashes are also checked before/after. No source or protection-mask mutation is performed.

Targeted validation: **673 passed, 1 skipped**, including 21 new synthetic controls for exact approval scope and preservation of prior fields. The only skip is the existing MuseScore-not-installed case (`test_omr_v3_gate.py:190`). No new skip or integrity waiver is introduced. `git diff --check` passes. The broader Full Acceptance suite is not run; executed checks are the targeted command below.

This task performs no fresh optical or independent musician validation. Visual quality retains historical limitations. Matching OMR, XML and approved candidate records is not an independent source-completeness denominator.

## Actual outputs and remaining review

Untracked directory: `/private/tmp/capomatic-v4-gt17f/gt17f-final-output/`:

- `owner-approval-record.json` — verbatim decisions and exact 39-case bindings.
- `owner-interpretation-layer.json` — prior approvals plus only the new onset overrides.
- `field-coverage-matrix.json` — unchanged event coverage and final association coverage.
- `approval-validation.json`, `preservation-verification.json`, `output-freeze.json`.
- `remaining-review-plan.json`, `remaining-owner-review-summary.md` — 48 pending questions with source-review references and blank answers.

This report is `docs/V4_GT17F_OWNER_LYRIC_CONFIRMATION.md`; the [validation metadata](V4_GT17F_VALIDATION.json) beside it records the actual file hashes and measured results. No new rendered score paths are claimed because no score export is needed for this status-only update.

```bash
cd /private/tmp/capomatic-v4-gt17f
/private/tmp/capomatic-v4-venv/bin/python -m scripts.research.gt17f_owner_lyric_confirmation --output /private/tmp/FRESH-GT17F-OUTPUT
/private/tmp/capomatic-v4-venv/bin/python -m pytest tests/test_v4_ground_truth_*.py tests/test_v4_paired_ground_truth_01.py tests/test_omr_v3_music.py tests/test_omr_v3_gate.py tests/test_omr_v4_integrity.py -q -ra
git diff --check
```

A fresh destination and the existing GT-17E delivery directory with its referenced original and historical evidence are required. This is local evidence-linked research tooling, not a portable archive. Only research code/tests/documentation/validation metadata are committed; detailed generated evidence remains untracked and retained locally in the stated output directory. No external backup or portable evidence archive was created. Any handoff must retain that directory with its freeze and referenced historical inputs.

Next review concerns continuation lineage, remaining SIG and playback fields only. No original PDF/raster change, original-ink removal, protection-mask change, raw OMR rewrite, production/API/frontend change, merge or deployment occurred. Stop after this scoped approval integration.
