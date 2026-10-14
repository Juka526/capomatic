# Reviewer handoff guide (melody study, M1)

Status: guidance only. No completed study labels or signed review records have been supplied to this worktree; nothing is Lock A ready, and `python research/melody/readiness.py` reports **NOT READY**. The acceptance scorer is a draft and not implemented. No model has been run. This guide adds no new gate; the contracts are `docs/plans/V2_3_MELODY.md`, `labels.schema.json`, `lock_a.template.json` and `readiness.py`.

## Roles (opaque IDs, no personal names)
Each person gets one anonymous ID (e.g. `L1`, `C2`). The labeler, corrector, rater, developer and fresh held-out-reader study roles are disjoint. Scorer review is a separate task: its independent second reviewer must not be a developer, as the existing lock requires; this guide does not add a separate-person requirement beyond that contract.

| Role | Count | Does |
| --- | --- | --- |
| Labeler | 2 | Reads the original score by hand, independently, and writes labels |
| Corrector | 2 | Later fixes engine output in the timed study; never made labels |
| Rater | 3 | Grades final outputs 1-5; never made labels or corrections |
| Fresh held-out reader | 1 | Labels the 2 held-out snippets; has seen no development output and did not design the pipeline |
| Scorer reviewer | 1 | Independently checks the tester's scorer; must not be a developer |
| Developers | existing team | Build tooling; hold no human role |

Two people cannot fulfil the whole study. If role separation allows, the same two independent readers may check chord truth separately from the melody labels.

## Before any data is formal
- Rights evidence for every source sheet comes first. Purchased sheets are not training data or a formal held-out set by default. Unknown-rights, user-uploaded and previously refused material is excluded.
- Held-out templates and docs contain no model answers.

## Labeling (no coding needed)
1. Each labeler reads the **original image**, never OCR, engine or product output, and writes by hand: staff lines and x extent, every note/rest, text (title, credits, lyrics) and which note each syllable and chord sits on, all in original-image pixels.
2. Durations and onsets are fractions of a whole note (`1/4`, `3/8`); pickup measure is 0. Write the pitch as printed (letter, accidental, octave).
3. Hand-calculate expected transpositions for the fixed shifts (-11, -7, -2, 0, +1, +5, +11) and the capo negative controls (melody unchanged). Do not use any product function.
4. Keep both readers' sheets. Record disagreements, then reconcile by looking at the source, not at a parser. Freeze after reconciling.
5. Handwritten tables may be encoded mechanically into separate label JSON files matching `labels.schema.json`, then rechecked against the source by a human. Keep the schema unchanged; never derive missing answers from model output.

## Study shape
6 development + 2 held-out snippets (at least 500 note events in total) and 32 predefined rejection cases (16 structures x 2). **Lock A** is frozen before any experiment. **Lock B** is frozen before the single held-out trial. Comparing both rendering arms on development data is in-sample tuning; the selection rule is fixed in advance.

Hide arm names and the hypothesis from correctors and raters; present outputs with labels A/B in random order. Rendering style may reveal an arm, so record this limitation rather than claiming complete blinding. Record all correction and review time as it happens; never estimate or invent times.

## Owner handoff checklist (minimum)
- [ ] Role counts and anonymized IDs: 2 labelers, 2 correctors, 3 raters, 1 fresh held-out reader, 1 scorer reviewer.
- [ ] Rights-cleared source sheets with evidence (6 development, 2 held-out).
- [ ] Independent reviewers' availability for returns and reconciliation.
- [ ] Reviewer returns and source images kept out of public Git commits and external uploads; this guide holds no private filenames, paths, hashes or data.
