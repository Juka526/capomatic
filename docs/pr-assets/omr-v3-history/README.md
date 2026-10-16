# Earlier V3 evaluation rounds (kept for the blind hold-out record)

Each round ran the same `scripts/omr_v3/evaluate.py` in the production Docker image on CI.

| Round | Commit | CI run | Blind hold-out | What was changed afterwards |
|---|---|---|---|---|
| 1 | `95318f3` | [38853905234](https://github.com/Juka526/capomatic/actions/runs/38853905234) | synthetic 201-204 | chord-only with no recognised chord became a 422; chord label filed as composer dropped (both found by inspecting 201-204 outputs) |
| 2 | `a96b574` | [38860946583](https://github.com/Juka526/capomatic/actions/runs/38860946583) | synthetic 205-208 | ledger repair rewritten: it moved D4 to C4 on degraded rasters (found on 208) |

After each round its hold-out seeds were moved to dev and fresh seeds were generated, so the
final evaluation in `../omr-v3/` uses seeds that were never inspected (209-212).
Round 1's chord-only accuracy was computed afterwards from that run's outputs with the same
function (`compare.chord_text_accuracy`); every other number is as produced on CI.
Full outputs (PDF, MusicXML, side-by-side) of these rounds are not kept; only the summaries.
