### API outcome per input (gate enforced) and full-score accuracy

"Notes exact" etc. are measured on the full score the API returned, or — marked *(withheld)* — on the full score the gate refused to return (ungated run), so the gate decision can be checked.

| Input | Set | Class | Condition | API outcome | Gate reason | Staff px | Bad bars | Notes exact | Rhythm | Chords R / P | Key sig | Integrity | Time (s) | Peak RSS py / tools |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| jusim | dev | ordinary_pdf | key+2 (cold) | **full_score** | full_score_allowed | 21.0 | 0/25 | 97.1% | 97.5% | 86.8% / 97.1% | 100.0% | ok | 30.2 | 1114 / 1114 MB |
| jusim | dev | ordinary_pdf | capo-2 | **full_score** | full_score_allowed | 21.0 | 0/25 | 97.1% | 97.5% | 86.8% / 97.1% | 100.0% | ok | 25.4 | 1164 / 1164 MB |
| jayu | dev | ordinary_pdf | key-2 | **full_score** | full_score_allowed | 22.0 | 0/33 | 100.0% | 100.0% | 98.4% / 98.4% | 100.0% | ok | 35.4 | 1199 / 1199 MB |
| jayu | dev | ordinary_pdf | capo-3 | **full_score** | full_score_allowed | 22.0 | 0/33 | 100.0% | 100.0% | 98.4% / 98.4% | 100.0% | ok | 36.6 | 1218 / 1218 MB |
| chingu | dev | ordinary_pdf | key+2 | **full_score** | full_score_allowed | 21.0 | 0/27 | 100.0% | 100.0% | 94.4% / 94.4% | 100.0% | ok | 27.3 | 1229 / 1229 MB |
| chingu | dev | ordinary_pdf | capo-2 | **full_score** | full_score_allowed | 21.0 | 0/27 | 100.0% | 100.0% | 94.4% / 94.4% | 100.0% | ok | 26.8 | 1233 / 1233 MB |
| naui | dev | phone_or_web_image | key-2 | **chord_only** | preflight:staff_spacing_too_small | 6.0 | 14/31 | 77.8% *(withheld)* | 79.1% | 81.0% / 90.4% | 93.8% | ok | 22.9 (+33 ungated) | 1377 / 1377 MB |
| naui | dev | phone_or_web_image | capo-2 | **chord_only** | preflight:staff_spacing_too_small | 6.0 | 14/31 | 77.8% *(withheld)* | 79.1% | 81.0% / 90.4% | 93.8% | ok | 23.1 (+35 ungated) | 1379 / 1379 MB |

### Gate decisions vs. usefulness (full score usable = pitched notes exact >= 95%)

| Set | Full score returned, usable | Full score returned, NOT usable (unsafe) | Withheld, would have been unusable (correct fallback) | Withheld, would have been usable (unnecessary) | Errors |
|---|---|---|---|---|---|
| dev | 6 | 0 | 2<br><sub>naui key-2, naui capo-2</sub> | 0 | 0 |

An "error" with a gate reason means the gate fell back to chord-only but chord recognition was not available in that run (PaddleOCR missing), so the API would answer 422 rather than a fabricated score.

### Pooled accuracy of full scores the API actually returned (key-change runs)

- **dev, returned** (3 runs): notes exact 99.2% of 620 notes (pitch only 99.5%); chords recall 94.2%, precision 97.0% of 138 chords.
- **dev, withheld by the gate** (1 runs): notes exact 77.8% of 153 notes (pitch only 86.9%); chords recall 81.0%, precision 90.4% of 58 chords.

Chord-only accepted: 2; rejected for insufficient confidence: 0.

### Chord-only fallback: transposed chord labels vs the transposed reference

Position-free multiset comparison (the fallback draws labels on the page, it has no measure structure). Recall = reference chords found; precision = drawn chords that are correct. A run with no chord at all is now an explicit 422 error, not a result.

| Input | Set | Condition | Reference chords | Drawn | Recall | Precision | Recall incl. enharmonic |
|---|---|---|---|---|---|---|---|
| naui | dev | key-2 | 58 | 58 | 94.8% | 94.8% | 94.8% |
| naui | dev | capo-2 | 58 | 58 | 94.8% | 94.8% | 94.8% |
| **pooled** | | | 116 | 116 | 94.8% | 94.8% | |

### Error classes (all runs with a full-score path)

| Input | Condition | Recognition (notes) | Transposition (notes) | Rendering (MuseScore, notes) | Chord recognition | Chord mapping | Chord transposition | Lyrics v1 chars |
|---|---|---|---|---|---|---|---|---|
| jusim | key+2 | 6 | 0 | 0 | 4 | 1 | 0 | 44.7% |
| jusim | capo-2 | 6 | 0 | 0 | 4 | 1 | 0 | 44.7% |
| jayu | key-2 | 0 | 0 | 0 | 1 | 0 | 0 | 50.5% |
| jayu | capo-3 | 0 | 0 | 0 | 1 | 0 | 0 | 50.5% |
| chingu | key+2 | 0 | 0 | 0 | 2 | 0 | 0 | 55.5% |
| chingu | capo-2 | 0 | 0 | 0 | 2 | 0 | 0 | 55.5% |
| naui | key-2 | 47 | 0 | 1 | 6 | 5 | 0 | 53.2% |
| naui | capo-2 | 47 | 0 | 1 | 6 | 5 | 0 | 53.2% |
| **total** | | 106 | 0 | 2 | 26 | 12 | 0 | |

### Discrepancies (recognised score vs reference, before transposition)

<details><summary><b>jusim</b> (full_score): 6 note/rest differences, 5 missed or wrong chords</summary>

| Bar (ref) | Beat | Expected | Found |
|---|---|---|---|
| 9 | 1 | A4/1/2 | (missing) |
| 9 | 3/2 | G4/1/4 | (missing) |
| 9 | 7/4 | A4/1/4 | (missing) |
| 9 | 3 | rest/1/2 | G4/1/2 |
| 9 | 7/2 | A4/1/4 | A4/1/2 |
| 9 | 15/4 | A4/1/4 | A4/1 |

| Bar (ref) | Beat | Expected chord | Class | Chords found in that bar |
|---|---|---|---|---|
| 4 | 0 | Bbadd2 | recognition | Bbm6@2 |
| 8 | 0 | Bbadd2 | recognition | Bbm6@3 |
| 8 | 2 | Bbm6 | mapping | Bbm6@3 |
| 16 | 0 | Bbadd2 | recognition | – |
| 16 | 2 | Bbm6 | recognition | – |

</details>

<details><summary><b>jayu</b> (full_score): 0 note/rest differences, 1 missed or wrong chords</summary>

| Bar (ref) | Beat | Expected chord | Class | Chords found in that bar |
|---|---|---|---|---|
| 18 | 0 | A7/C# | recognition | A@0, Dm7@2 |

</details>

<details><summary><b>chingu</b> (full_score): 0 note/rest differences, 2 missed or wrong chords</summary>

| Bar (ref) | Beat | Expected chord | Class | Chords found in that bar |
|---|---|---|---|---|
| 2 | 2 | Dm711 | recognition | C@0, Dm@2 |
| 10 | 2 | Dm711 | recognition | C@0, Dm@2 |

</details>

<details><summary><b>naui</b> (chord_only): 47 note/rest differences, 11 missed or wrong chords</summary>

| Bar (ref) | Beat | Expected | Found |
|---|---|---|---|
| 2 | 0 | B3/1/2 | B3/1 |
| 2 | 1/2 | G4/1/2 | E5/1 |
| 2 | 2 | G4/3/2 | G4/1 |
| 2 | 7/2 | rest/1/2 | E4/1/2 |
| 3 | 0 | E4/1/2 | G4/1/2 |
| 7 | 1/2 | C#4/1/2 | C#4/3/4 |
| 7 | 3/2 | A3/1/2 | C#4/3/2 |
| 7 | 2 | A3/1 | D4/3/4 |
| 7 | 3 | A3/1/2 | D4/1/2 |
| 8 | 0 | D4/1/2 | D4/3/4 |
| 9 | 0 | (extra) | E5/2 |
| 9 | 0 | E4/3 | E4/2 |
| 9 | 3 | rest/1 | F#4/1 |
| 10 | 0 | F#4/1 | E4/1 |
| 11 | 3/2 | rest/1/2 | (missing) |
| 12 | 7/2 | rest/1/2 | (missing) |
| 16 | 1 | B3/1/2 | B3/1 |
| 16 | 3/2 | E4/1/2 | C#5/1 |
| 16 | 2 | D4/3/2 | D4/1 |
| 16 | 7/2 | rest/1/2 | B3/1/2 |
| 17 | 0 | B3/1/2 | D4/1/2 |
| 22 | 0 | A4/7/2 | A4/2 |
| 22 | 7/2 | rest/1/2 | (missing) |
| 23 | 3 | rest/1/2 | (missing) |
| 24 | 3 | rest/1/2 | C4/1 |
| 25 | 0 | A4/1/2 | (missing) |
| 25 | 1/2 | A4/1/2 | (missing) |
| 25 | 1 | A4/1/2 | (missing) |
| 25 | 3/2 | G4/1/2 | (missing) |
| 25 | 2 | G4/1/2 | (missing) |
| 25 | 5/2 | E4/1/2 | (missing) |
| 25 | 3 | E4/1/2 | (missing) |
| 25 | 7/2 | D4/1/2 | (missing) |
| 26 | 7/2 | rest/1/2 | (missing) |
| 27 | 2 | G4/1/2 | G4/1 |
| 27 | 5/2 | E4/1/2 | E4/1 |
| 27 | 3 | D4/1/2 | (missing) |
| 27 | 7/2 | C4/1/2 | (missing) |
| 28 | 0 | C4/1 | C4/3/2 |
| 28 | 7/2 | D4/1/2 | (missing) |
| 29 | 5/2 | C4/1/2 | D4/3/4 |
| 29 | 3 | A4/1 | A4/3/4 |
| 30 | 0 | G4/7/2 | G4/2 |
| 29 | 2 | (extra) | A4/1/4 |
| 30 | 0 | (extra) | E5/2 |
| 30 | 2 | (extra) | D4/2 |
| 32 | 0 | D4/4 | D4/2 |

| Bar (ref) | Beat | Expected chord | Class | Chords found in that bar |
|---|---|---|---|---|
| 6 | 3 | D/F# | recognition | G2@0, D/F@3 |
| 7 | 2 | D/F# | recognition | Em7@0, D/F@7/4 |
| 9 | 0 | Em7/A | mapping | Em7/A@2 |
| 9 | 3 | A | recognition | Em7/A@2 |
| 16 | 2 | D/F# | recognition | Em9@0, D/F@3 |
| 20 | 3 | G/D | recognition | D@0, A/D@2 |
| 21 | 2 | A/D | mapping | D@0 |
| 21 | 3 | G/D | recognition | D@0 |
| 25 | 0 | Gm9 | mapping | Am7@0, Dm@2 |
| 25 | 2 | C | mapping | Am7@0, Dm@2 |
| 31 | 0 | D | mapping | – |

</details>

