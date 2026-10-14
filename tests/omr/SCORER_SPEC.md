# Melody acceptance scorer: specification draft (tester-owned, NOT APPROVED)

Status: spec only. `tests/omr/scorer.py` does not exist on purpose. Writing it before the prerequisites below are fixed would let the scorer's own choices define truth (designer = verifier). No model or engine output has been scored, and no accuracy number exists.

## Prerequisites that need human or owner approval before the scorer is written

1. **Alignment rule and tolerance.** The rule matches events by the independent label's original x position in printed order: snippet → system → measure → left to right. The pixel tolerance comes from development data only and is then frozen. Inherited plan §5. A second reviewer, not a developer, approves it.
2. **Spelling policy for transposed notes.** For example, F♯ major E♯ is written as F♮ under the chord rule. The plan says this policy is under music review. Until it is fixed, expected spellings cannot be written; only expected MIDI numbers can.
3. **Real labels.** Readers A and B are independent; a fresh held-out reader is required; roles are disjoint. A synthetic fixture can never stand in for this.
4. **Pickup, repeat and tie conventions in the label files.** These must be signed off before Lock A.

## Fixed formulas (from the plan; not tunable)

- `N` = labelled sounding events. `FP` = predicted events with no match.
- Pitch accuracy = exact-MIDI matches / (N + FP). Missing notes, extra notes and octave errors are all wrong.
- Rhythm accuracy uses the same denominator and includes rests. A match counts only when onset, duration and tie are all correct.
- Report both the aggregate score and the worst per-snippet score. Silent-error count is reported per note and per snippet.

## Hand-authored oracle cases (for the future scorer's own tests)

| Case | Truth | Prediction | Expected pitch accuracy |
| --- | --- | --- | --- |
| all correct | C4 D4 E4 F4 (60 62 64 65) | 60 62 64 65 | 4/4 |
| one octave error | 60 62 64 65 | 60 62 76 65 | 3/4 |
| one missing | 60 62 64 65 | 60 62 65 (E4 absent) | 3/4 |
| one extra | 60 62 64 65 | 60 62 64 65 + 67 | 4/5 |
| extra + missing | 60 62 64 65 | 60 62 65 + 67 | 3/5 |

MIDI-only transposition truth. Spelling is pending item 2. These values were hand-calculated: B♭4 = 70, C♯5 = 73, A4 = 69.

| Shift | 70 → | 73 → | 69 → |
| --- | --- | --- | --- |
| −11 | 59 | 62 | 58 |
| −7 | 63 | 66 | 62 |
| −2 | 68 | 71 | 67 |
| 0 | 70 | 73 | 69 |
| +1 | 71 | 74 | 70 |
| +5 | 75 | 78 | 74 |
| +11 | 81 | 84 | 80 |

The scorer's own tests must show that each guard fires on a known-bad synthetic case before a "no error" result is trusted (T5): an octave error, a missing note, an extra note, a wrong tie and a moved protected pixel.
