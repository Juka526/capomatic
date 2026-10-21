# GT-17E — scoped owner confirmation of full-score event cores

All **169 recognized note/rest event cores** now have owner verification. This evidence-status update changes no musical content or rendered pixels. Source recognition completeness remains **UNVERIFIED**, rendering remains **INCOMPLETE**, and independent ground truth remains **0**. Owner review of recognized events cannot establish that the OMR omitted no printed event.

Base: `55b72a2fb2162ee4ba913b99310932fbb26fcfab`. Branch: `experiment/v4-gt17e-owner-event-confirmation`. Worktree: `/private/tmp/capomatic-v4-gt17e`. The containing commit is the implementation revision; its exact SHA is supplied at delivery.

Understood as: promote only the reviewed note/rest core fields, plus separately and expressly approved SYS6 lyric-onset associations, without changing source content, attachments or visual layouts.

## Owner approval and exact scope

The current GT-17E user instruction explicitly approves SYS6_EVENT (30), SYS7_EVENT (17), SYS8_EVENT (22) and SYS9_EVENT (14): 83 previously provisional cores in printed measures 20–37. `owner-approval-record.json` preserves the exact approval excerpt, all reviewed candidate records, exact source event IDs and source crop hashes. It binds the GT-17D review summary, remaining plan, freeze and prior 4867 interpretation. It does not invent a separate signature, timestamp or independent reviewer.

Only **note/rest kind, written pitch, onset, duration, voice and part identity** are promoted. Attachment IDs, stems, beams, flags, raw SIG interpretations, new ties/slurs, lyric associations, continuation lineage and overall source completeness are not implicitly approved. Original candidate and OMR records remain immutable. The new interpretation layer contains field-specific overrides and references prior owner evidence; it does not replace that historical evidence.

The two event cores whose erroneous 4867 attachment was corrected in GT-17D are included among the 83. Their core approval does not restore that slur. The raw 4867 object and prior approved ‘되’ interpretation remain untouched.

### Separate SYS6 lyric approval

The original instruction mentioned SYS6 association context without identifying an express approval. The assistant therefore requested clarification; the owner answered exactly:

> SYS6_LYRIC_ONSET 40개 전체 승인

The complete question and answer are recorded separately in `owner-approval-record.json`, with the exact 40 reviewed case IDs, original text/row/onset candidates and source crop bindings. Each association maps uniquely to the existing pitched event and the corresponding serialized lyric. Only these 40 exact associations are promoted. Previously approved wording and row assignments are not submitted for duplicate confirmation.

## Coverage after integration

| Field | Owner approved | Still provisional / unresolved |
|---|---:|---:|
| Recognized note/rest cores |169 |0 |
| Chord symbols |24 |No new chord decisions |
| Korean syllable wording / row assignments |167 |No new wording decisions |
| Exact syllable-to-event/onset associations |128 |39 |
| Lyric continuation marks |30 |20 |
| Other raw SIG cases |No new classification |27 |
| m28 held-syllable ancestry |Not approved |UNRESOLVED |
| Full repeat playback |Not approved |UNRESOLVED |

The 128 lyric associations comprise 88 prior approvals and 40 SYS6 approvals. The 20 pending continuation questions comprise 19 visually supported candidates and the unresolved m28 mark. The pending workload is 39 associations + 20 continuation questions (including m28) + 27 SIG cases + 1 playback decision = 87 field questions. Counts overlap source regions and are not independent errors or a verified accuracy denominator. MusicXML lyric-extender serialization remains the prior unresolved gap.

`field-coverage-matrix.json` lists all 169 event IDs with their prior/new approval origin and field values, and each of the 79 newer lyric-association statuses. Prior 88 association approvals remain inherited. It does not claim full source coverage.

## Validation and preservation

The importer rejects missing/duplicate groups, case IDs, source event IDs, nonunique mappings, incorrect group counts, wrong measures/systems, changed core values or bounding boxes. The approved set must equal exactly the 83 previously provisional IDs. Raw object records and bounding boxes must equal their frozen inventory counterparts; each candidate crop hash is checked. Note/rest semantic addresses must be unique, including rests. Approved lyric fields must match the exact original candidate and a unique pitched event containing the same text/row.

Unchanged V3 full integrity guards pass corrected source→A (−1) and source→G (−3), using the frozen GT-17D MusicXML files. The source-backed m21→22, m31, m33 and m35 curve relationships remain valid. The 4867 false slur remains absent. These checks establish representation/transposition consistency, not independent recognition correctness.

No MusicXML, PNG or PDF is generated, copied or changed in GT-17E. Previous owner-integration and GT-17D source/target XML, PNGs, metadata and recorded historical directories are hashed before and after. Original source PNG/OMR/visual graph hashes are verified against the existing source bindings. GT-16B/16C/17 frozen manifests are rechecked. GT-16C optical layout is not altered. No new visual or independent optical review is claimed; prior visual limitations remain.

Targeted validation: **652 passed, 1 skipped**. The only skip is the existing MuseScore-not-installed case (`test_omr_v3_gate.py:190`). There are 28 new synthetic boundary tests covering identity, scope, duplicate/missing candidates, field mismatches, rest lookup and separation of event/lyric approval. `git diff --check` passes. Full Acceptance is not run.

## Outputs and next review

Untracked output directory: `/private/tmp/capomatic-v4-gt17e/gt17e-delivery-output/`:

- `owner-approval-record.json`: verbatim approval context and exact event/lyric bindings.
- `owner-interpretation-layer.json`: field-specific overrides and prior-layer hashes.
- `field-coverage-matrix.json`: approved versus pending coverage.
- `semantic-validation.json`, `preservation-verification.json`, `output-freeze.json`.
- `remaining-review-plan.json`, `remaining-owner-review-summary.md`: **87 pending field questions in 16 groups**, retaining blank owner answers and prior source-native review references.

Review the remaining lyric-onset, continuation, SIG, m28 and playback groups only. The summary links the prior detailed source-only material but explicitly excludes the now-approved EVENT and SYS6_LYRIC_ONSET groups from new review. Already confirmed chords, wording and events require no repeated approval.

```bash
cd /private/tmp/capomatic-v4-gt17e
/private/tmp/capomatic-v4-venv/bin/python -m scripts.research.gt17e_owner_confirmation --output /private/tmp/FRESH-GT17E-OUTPUT
/private/tmp/capomatic-v4-venv/bin/python -m pytest tests/test_v4_ground_truth_*.py tests/test_v4_paired_ground_truth_01.py tests/test_omr_v3_music.py tests/test_omr_v3_gate.py tests/test_omr_v4_integrity.py -q -ra
git diff --check
```

The output destination must be fresh. This is local evidence-linked tooling requiring the existing GT-17D delivery directory and its referenced original and historical evidence; it is not a portable evidence archive. [Validation metadata](V4_GT17E_VALIDATION.json) binds the delivered output hashes and measured checks.

No original source changes, original-ink removal, protection-mask changes, raw OMR rewriting, production/API/frontend changes, merge or deployment. All experimental previews retain **DEVELOPER-ONLY / INCOMPLETE / NOT FOR PERFORMANCE OR PRINTING** status. Stop after the scoped owner-approval integration.
