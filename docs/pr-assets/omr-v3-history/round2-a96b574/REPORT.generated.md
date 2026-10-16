### API outcome per input (gate enforced) and full-score accuracy

"Notes exact" etc. are measured on the full score the API returned, or — marked *(withheld)* — on the full score the gate refused to return (ungated run), so the gate decision can be checked.

| Input | Set | Class | Condition | API outcome | Gate reason | Staff px | Bad bars | Notes exact | Rhythm | Chords R / P | Key sig | Integrity | Time (s) | Peak RSS py / tools |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| jusim | dev | ordinary_pdf | key+2 (cold) | **full_score** | full_score_allowed | 21.0 | 0/25 | 97.1% | 97.5% | 86.8% / 97.1% | 100.0% | ok | 45.4 | 1090 / 1090 MB |
| jusim | dev | ordinary_pdf | capo-2 | **full_score** | full_score_allowed | 21.0 | 0/25 | 97.1% | 97.5% | 86.8% / 97.1% | 100.0% | ok | 42.3 | 1134 / 1134 MB |
| jayu | dev | ordinary_pdf | key-2 | **full_score** | full_score_allowed | 22.0 | 0/33 | 100.0% | 100.0% | 98.4% / 98.4% | 100.0% | ok | 58.6 | 1147 / 1147 MB |
| jayu | dev | ordinary_pdf | capo-3 | **full_score** | full_score_allowed | 22.0 | 0/33 | 100.0% | 100.0% | 98.4% / 98.4% | 100.0% | ok | 55.9 | 1171 / 1171 MB |
| chingu | dev | ordinary_pdf | key+2 | **full_score** | full_score_allowed | 21.0 | 0/27 | 100.0% | 100.0% | 94.4% / 94.4% | 100.0% | ok | 39.8 | 1183 / 1183 MB |
| chingu | dev | ordinary_pdf | capo-2 | **full_score** | full_score_allowed | 21.0 | 0/27 | 100.0% | 100.0% | 94.4% / 94.4% | 100.0% | ok | 40.4 | 1203 / 1203 MB |
| naui | dev | phone_or_web_image | key-2 | **chord_only** | preflight:staff_spacing_too_small | 6.0 | 14/31 | 77.8% *(withheld)* | 79.1% | 81.0% / 90.4% | 93.8% | ok | 34.6 (+51 ungated) | 1351 / 1351 MB |
| naui | dev | phone_or_web_image | capo-2 | **chord_only** | preflight:staff_spacing_too_small | 6.0 | 14/31 | 77.8% *(withheld)* | 79.1% | 81.0% / 90.4% | 93.8% | ok | 35.0 (+53 ungated) | 1354 / 1354 MB |
| syn101-clean | synthetic-dev | clean | key+2 | **full_score** | full_score_allowed | 21.0 | 1/20 | 97.0% | 97.0% | 100.0% / 95.2% | 100.0% | ok | 25.9 | 1354 / 1354 MB |
| syn101-ordinary | synthetic-dev | ordinary | key+2 | **full_score** | full_score_allowed | 14.0 | 0/20 | 95.4% | 100.0% | 50.0% / 83.3% | 100.0% | ok | 30.7 | 2296 / 2296 MB |
| syn101-scan | synthetic-dev | scan | key+2 | **chord_only** | preflight:staff_spacing_too_small | 10.0 | 6/20 | 92.4% *(withheld)* | 91.8% | 100.0% / 100.0% | 100.0% | ok | 26.5 (+36 ungated) | 2296 / 2296 MB |
| syn101-phone | synthetic-dev | phone | key+2 | **chord_only** | preflight:staff_spacing_too_small | 13.0 | 0/20 | 97.7% *(withheld)* | 100.0% | 95.0% / 100.0% | 100.0% | ok | 20.1 (+32 ungated) | 2296 / 2296 MB |
| syn101-musicxml | synthetic-dev | musicxml | key+2 | **full_score** | musicxml_input | – | – | 100.0% | 100.0% | 100.0% / 100.0% | 100.0% | ok | 0.7 | 2296 / 2296 MB |
| syn102-clean | synthetic-dev | clean | key-2 | **full_score** | full_score_allowed | 21.0 | 0/20 | 100.0% | 100.0% | 100.0% / 100.0% | 100.0% | ok | 25.9 | 2296 / 2296 MB |
| syn102-ordinary | synthetic-dev | ordinary | key-2 | **full_score** | full_score_allowed | 14.0 | 1/20 | 97.7% | 98.6% | 90.0% / 100.0% | 100.0% | ok | 34.1 | 2296 / 2296 MB |
| syn102-scan | synthetic-dev | scan | key-2 | **chord_only** | preflight:staff_spacing_too_small | 10.0 | 9/20 | 84.5% *(withheld)* | 84.2% | 80.0% / 88.9% | 100.0% | ok | 22.2 (+34 ungated) | 2296 / 2296 MB |
| syn102-phone | synthetic-dev | phone | key-2 | **chord_only** | preflight:staff_spacing_too_small | 13.0 | 2/20 | 94.6% *(withheld)* | 96.4% | 95.0% / 100.0% | 100.0% | ok | 18.1 (+29 ungated) | 2296 / 2296 MB |
| syn102-musicxml | synthetic-dev | musicxml | key-2 | **full_score** | musicxml_input | – | – | 100.0% | 100.0% | 100.0% / 100.0% | 100.0% | ok | 0.6 | 2296 / 2296 MB |
| syn103-clean | synthetic-dev | clean | key+3 | **full_score** | full_score_allowed | 21.0 | 1/24 | 97.9% | 97.0% | 88.2% / 88.2% | 100.0% | ok | 34.1 | 2296 / 2296 MB |
| syn103-ordinary | synthetic-dev | ordinary | key+3 | **full_score** | full_score_allowed | 14.0 | 0/24 | 99.5% | 100.0% | 91.2% / 91.2% | 100.0% | ok | 44.4 | 2296 / 2296 MB |
| syn103-scan | synthetic-dev | scan | key+3 | **chord_only** | preflight:staff_spacing_too_small | 10.0 | 8/24 | 93.2% *(withheld)* | 91.6% | 88.2% / 85.7% | 100.0% | ok | 31.7 (+45 ungated) | 2296 / 2296 MB |
| syn103-phone | synthetic-dev | phone | key+3 | **chord_only** | preflight:staff_spacing_too_small | 13.0 | 0/24 | 90.5% *(withheld)* | 100.0% | 88.2% / 93.8% | 100.0% | ok | 24.2 (+39 ungated) | 2296 / 2296 MB |
| syn103-musicxml | synthetic-dev | musicxml | key+3 | **full_score** | musicxml_input | – | – | 100.0% | 100.0% | 100.0% / 100.0% | 100.0% | ok | 0.9 | 2296 / 2296 MB |
| syn201-clean | synthetic-dev | clean | key-3 | **chord_only** | omr:too_many_inconsistent_bars | 21.0 | 2/20 | 94.7% *(withheld)* | 95.0% | 100.0% / 100.0% | 100.0% | ok | 33.2 (+34 ungated) | 2296 / 2296 MB |
| syn201-ordinary | synthetic-dev | ordinary | key-3 | **full_score** | full_score_allowed | 14.0 | 0/20 | 94.7% | 99.5% | 93.9% / 100.0% | 100.0% | ok | 37.3 | 2296 / 2296 MB |
| syn201-scan | synthetic-dev | scan | key-3 | **chord_only** | preflight:staff_spacing_too_small | 10.0 | 6/19 | 86.4% *(withheld)* | 86.3% | 63.6% / 95.5% | 100.0% | ok | 25.0 (+40 ungated) | 2296 / 2296 MB |
| syn201-phone | synthetic-dev | phone | key-3 | **chord_only** | preflight:staff_spacing_too_small | 13.0 | 1/20 | 89.9% *(withheld)* | 98.4% | 93.9% / 100.0% | 100.0% | ok | 26.6 (+40 ungated) | 2296 / 2296 MB |
| syn201-musicxml | synthetic-dev | musicxml | key-3 | **full_score** | musicxml_input | – | – | 100.0% | 100.0% | 100.0% / 100.0% | 100.0% | ok | 0.9 | 2296 / 2296 MB |
| syn202-clean | synthetic-dev | clean | key+2 | **full_score** | full_score_allowed | 21.0 | 0/20 | 100.0% | 100.0% | 90.9% / 100.0% | 100.0% | ok | 31.6 | 2296 / 2296 MB |
| syn202-ordinary | synthetic-dev | ordinary | key+2 | **full_score** | full_score_allowed | 14.0 | 1/20 | 96.1% | 99.0% | 81.8% / 87.1% | 100.0% | ok | 39.9 | 2296 / 2296 MB |
| syn202-scan | synthetic-dev | scan | key+2 | **chord_only** | preflight:staff_spacing_too_small | 10.0 | 7/20 | 91.1% *(withheld)* | 90.0% | 54.5% / 85.7% | 100.0% | ok | 48.8 (+61 ungated) | 3505 / 3505 MB |
| syn202-phone | synthetic-dev | phone | key+2 | **chord_only** | preflight:staff_spacing_too_small | 13.0 | 1/20 | 89.4% *(withheld)* | 99.0% | 42.4% / 93.3% | 100.0% | ok | 20.2 (+35 ungated) | 3505 / 3505 MB |
| syn202-musicxml | synthetic-dev | musicxml | key+2 | **full_score** | musicxml_input | – | – | 100.0% | 100.0% | 100.0% / 100.0% | 100.0% | ok | 0.8 | 3505 / 3505 MB |
| syn203-clean | synthetic-dev | clean | key-2 | **full_score** | full_score_allowed | 21.0 | 1/20 | 97.5% | 97.1% | 100.0% / 96.5% | 100.0% | ok | 29.7 | 3505 / 3505 MB |
| syn203-ordinary | synthetic-dev | ordinary | key-2 | **chord_only** | omr:too_many_inconsistent_bars | 14.0 | 2/20 | 89.4% *(withheld)* | 94.2% | 96.4% / 93.1% | 100.0% | ok | 39.0 (+40 ungated) | 3505 / 3505 MB |
| syn203-scan | synthetic-dev | scan | key-2 | **chord_only** | preflight:staff_spacing_too_small | 10.0 | 6/20 | 95.7% *(withheld)* | 94.8% | 96.4% / 96.4% | 100.0% | ok | 31.1 (+43 ungated) | 3505 / 3505 MB |
| syn203-phone | synthetic-dev | phone | key-2 | **chord_only** | preflight:staff_spacing_too_small | 13.0 | 0/20 | 83.9% *(withheld)* | 100.0% | 96.4% / 96.4% | 100.0% | ok | 25.7 (+39 ungated) | 3505 / 3505 MB |
| syn203-musicxml | synthetic-dev | musicxml | key-2 | **full_score** | musicxml_input | – | – | 100.0% | 100.0% | 100.0% / 100.0% | 100.0% | ok | 0.7 | 3505 / 3505 MB |
| syn204-clean | synthetic-dev | clean | key+3 | **full_score** | full_score_allowed | 21.0 | 1/24 | 99.5% | 99.5% | 100.0% / 97.5% | 100.0% | ok | 37.0 | 3505 / 3505 MB |
| syn204-ordinary | synthetic-dev | ordinary | key+3 | **chord_only** | omr:too_many_inconsistent_bars | 14.0 | 2/24 | 96.1% *(withheld)* | 95.8% | 97.4% / 97.4% | 100.0% | ok | 44.8 (+46 ungated) | 3505 / 3505 MB |
| syn204-scan | synthetic-dev | scan | key+3 | **error (preflight:staff_spacing_too_small)** | preflight:staff_spacing_too_small | 10.0 | 6/24 | 96.1% *(withheld)* | 94.0% | 33.3% / 92.9% | 100.0% | ok | 24.2 (+43 ungated) | 3505 / 3505 MB |
| syn204-phone | synthetic-dev | phone | key+3 | **chord_only** | preflight:staff_spacing_too_small | 13.0 | 2/24 | 92.6% *(withheld)* | 98.1% | 51.3% / 83.3% | 100.0% | ok | 23.2 (+40 ungated) | 3505 / 3505 MB |
| syn204-musicxml | synthetic-dev | musicxml | key+3 | **full_score** | musicxml_input | – | – | 100.0% | 100.0% | 100.0% / 100.0% | 100.0% | ok | 1.0 | 3505 / 3505 MB |
| syn205-clean | synthetic-holdout | clean | key+2 | **chord_only** | omr:too_many_inconsistent_bars | 21.0 | 3/24 | 93.4% *(withheld)* | 93.4% | 94.1% / 91.4% | 100.0% | ok | 37.4 (+36 ungated) | 3505 / 3505 MB |
| syn205-ordinary | synthetic-holdout | ordinary | key+2 | **chord_only** | omr:too_many_inconsistent_bars | 14.0 | 2/24 | 89.3% *(withheld)* | 95.8% | 50.0% / 94.4% | 100.0% | ok | 35.8 (+37 ungated) | 3505 / 3505 MB |
| syn205-scan | synthetic-holdout | scan | key+2 | **chord_only** | preflight:staff_spacing_too_small | 10.0 | 6/24 | 95.4% *(withheld)* | 94.8% | 79.4% / 100.0% | 100.0% | ok | 47.0 (+60 ungated) | 3562 / 3562 MB |
| syn205-phone | synthetic-holdout | phone | key+2 | **chord_only** | preflight:staff_spacing_too_small | 13.0 | 1/24 | 98.5% *(withheld)* | 98.1% | 73.5% / 100.0% | 100.0% | ok | 23.3 (+39 ungated) | 3562 / 3562 MB |
| syn205-musicxml | synthetic-holdout | musicxml | key+2 | **full_score** | musicxml_input | – | – | 100.0% | 100.0% | 100.0% / 100.0% | 100.0% | ok | 0.8 | 3562 / 3562 MB |
| syn206-clean | synthetic-holdout | clean | key-2 | **full_score** | full_score_allowed | 21.0 | 0/20 | 100.0% | 100.0% | 100.0% / 100.0% | 100.0% | ok | 27.6 | 3562 / 3562 MB |
| syn206-ordinary | synthetic-holdout | ordinary | key-2 | **full_score** | full_score_allowed | 14.0 | 1/20 | 96.1% | 99.4% | 96.0% / 100.0% | 100.0% | ok | 33.4 | 3562 / 3562 MB |
| syn206-scan | synthetic-holdout | scan | key-2 | **chord_only** | preflight:staff_spacing_too_small | 10.0 | 11/20 | 77.8% *(withheld)* | 77.1% | 80.0% / 87.0% | 100.0% | ok | 48.3 (+60 ungated) | 3562 / 3562 MB |
| syn206-phone | synthetic-holdout | phone | key-2 | **chord_only** | preflight:staff_spacing_too_small | 13.0 | 1/20 | 92.8% *(withheld)* | 97.5% | 76.0% / 95.0% | 100.0% | ok | 13.7 (+29 ungated) | 3562 / 3562 MB |
| syn206-musicxml | synthetic-holdout | musicxml | key-2 | **full_score** | musicxml_input | – | – | 100.0% | 100.0% | 100.0% / 100.0% | 100.0% | ok | 0.5 | 3562 / 3562 MB |
| syn207-clean | synthetic-holdout | clean | key+3 | **full_score** | full_score_allowed | 21.0 | 0/16 | 100.0% | 100.0% | 100.0% / 100.0% | 100.0% | ok | 27.5 | 3562 / 3562 MB |
| syn207-ordinary | synthetic-holdout | ordinary | key+3 | **full_score** | full_score_allowed | 14.0 | 0/15 | 92.3% | 92.7% | 96.3% / 96.3% | 100.0% | ok | 37.1 | 3562 / 3562 MB |
| syn207-scan | synthetic-holdout | scan | key+3 | **chord_only** | preflight:staff_spacing_too_small | 10.0 | 7/16 | 93.1% *(withheld)* | 90.5% | 81.5% / 95.7% | 100.0% | ok | 49.4 (+60 ungated) | 3562 / 3562 MB |
| syn207-phone | synthetic-holdout | phone | key+3 | **chord_only** | preflight:staff_spacing_too_small | 13.0 | 2/16 | 91.5% *(withheld)* | 98.5% | 51.8% / 100.0% | 100.0% | ok | 21.2 (+34 ungated) | 3562 / 3562 MB |
| syn207-musicxml | synthetic-holdout | musicxml | key+3 | **full_score** | musicxml_input | – | – | 100.0% | 100.0% | 100.0% / 100.0% | 100.0% | ok | 0.7 | 3562 / 3562 MB |
| syn208-clean | synthetic-holdout | clean | key-3 | **chord_only** | omr:too_many_inconsistent_bars | 21.0 | 2/16 | 86.6% *(withheld)* | 87.3% | 100.0% / 94.1% | 100.0% | ok | 23.0 (+23 ungated) | 3562 / 3562 MB |
| syn208-ordinary | synthetic-holdout | ordinary | key-3 | **full_score** | full_score_allowed | 14.0 | 0/16 | 93.8% | 100.0% | 81.2% / 92.9% | 100.0% | ok | 56.0 | 3562 / 3562 MB |
| syn208-scan | synthetic-holdout | scan | key-3 | **chord_only** | preflight:staff_spacing_too_small | 10.0 | 4/16 | 87.5% *(withheld)* | 87.3% | 50.0% / 88.9% | 100.0% | ok | 20.0 (+31 ungated) | 3562 / 3562 MB |
| syn208-phone | synthetic-holdout | phone | key-3 | **chord_only** | preflight:staff_spacing_too_small | 13.0 | 3/16 | 79.5% *(withheld)* | 89.0% | 100.0% / 100.0% | 100.0% | ok | 18.9 (+31 ungated) | 3562 / 3562 MB |
| syn208-musicxml | synthetic-holdout | musicxml | key-3 | **full_score** | musicxml_input | – | – | 100.0% | 100.0% | 100.0% / 100.0% | 100.0% | ok | 0.7 | 3562 / 3562 MB |

### Gate decisions vs. usefulness (full score usable = pitched notes exact >= 95%)

| Set | Full score returned, usable | Full score returned, NOT usable (unsafe) | Withheld, would have been unusable (correct fallback) | Withheld, would have been usable (unnecessary) | Errors |
|---|---|---|---|---|---|
| dev | 6 | 0 | 2<br><sub>naui key-2, naui capo-2</sub> | 0 | 0 |
| synthetic-dev | 17 | 1<br><sub>syn201-ordinary key-3</sub> | 13<br><sub>syn101-scan key+2, syn102-scan key-2, syn102-phone key-2, syn103-scan key+3, syn103-phone key+3, syn201-clean key-3, syn201-scan key-3, syn201-phone key-3, syn202-scan key+2, syn202-phone key+2, syn203-ordinary key-2, syn203-phone key-2, syn204-phone key+3</sub> | 4<br><sub>syn101-phone key+2, syn203-scan key-2, syn204-ordinary key+3, syn204-scan key+3</sub> | 1<br><sub>syn204-scan key+3</sub> |
| synthetic-holdout | 7 | 2<br><sub>syn207-ordinary key+3, syn208-ordinary key-3</sub> | 9<br><sub>syn205-clean key+2, syn205-ordinary key+2, syn206-scan key-2, syn206-phone key-2, syn207-scan key+3, syn207-phone key+3, syn208-clean key-3, syn208-scan key-3, syn208-phone key-3</sub> | 2<br><sub>syn205-scan key+2, syn205-phone key+2</sub> | 0 |

An "error" with a gate reason means the gate fell back to chord-only but chord recognition was not available in that run (PaddleOCR missing), so the API would answer 422 rather than a fabricated score.

### Pooled accuracy of full scores the API actually returned (key-change runs)

- **dev, returned** (3 runs): notes exact 99.2% of 620 notes (pitch only 99.5%); chords recall 94.2%, precision 97.0% of 138 chords.
- **dev, withheld by the gate** (1 runs): notes exact 77.8% of 153 notes (pitch only 86.9%); chords recall 81.0%, precision 90.4% of 58 chords.
- **synthetic-dev, returned** (18 runs): notes exact 98.7% of 2956 notes (pitch only 99.1%); chords recall 94.2%, precision 96.8% of 521 chords.
- **synthetic-dev, withheld by the gate** (17 runs): notes exact 91.7% of 2859 notes (pitch only 95.0%); chords recall 78.4%, precision 94.4% of 514 chords.
- **synthetic-holdout, returned** (9 runs): notes exact 98.2% of 1269 notes (pitch only 98.2%); chords recall 97.7%, precision 99.1% of 222 chords.
- **synthetic-holdout, withheld by the gate** (11 runs): notes exact 90.3% of 1686 notes (pitch only 95.7%); chords recall 75.0%, precision 95.2% of 288 chords.

### Chord-only fallback: transposed chord labels vs the transposed reference

Position-free multiset comparison (the fallback draws labels on the page, it has no measure structure). Recall = reference chords found; precision = drawn chords that are correct. A run with no chord at all is now an explicit 422 error, not a result.

| Input | Set | Condition | Reference chords | Drawn | Recall | Precision | Recall incl. enharmonic |
|---|---|---|---|---|---|---|---|
| naui | dev | key-2 | 58 | 58 | 94.8% | 94.8% | 94.8% |
| naui | dev | capo-2 | 58 | 58 | 94.8% | 94.8% | 94.8% |
| syn101-scan | synthetic-dev | key+2 | 20 | 20 | 100.0% | 100.0% | 100.0% |
| syn101-phone | synthetic-dev | key+2 | 20 | 18 | 90.0% | 100.0% | 90.0% |
| syn102-scan | synthetic-dev | key-2 | 20 | 11 | 55.0% | 100.0% | 55.0% |
| syn102-phone | synthetic-dev | key-2 | 20 | 18 | 90.0% | 100.0% | 90.0% |
| syn103-scan | synthetic-dev | key+3 | 34 | 27 | 73.5% | 92.6% | 73.5% |
| syn103-phone | synthetic-dev | key+3 | 34 | 13 | 38.2% | 100.0% | 38.2% |
| syn201-clean | synthetic-dev | key-3 | 33 | 33 | 100.0% | 100.0% | 100.0% |
| syn201-scan | synthetic-dev | key-3 | 33 | 9 | 27.3% | 100.0% | 27.3% |
| syn201-phone | synthetic-dev | key-3 | 33 | 20 | 60.6% | 100.0% | 60.6% |
| syn202-scan | synthetic-dev | key+2 | 33 | 17 | 51.5% | 100.0% | 51.5% |
| syn202-phone | synthetic-dev | key+2 | 33 | 7 | 21.2% | 100.0% | 21.2% |
| syn203-ordinary | synthetic-dev | key-2 | 28 | 28 | 100.0% | 100.0% | 100.0% |
| syn203-scan | synthetic-dev | key-2 | 28 | 28 | 100.0% | 100.0% | 100.0% |
| syn203-phone | synthetic-dev | key-2 | 28 | 23 | 82.1% | 100.0% | 82.1% |
| syn204-ordinary | synthetic-dev | key+3 | 39 | 39 | 100.0% | 100.0% | 100.0% |
| syn204-phone | synthetic-dev | key+3 | 39 | 9 | 23.1% | 100.0% | 23.1% |
| syn205-clean | synthetic-holdout | key+2 | 34 | 34 | 100.0% | 100.0% | 100.0% |
| syn205-ordinary | synthetic-holdout | key+2 | 34 | 5 | 14.7% | 100.0% | 14.7% |
| syn205-scan | synthetic-holdout | key+2 | 34 | 15 | 44.1% | 100.0% | 44.1% |
| syn205-phone | synthetic-holdout | key+2 | 34 | 14 | 41.2% | 100.0% | 41.2% |
| syn206-scan | synthetic-holdout | key-2 | 25 | 15 | 60.0% | 100.0% | 60.0% |
| syn206-phone | synthetic-holdout | key-2 | 25 | 11 | 44.0% | 100.0% | 44.0% |
| syn207-scan | synthetic-holdout | key+3 | 27 | 17 | 63.0% | 100.0% | 63.0% |
| syn207-phone | synthetic-holdout | key+3 | 27 | 2 | 7.4% | 100.0% | 7.4% |
| syn208-clean | synthetic-holdout | key-3 | 16 | 16 | 100.0% | 100.0% | 100.0% |
| syn208-scan | synthetic-holdout | key-3 | 16 | 5 | 31.2% | 100.0% | 31.2% |
| syn208-phone | synthetic-holdout | key-3 | 16 | 16 | 100.0% | 100.0% | 100.0% |
| **pooled** | | | 879 | 586 | 65.8% | 98.6% | |

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
| syn101-clean | key+2 | 4 | 0 | 0 | 0 | 0 | 0 | 43.9% |
| syn101-ordinary | key+2 | 6 | 0 | 0 | 8 | 2 | 0 | 57.7% |
| syn101-scan | key+2 | 14 | 0 | 0 | 0 | 0 | 0 | 65.8% |
| syn101-phone | key+2 | 3 | 0 | 0 | 1 | 0 | 0 | 79.7% |
| syn101-musicxml | key+2 | 0 | 0 | 0 | 0 | 0 | 0 | 100.0% |
| syn102-clean | key-2 | 0 | 0 | 0 | 0 | 0 | 0 | 22.8% |
| syn102-ordinary | key-2 | 4 | 0 | 1 | 2 | 0 | 0 | 74.0% |
| syn102-scan | key-2 | 25 | 0 | 0 | 2 | 2 | 0 | 63.4% |
| syn102-phone | key-2 | 9 | 0 | 1 | 1 | 0 | 0 | 85.4% |
| syn102-musicxml | key-2 | 0 | 0 | 0 | 0 | 0 | 0 | 100.0% |
| syn103-clean | key+3 | 6 | 0 | 0 | 1 | 3 | 0 | 84.3% |
| syn103-ordinary | key+3 | 1 | 0 | 0 | 1 | 2 | 0 | 81.4% |
| syn103-scan | key+3 | 24 | 0 | 0 | 2 | 2 | 0 | 63.4% |
| syn103-phone | key+3 | 18 | 0 | 0 | 2 | 2 | 0 | 91.9% |
| syn103-musicxml | key+3 | 0 | 0 | 0 | 0 | 0 | 0 | 100.0% |
| syn201-clean | key-3 | 9 | 0 | 0 | 0 | 0 | 0 | 28.1% |
| syn201-ordinary | key-3 | 10 | 0 | 0 | 2 | 0 | 0 | 87.6% |
| syn201-scan | key-3 | 29 | 0 | 1 | 10 | 2 | 0 | 64.7% |
| syn201-phone | key-3 | 18 | 0 | 0 | 2 | 0 | 0 | 92.2% |
| syn201-musicxml | key-3 | 0 | 0 | 0 | 0 | 0 | 0 | 100.0% |
| syn202-clean | key+2 | 0 | 0 | 0 | 3 | 0 | 0 | 91.9% |
| syn202-ordinary | key+2 | 9 | 0 | 0 | 3 | 3 | 0 | 88.1% |
| syn202-scan | key+2 | 23 | 0 | 0 | 12 | 3 | 0 | 71.2% |
| syn202-phone | key+2 | 20 | 0 | 0 | 16 | 3 | 0 | 92.5% |
| syn202-musicxml | key+2 | 0 | 0 | 0 | 0 | 0 | 0 | 100.0% |
| syn203-clean | key-2 | 5 | 0 | 0 | 0 | 0 | 0 | 79.0% |
| syn203-ordinary | key-2 | 17 | 0 | 0 | 0 | 1 | 0 | 83.1% |
| syn203-scan | key-2 | 10 | 0 | 1 | 0 | 1 | 0 | 66.9% |
| syn203-phone | key-2 | 26 | 0 | 0 | 1 | 0 | 0 | 86.5% |
| syn203-musicxml | key-2 | 0 | 0 | 0 | 0 | 0 | 0 | 100.0% |
| syn204-clean | key+3 | 1 | 0 | 0 | 0 | 0 | 0 | 90.9% |
| syn204-ordinary | key+3 | 10 | 0 | 0 | 0 | 1 | 0 | 50.0% |
| syn204-scan | key+3 | 15 | 0 | 0 | 25 | 1 | 0 | 71.0% |
| syn204-phone | key+3 | 16 | 0 | 0 | 15 | 4 | 0 | 87.6% |
| syn204-musicxml | key+3 | 0 | 0 | 0 | 0 | 0 | 0 | 100.0% |
| syn205-clean | key+2 | 14 | 0 | 1 | 0 | 2 | 0 | 24.7% |
| syn205-ordinary | key+2 | 24 | 0 | 0 | 16 | 1 | 0 | 80.8% |
| syn205-scan | key+2 | 14 | 0 | 0 | 7 | 0 | 0 | 70.3% |
| syn205-phone | key+2 | 5 | 0 | 0 | 9 | 0 | 0 | 91.8% |
| syn205-musicxml | key+2 | 0 | 0 | 0 | 0 | 0 | 0 | 100.0% |
| syn206-clean | key-2 | 0 | 0 | 0 | 0 | 0 | 0 | 28.1% |
| syn206-ordinary | key-2 | 6 | 0 | 0 | 1 | 0 | 0 | 86.3% |
| syn206-scan | key-2 | 40 | 0 | 1 | 2 | 3 | 0 | 71.2% |
| syn206-phone | key-2 | 11 | 0 | 0 | 5 | 1 | 0 | 52.5% |
| syn206-musicxml | key-2 | 0 | 0 | 0 | 0 | 0 | 0 | 100.0% |
| syn207-clean | key+3 | 0 | 0 | 0 | 0 | 0 | 0 | 92.4% |
| syn207-ordinary | key+3 | 10 | 0 | 0 | 0 | 1 | 0 | 83.9% |
| syn207-scan | key+3 | 15 | 0 | 0 | 4 | 1 | 0 | 72.9% |
| syn207-phone | key+3 | 13 | 0 | 0 | 12 | 1 | 0 | 83.9% |
| syn207-musicxml | key+3 | 0 | 0 | 0 | 0 | 0 | 0 | 100.0% |
| syn208-clean | key-3 | 15 | 0 | 1 | 0 | 0 | 0 | 3.9% |
| syn208-ordinary | key-3 | 7 | 0 | 0 | 3 | 0 | 0 | 64.7% |
| syn208-scan | key-3 | 15 | 0 | 0 | 7 | 1 | 0 | 65.7% |
| syn208-phone | key-3 | 25 | 0 | 2 | 0 | 0 | 0 | 13.7% |
| syn208-musicxml | key-3 | 0 | 0 | 0 | 0 | 0 | 0 | 100.0% |
| **total** | | 652 | 0 | 11 | 201 | 55 | 0 | |

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
| 7 | 2 | A3/1 | C#4/3/4 |
| 7 | 3 | A3/1/2 | D4/1/2 |
| 8 | 0 | D4/1/2 | C#4/3/4 |
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
| 29 | 5/2 | C4/1/2 | C4/3/4 |
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

<details><summary><b>syn101-clean</b> (full_score): 4 note/rest differences, 0 missed or wrong chords</summary>

| Bar (ref) | Beat | Expected | Found |
|---|---|---|---|
| 13 | 0 | D5/1/2 | D5/1/3 |
| 13 | 1/2 | E5/1/2 | E5/1/3 |
| 13 | 1 | E5/1/4 | E5/1/6 |
| 13 | 5/4 | G#5/1/4 | G#5/1/6 |

</details>

<details><summary><b>syn101-ordinary</b> (full_score): 6 note/rest differences, 10 missed or wrong chords</summary>

| Bar (ref) | Beat | Expected | Found |
|---|---|---|---|
| 5 | 1 | G5/1/4 | A5/1/4 |
| 9 | 2 | G#5/1 | A5/1 |
| 15 | 1/2 | G#5/1/4 | A5/1/4 |
| 15 | 3/4 | G#5/1/4 | A5/1/4 |
| 15 | 1 | G#5/1/2 | A5/1/2 |
| 16 | 3/4 | G#5/1/4 | A5/1/4 |

| Bar (ref) | Beat | Expected chord | Class | Chords found in that bar |
|---|---|---|---|---|
| 1 | 0 | Esus4 | mapping | Esus4@1 |
| 2 | 0 | A/C# | recognition | – |
| 3 | 0 | E7 | recognition | – |
| 4 | 0 | A | recognition | – |
| 6 | 0 | A | recognition | – |
| 10 | 0 | Bm7 | mapping | Bm7@3/4 |
| 11 | 0 | F#m | recognition | – |
| 15 | 0 | F#m7 | recognition | – |
| 17 | 0 | C#m7 | recognition | – |
| 18 | 0 | A/C# | recognition | – |

</details>

<details><summary><b>syn101-scan</b> (chord_only): 14 note/rest differences, 0 missed or wrong chords</summary>

| Bar (ref) | Beat | Expected | Found |
|---|---|---|---|
| 3 | 0 | A5/1/2 | A5/1 |
| 3 | 1/2 | F#5/1/2 | F#5/1 |
| 3 | 2 | F5/3/4 | (missing) |
| 3 | 11/4 | C#5/1/4 | (missing) |
| 6 | 1 | C#5/3/4 | C#5/1/2 |
| 6 | 2 | G#4/3/4 | G#4/1/2 |
| 8 | 0 | D5/3/4 | D5/1/2 |
| 10 | 0 | rest/3/4 | rest/1/2 |
| 10 | 11/4 | (extra) | rest/1/4 |
| 11 | 1/2 | (extra) | C#5/1 |
| 11 | 1 | rest/3/4 | E5/1/4 |
| 11 | 7/4 | E5/1/4 | C#5/1/4 |
| 12 | 0 | D5/3 | D5/2 |
| 18 | 2 | B4/3/4 | B4/1/2 |

</details>

<details><summary><b>syn101-phone</b> (chord_only): 3 note/rest differences, 1 missed or wrong chords</summary>

| Bar (ref) | Beat | Expected | Found |
|---|---|---|---|
| 1 | 11/4 | G#5/1/4 | A5/1/4 |
| 5 | 1 | G5/1/4 | A5/1/4 |
| 16 | 3/4 | G#5/1/4 | A5/1/4 |

| Bar (ref) | Beat | Expected chord | Class | Chords found in that bar |
|---|---|---|---|---|
| 2 | 0 | A/C# | recognition | – |

</details>

<details><summary><b>syn101-musicxml</b> (full_score): 0 note/rest differences, 0 missed or wrong chords</summary>

</details>

<details><summary><b>syn102-clean</b> (full_score): 0 note/rest differences, 0 missed or wrong chords</summary>

</details>

<details><summary><b>syn102-ordinary</b> (full_score): 4 note/rest differences, 2 missed or wrong chords</summary>

| Bar (ref) | Beat | Expected | Found |
|---|---|---|---|
| 6 | 3/4 | E4/1/4 | E4/1 |
| 6 | 2 | A3/1/2 | A3/1/4 |
| 7 | 1/2 | (extra) | A3/1/4 |
| 18 | 2 | D4/1/4 | C#4/1/4 |

| Bar (ref) | Beat | Expected chord | Class | Chords found in that bar |
|---|---|---|---|---|
| 2 | 0 | F#m7 | recognition | – |
| 4 | 0 | D/F# | recognition | – |

</details>

<details><summary><b>syn102-scan</b> (chord_only): 25 note/rest differences, 4 missed or wrong chords</summary>

| Bar (ref) | Beat | Expected | Found |
|---|---|---|---|
| 2 | 1 | A4/3/4 | (missing) |
| 2 | 7/4 | A4/1/4 | A4/3/2 |
| 2 | 2 | B4/1/4 | (missing) |
| 2 | 9/4 | A4/1/2 | G5/1/2 |
| 3 | 0 | G#4/1/4 | G5/1/2 |
| 3 | 1 | C#5/3/4 | C#5/1/2 |
| 6 | 0 | rest/3/4 | rest/1/2 |
| 6 | 3/4 | E4/1/4 | rest/3 |
| 6 | 1 | C#4/1/4 | E4/1 |
| 6 | 5/4 | C#4/1/4 | C#4/1/2 |
| 6 | 3/2 | A3/1/2 | C#4/1/2 |
| 6 | 5/2 | B3/1/2 | A3/1/2 |
| 8 | 0 | G4/3/2 | rest/1/2 |
| 8 | 3/2 | rest/1/2 | G4/1 |
| 12 | 1 | C#5/3/4 | C#5/1/2 |
| 12 | 2 | A4/3/4 | A4/1/2 |
| 13 | 0 | B4/3/4 | B4/1/2 |
| 15 | 1/4 | D5/1/4 | D5/1 |
| 15 | 1/2 | B4/1/4 | B4/1 |
| 15 | 2 | D5/1/2 | (missing) |
| 15 | 5/2 | rest/1/2 | (missing) |
| 16 | 2 | rest/3/4 | (missing) |
| 17 | 2 | D5/3/4 | D5/1/2 |
| 17 | 11/4 | F#5/1/4 | F#5/1/2 |
| 19 | 2 | rest/1/2 | (missing) |

| Bar (ref) | Beat | Expected chord | Class | Chords found in that bar |
|---|---|---|---|---|
| 6 | 0 | F#m7 | mapping | – |
| 7 | 0 | G | mapping | F#m7@0, G@7/2 |
| 12 | 0 | Asus4 | recognition | – |
| 14 | 0 | A7 | recognition | – |

</details>

<details><summary><b>syn102-phone</b> (chord_only): 9 note/rest differences, 1 missed or wrong chords</summary>

| Bar (ref) | Beat | Expected | Found |
|---|---|---|---|
| 4 | 7/4 | rest/1/4 | A4/1 |
| 4 | 2 | G4/1/4 | A4/1/4 |
| 4 | 9/4 | F#4/1/2 | (missing) |
| 4 | 11/4 | E4/1/4 | G4/1/4 |
| 5 | 0 | G4/1/4 | A4/3/4 |
| 6 | 3/4 | E4/1/4 | E4/1 |
| 6 | 2 | A3/1/2 | A3/1/4 |
| 7 | 1/2 | (extra) | A3/1/4 |
| 18 | 2 | D4/1/4 | C#4/1/4 |

| Bar (ref) | Beat | Expected chord | Class | Chords found in that bar |
|---|---|---|---|---|
| 20 | 0 | A7 | recognition | – |

</details>

<details><summary><b>syn102-musicxml</b> (full_score): 0 note/rest differences, 0 missed or wrong chords</summary>

</details>

<details><summary><b>syn103-clean</b> (full_score): 6 note/rest differences, 4 missed or wrong chords</summary>

| Bar (ref) | Beat | Expected | Found |
|---|---|---|---|
| 5 | 1/2 | rest/1/4 | (missing) |
| 5 | 3/4 | rest/1/4 | (missing) |
| 5 | 2 | B-4/1 | (missing) |
| 5 | 3 | C5/1/4 | (missing) |
| 5 | 13/4 | B-4/1/2 | (missing) |
| 5 | 15/4 | A-4/1/4 | (missing) |

| Bar (ref) | Beat | Expected chord | Class | Chords found in that bar |
|---|---|---|---|---|
| 4 | 2 | Ab/Eb | mapping | Bb@0, Ab/Eb@3 |
| 5 | 2 | Cm | mapping | Cm@0, Cm@5/4 |
| 8 | 2 | Bbsus4 | recognition | Eb/G@0 |
| 12 | 2 | Gm7 | mapping | Cm@0, Gm7@1 |

</details>

<details><summary><b>syn103-ordinary</b> (full_score): 1 note/rest differences, 3 missed or wrong chords</summary>

| Bar (ref) | Beat | Expected | Found |
|---|---|---|---|
| 20 | 0 | G5/3/4 | A-5/3/4 |

| Bar (ref) | Beat | Expected chord | Class | Chords found in that bar |
|---|---|---|---|---|
| 4 | 2 | Ab/Eb | mapping | Bb@0, Ab/Eb@3 |
| 8 | 2 | Bbsus4 | recognition | Eb/G@0 |
| 12 | 2 | Gm7 | mapping | Cm@0, Gm7@1 |

</details>

<details><summary><b>syn103-scan</b> (chord_only): 24 note/rest differences, 4 missed or wrong chords</summary>

| Bar (ref) | Beat | Expected | Found |
|---|---|---|---|
| 1 | 2 | E-4/1/2 | E-4/1 |
| 1 | 5/2 | G4/1/2 | (missing) |
| 1 | 3 | F4/1/4 | (missing) |
| 1 | 13/4 | G4/1/2 | G4/1 |
| 1 | 15/4 | F4/1/4 | (missing) |
| 4 | 0 | E-4/3 | E-4/2 |
| 5 | 1/2 | rest/1/4 | (missing) |
| 12 | 0 | G5/1/4 | G5/1 |
| 12 | 1/4 | E-5/1/4 | E-5/1 |
| 12 | 1/2 | rest/1/2 | (missing) |
| 12 | 1 | F5/3 | F5/2 |
| 13 | 1/2 | (extra) | F5/1 |
| 17 | 7/4 | C5/1/4 | C5/1 |
| 17 | 3 | rest/1/2 | (missing) |
| 17 | 7/2 | A-4/1/2 | A-4/1/4 |
| 18 | 1 | (extra) | A-4/1/4 |
| 18 | 7/2 | rest/1/2 | (missing) |
| 21 | 3 | rest/1 | (missing) |
| 24 | 1/2 | (extra) | B-4/1/4 |
| 24 | 1 | (extra) | F4/1 |
| 24 | 2 | (extra) | rest/1 |
| 24 | 3 | (extra) | A-4/1 |
| 24 | 3/4 | F4/1/4 | A-4/1/4 |
| 24 | 1 | A-4/3 | A-4/7/4 |

| Bar (ref) | Beat | Expected chord | Class | Chords found in that bar |
|---|---|---|---|---|
| 4 | 0 | Bb | mapping | Ab/Eb@0 |
| 4 | 2 | Ab/Eb | mapping | Ab/Eb@0 |
| 8 | 2 | Bbsus4 | recognition | Eb/G@0 |
| 14 | 0 | Ab/Eb | recognition | A@0, D/Eb@1/2 |

</details>

<details><summary><b>syn103-phone</b> (chord_only): 18 note/rest differences, 4 missed or wrong chords</summary>

| Bar (ref) | Beat | Expected | Found |
|---|---|---|---|
| 1 | 1 | D4/1/2 | C4/1/2 |
| 2 | 1/2 | D4/1/2 | C4/1/2 |
| 7 | 2 | G-5/1/4 | A-5/1/4 |
| 7 | 3 | G5/1 | A-5/1 |
| 8 | 0 | G5/4 | A-5/4 |
| 9 | 0 | G5/1/2 | A-5/1/2 |
| 9 | 3/4 | G5/1/4 | A-5/1/4 |
| 11 | 2 | G5/1 | A-5/1 |
| 11 | 7/2 | G5/1/2 | A-5/1/2 |
| 12 | 0 | G5/1/4 | A-5/1/4 |
| 13 | 0 | G5/1/2 | A-5/1/2 |
| 13 | 1/2 | G5/1/2 | A-5/1/2 |
| 13 | 1 | G5/1/2 | A-5/1/2 |
| 13 | 2 | G5/1/4 | A-5/1/4 |
| 13 | 9/4 | G5/1/4 | A-5/1/4 |
| 13 | 5/2 | G5/1/4 | A-5/1/4 |
| 15 | 2 | G5/1/4 | A-5/1/4 |
| 19 | 7/2 | G5/1/2 | A-5/1/2 |

| Bar (ref) | Beat | Expected chord | Class | Chords found in that bar |
|---|---|---|---|---|
| 4 | 2 | Ab/Eb | mapping | Bb@0, Ab/Eb@3 |
| 8 | 2 | Bbsus4 | recognition | Eb/G@0 |
| 12 | 2 | Gm7 | recognition | Cm@0 |
| 16 | 0 | Bbsus4 | mapping | Bbsus4@1 |

</details>

<details><summary><b>syn103-musicxml</b> (full_score): 0 note/rest differences, 0 missed or wrong chords</summary>

</details>

<details><summary><b>syn201-clean</b> (chord_only): 9 note/rest differences, 0 missed or wrong chords</summary>

| Bar (ref) | Beat | Expected | Found |
|---|---|---|---|
| 14 | 2 | B4/1/2 | B4/1/3 |
| 14 | 5/2 | C5/1/2 | C5/1/3 |
| 14 | 3 | B4/1/4 | B4/1/6 |
| 14 | 13/4 | B4/1/4 | B4/1/6 |
| 15 | 2 | G4/1/4 | G4/1/6 |
| 15 | 9/4 | G4/1/2 | G4/1/3 |
| 15 | 11/4 | A4/1/4 | A4/1/6 |
| 15 | 3 | B4/1/4 | B4/1/6 |
| 15 | 13/4 | C5/1/4 | C5/1/6 |

</details>

<details><summary><b>syn201-ordinary</b> (full_score): 10 note/rest differences, 2 missed or wrong chords</summary>

| Bar (ref) | Beat | Expected | Found |
|---|---|---|---|
| 1 | 9/4 | rest/1/2 | (missing) |
| 3 | 3 | D4/1/2 | C4/1/2 |
| 7 | 7/2 | D4/1/4 | C4/1/4 |
| 7 | 15/4 | D4/1/4 | C4/1/4 |
| 8 | 0 | D4/4 | C4/4 |
| 9 | 3/4 | D4/1/4 | C4/1/4 |
| 9 | 1 | D4/1/2 | C4/1/2 |
| 19 | 3 | D4/1/2 | C4/1/2 |
| 19 | 7/2 | D4/1/2 | C4/1/2 |
| 20 | 7/2 | D4/1/4 | C4/1/4 |

| Bar (ref) | Beat | Expected chord | Class | Chords found in that bar |
|---|---|---|---|---|
| 11 | 0 | Am7 | recognition | Cmaj7@9/4 |
| 14 | 2 | Am7 | recognition | Dsus4@1/2 |

</details>

<details><summary><b>syn201-scan</b> (chord_only): 29 note/rest differences, 12 missed or wrong chords</summary>

| Bar (ref) | Beat | Expected | Found |
|---|---|---|---|
| 1 | 2 | A4/1/4 | A4/1 |
| 1 | 9/4 | rest/1/2 | (missing) |
| 1 | 11/4 | A#4/1/4 | A#4/1 |
| 1 | 3 | A4/1/4 | (missing) |
| 1 | 13/4 | G4/1/2 | (missing) |
| 1 | 15/4 | E4/1/4 | (missing) |
| 3 | 1 | D4/3/4 | (missing) |
| 3 | 7/4 | D4/1/4 | D4/3/2 |
| 3 | 2 | rest/1/2 | D4/1/2 |
| 4 | 2 | F#4/3/4 | F#4/1/2 |
| 4 | 3 | G4/3/4 | G4/1/2 |
| 6 | 0 | rest/1/2 | (missing) |
| 6 | 5/2 | rest/1/2 | (missing) |
| 6 | 3 | G4/3/4 | G4/1/2 |
| 8 | 0 | D4/4 | (missing) |
| 15 | 0 | C5/3/4 | C5/3/2 |
| 15 | 3/4 | C5/1/4 | C5/1 |
| 15 | 9/4 | G4/1/2 | G4/1/4 |
| 15 | 3 | B4/1/4 | rest/1/4 |
| 15 | 13/4 | C5/1/4 | G4/1/4 |
| 15 | 7/2 | C5/1/2 | (missing) |
| 16 | 0 | rest/1/4 | (missing) |
| 17 | 1 | rest/1/2 | (missing) |
| 18 | 0 | E4/3/4 | E4/1/2 |
| 18 | 1 | D4/1/4 | D4/1 |
| 18 | 7/4 | D4/1/4 | D4/1 |
| 18 | 5/2 | G#4/1/2 | G#4/1/4 |
| 18 | 3 | A4/1 | A4/1/4 |
| 19 | 0 | A4/1/4 | G#4/1/4 |

| Bar (ref) | Beat | Expected chord | Class | Chords found in that bar |
|---|---|---|---|---|
| 2 | 0 | Gadd2 | recognition | – |
| 3 | 0 | Am7 | recognition | – |
| 3 | 2 | Cmaj7 | recognition | – |
| 4 | 2 | Am7 | recognition | Bm7@0 |
| 6 | 0 | Em | recognition | D@3/2 |
| 7 | 0 | Gadd2 | recognition | G@2 |
| 8 | 0 | G/B | recognition | C@2 |
| 9 | 0 | Bm7 | recognition | C@2 |
| 11 | 0 | Am7 | recognition | – |
| 11 | 2 | Cmaj7 | recognition | – |
| 15 | 2 | Bm7 | mapping | Em@0, Bm7@7/2 |
| 20 | 2 | D7 | mapping | D7@0 |

</details>

<details><summary><b>syn201-phone</b> (chord_only): 18 note/rest differences, 2 missed or wrong chords</summary>

| Bar (ref) | Beat | Expected | Found |
|---|---|---|---|
| 1 | 11/4 | A#4/1/4 | A#4/1 |
| 3 | 1 | D4/3/4 | C4/3/4 |
| 3 | 7/4 | D4/1/4 | C4/1/4 |
| 3 | 5/2 | D4/1/2 | C4/1/2 |
| 3 | 3 | D4/1/2 | C4/1/2 |
| 5 | 5/2 | D4/1/4 | C4/1/4 |
| 5 | 11/4 | D4/1/4 | C4/1/4 |
| 5 | 3 | D4/1/4 | C4/1/4 |
| 5 | 7/2 | D4/1/2 | C4/1/2 |
| 7 | 7/2 | D4/1/4 | C4/1/4 |
| 7 | 15/4 | D4/1/4 | C4/1/4 |
| 8 | 0 | D4/4 | C4/4 |
| 18 | 7/4 | D4/1/4 | D4/1 |
| 18 | 3 | A4/1 | A4/1/4 |
| 19 | 1/4 | (extra) | A4/3/4 |
| 19 | 3 | D4/1/2 | C4/1/2 |
| 19 | 7/2 | D4/1/2 | C4/1/2 |
| 20 | 7/2 | D4/1/4 | C4/1/4 |

| Bar (ref) | Beat | Expected chord | Class | Chords found in that bar |
|---|---|---|---|---|
| 3 | 0 | Am7 | recognition | Cmaj7@5/2 |
| 4 | 2 | Am7 | recognition | Bm7@0 |

</details>

<details><summary><b>syn201-musicxml</b> (full_score): 0 note/rest differences, 0 missed or wrong chords</summary>

</details>

<details><summary><b>syn202-clean</b> (full_score): 0 note/rest differences, 3 missed or wrong chords</summary>

| Bar (ref) | Beat | Expected chord | Class | Chords found in that bar |
|---|---|---|---|---|
| 4 | 2 | Cm7 | recognition | F@0 |
| 6 | 2 | Gm7 | recognition | Gm@0 |
| 20 | 2 | Gm7 | recognition | F@0 |

</details>

<details><summary><b>syn202-ordinary</b> (full_score): 9 note/rest differences, 6 missed or wrong chords</summary>

| Bar (ref) | Beat | Expected | Found |
|---|---|---|---|
| 10 | 3 | A-5/1/4 | A-5/1/2 |
| 10 | 13/4 | A-5/1/2 | B-5/1/2 |
| 10 | 15/4 | B-5/1/4 | rest/4 |
| 11 | 4 | (extra) | rest/1/2 |
| 11 | 9/2 | (extra) | rest/2 |
| 19 | 3/4 | G-4/1/4 | G4/1/4 |
| 19 | 1 | G4/1/4 | G-4/1/4 |
| 19 | 3/2 | G4/1/2 | G-4/1/2 |
| 19 | 11/4 | G4/1/4 | G-4/1/4 |

| Bar (ref) | Beat | Expected chord | Class | Chords found in that bar |
|---|---|---|---|---|
| 4 | 2 | Cm7 | recognition | F@0 |
| 6 | 2 | Gm7 | recognition | Gm@0, Gm@2 |
| 10 | 0 | Gm7 | mapping | – |
| 11 | 0 | F7 | mapping | Gm7@0, F7@9/2, Gm7@13/2 |
| 11 | 2 | Gm7 | mapping | Gm7@0, F7@9/2, Gm7@13/2 |
| 20 | 2 | Gm7 | recognition | F@0 |

</details>

<details><summary><b>syn202-scan</b> (chord_only): 23 note/rest differences, 15 missed or wrong chords</summary>

| Bar (ref) | Beat | Expected | Found |
|---|---|---|---|
| 1 | 0 | D5/3/4 | D5/1/2 |
| 6 | 3 | D6/1/4 | D6/1/2 |
| 6 | 7/2 | D6/1/2 | D6/1/4 |
| 7 | 3/4 | C6/1/4 | D6/1/4 |
| 7 | 1 | B-5/1/4 | C6/1/4 |
| 7 | 5/4 | rest/1/2 | B-5/1/2 |
| 7 | 7/4 | B-5/1/4 | B-5/1/2 |
| 10 | 1/4 | (extra) | rest/4 |
| 10 | 2 | A5/1/4 | A5/1 |
| 10 | 9/4 | F5/1/2 | F5/1 |
| 10 | 11/4 | rest/1/4 | (missing) |
| 10 | 3 | A-5/1/4 | (missing) |
| 10 | 13/4 | A-5/1/2 | (missing) |
| 10 | 15/4 | B-5/1/4 | (missing) |
| 12 | 0 | rest/1/2 | (missing) |
| 12 | 1/2 | B-5/1/4 | B-5/1/2 |
| 14 | 0 | rest/3/4 | rest/1/2 |
| 15 | 3/4 | C5/1/4 | C5/1/2 |
| 15 | 7/2 | rest/1/2 | (missing) |
| 16 | 0 | D5/3/2 | D5/1 |
| 16 | 2 | E-5/3/4 | E-5/1/2 |
| 17 | 0 | F5/3/4 | F5/1/2 |
| 17 | 3 | rest/3/4 | (missing) |

| Bar (ref) | Beat | Expected chord | Class | Chords found in that bar |
|---|---|---|---|---|
| 1 | 2 | Eb | mapping | Fsus4@0, Eb@1, Cm7@11/4 |
| 10 | 0 | Gm7 | mapping | – |
| 11 | 0 | F7 | recognition | Gm7@0 |
| 11 | 2 | Gm7 | mapping | Gm7@0 |
| 12 | 0 | Gm | recognition | – |
| 12 | 2 | Bb/D | recognition | – |
| 13 | 2 | Ebmaj7 | recognition | Dm7@0 |
| 14 | 0 | Cm7 | recognition | – |
| 15 | 0 | Eb/Bb | recognition | – |
| 16 | 0 | Eb/Bb | recognition | – |
| 16 | 2 | Bbadd2 | recognition | – |
| 17 | 0 | Gm7 | recognition | – |
| 18 | 0 | Bb | recognition | Gm@2 |
| 20 | 0 | F | recognition | – |
| 20 | 2 | Gm7 | recognition | – |

</details>

<details><summary><b>syn202-phone</b> (chord_only): 20 note/rest differences, 19 missed or wrong chords</summary>

| Bar (ref) | Beat | Expected | Found |
|---|---|---|---|
| 2 | 5/4 | G5/1/2 | A5/1/2 |
| 3 | 1 | G5/1/4 | A5/1/4 |
| 7 | 5/4 | rest/1/2 | (missing) |
| 7 | 7/4 | B-5/1/4 | B-5/1 |
| 7 | 7/2 | G5/1/4 | A5/1/4 |
| 8 | 9/4 | G5/1/4 | A5/1/4 |
| 8 | 3 | G5/1/2 | A5/1/2 |
| 10 | 5/4 | G5/1/2 | A5/1/2 |
| 11 | 13/4 | G5/1/2 | A5/1/2 |
| 13 | 1/4 | G5/1/4 | A5/1/4 |
| 13 | 2 | G5/3/4 | A5/3/4 |
| 14 | 2 | G5/1/2 | A5/1/2 |
| 14 | 13/4 | G5/1/2 | A5/1/2 |
| 16 | 11/4 | G5/1/4 | A5/1/4 |
| 16 | 3 | G5/1/4 | A5/1/4 |
| 17 | 3/2 | G5/1/2 | A5/1/2 |
| 17 | 2 | G5/1/4 | A5/1/4 |
| 17 | 9/4 | G5/1/4 | A5/1/4 |
| 18 | 0 | G5/1/4 | A5/1/4 |
| 18 | 1/4 | G5/1/4 | A5/1/4 |

| Bar (ref) | Beat | Expected chord | Class | Chords found in that bar |
|---|---|---|---|---|
| 1 | 0 | Fsus4 | mapping | Fsus4@3/4, Eb@2 |
| 2 | 2 | Bb/D | mapping | Cm7@1/4 |
| 3 | 2 | F7 | recognition | Bb/D@1/2 |
| 4 | 0 | F | recognition | Cm7@2 |
| 5 | 0 | Fsus4 | recognition | – |
| 5 | 2 | Gm | recognition | – |
| 6 | 0 | Gm | recognition | Gm7@2 |
| 7 | 0 | Bb | recognition | – |
| 8 | 0 | Dm7 | recognition | – |
| 9 | 0 | Bb/D | recognition | – |
| 9 | 2 | Gm | recognition | – |
| 10 | 0 | Gm7 | mapping | – |
| 11 | 0 | F7 | recognition | Gm7@2 |
| 12 | 2 | Bb/D | recognition | Gm@0 |
| 14 | 0 | Cm7 | recognition | – |
| 15 | 0 | Eb/Bb | recognition | – |
| 16 | 0 | Eb/Bb | recognition | – |
| 16 | 2 | Bbadd2 | recognition | – |
| 20 | 2 | Gm7 | recognition | F@0 |

</details>

<details><summary><b>syn202-musicxml</b> (full_score): 0 note/rest differences, 0 missed or wrong chords</summary>

</details>

<details><summary><b>syn203-clean</b> (full_score): 5 note/rest differences, 0 missed or wrong chords</summary>

| Bar (ref) | Beat | Expected | Found |
|---|---|---|---|
| 4 | 1/4 | G4/1/4 | G4/1/6 |
| 4 | 1/2 | G4/1/4 | G4/1/6 |
| 4 | 3/4 | rest/1/4 | rest/1/6 |
| 4 | 1 | B4/1/4 | B4/1/6 |
| 4 | 5/4 | A4/1/2 | A4/1/3 |

</details>

<details><summary><b>syn203-ordinary</b> (chord_only): 17 note/rest differences, 1 missed or wrong chords</summary>

| Bar (ref) | Beat | Expected | Found |
|---|---|---|---|
| 3 | 3 | D4/1/2 | C4/1/2 |
| 7 | 7/2 | D4/1/2 | C4/1/2 |
| 11 | 7/2 | D#4/1/2 | C4/1/2 |
| 15 | 7/4 | G5/1/4 | G5/3/8 |
| 15 | 2 | A5/1 | A5/15/8 |
| 15 | 3 | G5/1/2 | (missing) |
| 15 | 7/2 | G5/1/4 | A#5/1/4 |
| 15 | 15/4 | A5/1/4 | A5/1 |
| 16 | 0 | A#5/1/4 | (missing) |
| 16 | 1 | A5/1/2 | A5/1 |
| 16 | 3/2 | A5/1/2 | A5/1/8 |
| 16 | 2 | B5/2 | (missing) |
| 17 | 0 | B5/1/2 | (missing) |
| 17 | 1/2 | B5/1/2 | B5/1 |
| 18 | 5/2 | G5/1/2 | A5/1/2 |
| 18 | 3 | G5/1/2 | A5/1/2 |
| 18 | 7/2 | G5/1/2 | A5/1/2 |

| Bar (ref) | Beat | Expected chord | Class | Chords found in that bar |
|---|---|---|---|---|
| 16 | 2 | Gadd2 | mapping | Dsus4@0, Gadd2@1 |

</details>

<details><summary><b>syn203-scan</b> (chord_only): 10 note/rest differences, 1 missed or wrong chords</summary>

| Bar (ref) | Beat | Expected | Found |
|---|---|---|---|
| 3 | 3/2 | rest/1/2 | (missing) |
| 4 | 2 | B4/3/2 | B4/1 |
| 5 | 3 | G4/3/4 | G4/1/2 |
| 10 | 0 | G4/3/4 | G4/1/2 |
| 11 | 3/2 | rest/1/2 | (missing) |
| 13 | 3/4 | D4/1/4 | D4/1 |
| 13 | 3 | G4/1/2 | G4/1/4 |
| 14 | 1/4 | (extra) | G4/1/4 |
| 17 | 0 | B5/1/2 | (missing) |
| 17 | 1/2 | B5/1/2 | B5/1 |

| Bar (ref) | Beat | Expected chord | Class | Chords found in that bar |
|---|---|---|---|---|
| 13 | 2 | Em7 | mapping | C/G@0, Em7@11/4 |

</details>

<details><summary><b>syn203-phone</b> (chord_only): 26 note/rest differences, 1 missed or wrong chords</summary>

| Bar (ref) | Beat | Expected | Found |
|---|---|---|---|
| 2 | 3 | D4/1 | C4/1 |
| 3 | 0 | D4/1/4 | C4/1/4 |
| 3 | 2 | D4/1/4 | C4/1/4 |
| 3 | 9/4 | D4/1/4 | C4/1/4 |
| 3 | 5/2 | D4/1/2 | C4/1/2 |
| 3 | 3 | D4/1/2 | C4/1/2 |
| 6 | 9/4 | D4/1/4 | C4/1/4 |
| 6 | 5/2 | D4/1/2 | C4/1/2 |
| 7 | 0 | D4/1 | C4/1 |
| 7 | 7/2 | D4/1/2 | C4/1/2 |
| 9 | 0 | D4/1/4 | C4/1/4 |
| 10 | 7/2 | D4/1/2 | C4/1/2 |
| 11 | 1/2 | D4/1/2 | C4/1/2 |
| 11 | 1 | D4/1/2 | C4/1/2 |
| 11 | 7/2 | D#4/1/2 | C4/1/2 |
| 12 | 0 | D4/1/2 | C4/1/2 |
| 13 | 1/4 | D4/1/4 | C4/1/4 |
| 15 | 3/2 | G5/1/4 | A5/1/4 |
| 15 | 7/4 | G5/1/4 | A5/1/4 |
| 15 | 3 | G5/1/2 | A5/1/2 |
| 15 | 7/2 | G5/1/4 | A5/1/4 |
| 18 | 3/4 | G5/1/4 | A5/1/4 |
| 18 | 2 | G5/1/4 | A5/1/4 |
| 18 | 5/2 | G5/1/2 | A5/1/2 |
| 18 | 3 | G5/1/2 | A5/1/2 |
| 18 | 7/2 | G5/1/2 | A5/1/2 |

| Bar (ref) | Beat | Expected chord | Class | Chords found in that bar |
|---|---|---|---|---|
| 1 | 2 | Am7 | recognition | G/B@0 |

</details>

<details><summary><b>syn203-musicxml</b> (full_score): 0 note/rest differences, 0 missed or wrong chords</summary>

</details>

<details><summary><b>syn204-clean</b> (full_score): 1 note/rest differences, 0 missed or wrong chords</summary>

| Bar (ref) | Beat | Expected | Found |
|---|---|---|---|
| 19 | 0 | D6/3/4 | D6/1/2 |

</details>

<details><summary><b>syn204-ordinary</b> (chord_only): 10 note/rest differences, 1 missed or wrong chords</summary>

| Bar (ref) | Beat | Expected | Found |
|---|---|---|---|
| 7 | 3 | E-5/1/4 | E-5/1/2 |
| 7 | 15/4 | rest/1/4 | (missing) |
| 11 | 9/4 | E-5/1/4 | E-5/1/2 |
| 11 | 7/2 | rest/1/4 | (missing) |
| 16 | 0 | D5/1 | D5/2/3 |
| 16 | 1 | E-5/1/2 | E-5/1/3 |
| 16 | 3/2 | D5/1/2 | D5/1/3 |
| 16 | 2 | F5/1 | F5/2/3 |
| 19 | 0 | D6/3/4 | D6/1/2 |
| 20 | 7/4 | D6/1/4 | D-6/1/4 |

| Bar (ref) | Beat | Expected chord | Class | Chords found in that bar |
|---|---|---|---|---|
| 16 | 2 | Bbadd2 | mapping | Gm7@0, Bbadd2@4/3 |

</details>

<details><summary><b>syn204-scan</b> (error (preflight:staff_spacing_too_small)): 15 note/rest differences, 26 missed or wrong chords</summary>

| Bar (ref) | Beat | Expected | Found |
|---|---|---|---|
| 4 | 1/2 | rest/1/2 | (missing) |
| 7 | 3 | E-5/1/4 | (missing) |
| 7 | 13/4 | rest/1/2 | E-5/1/2 |
| 8 | 13/4 | C6/1/4 | B-5/1/2 |
| 8 | 7/2 | C6/1/2 | B-5/1/4 |
| 9 | 1/4 | (extra) | B-5/3/4 |
| 10 | 7/2 | rest/1/2 | (missing) |
| 11 | 1 | E-5/3/4 | E-5/1/2 |
| 11 | 9/4 | E-5/1/4 | E-5/1 |
| 11 | 5/2 | G5/1/2 | G5/1 |
| 11 | 3 | A5/1/2 | (missing) |
| 11 | 7/2 | rest/1/4 | (missing) |
| 11 | 15/4 | rest/1/4 | (missing) |
| 15 | 0 | B-4/3/4 | B-4/1/2 |
| 21 | 1/2 | rest/1/2 | (missing) |

| Bar (ref) | Beat | Expected chord | Class | Chords found in that bar |
|---|---|---|---|---|
| 1 | 0 | Eb | recognition | – |
| 1 | 2 | Bb | recognition | – |
| 4 | 2 | Cm7 | recognition | Eb@0 |
| 6 | 0 | Cm7 | recognition | – |
| 6 | 2 | F7 | recognition | – |
| 7 | 0 | Fsus4 | recognition | Dm7@2 |
| 8 | 0 | Cm7 | recognition | – |
| 8 | 2 | Bb/D | recognition | – |
| 9 | 0 | Eb | recognition | – |
| 10 | 0 | Eb | recognition | – |
| 11 | 2 | Cm7 | recognition | Gm@0 |
| 12 | 0 | Ebmaj7 | recognition | – |
| 12 | 2 | Fsus4 | recognition | – |
| 13 | 2 | Ebmaj7 | recognition | Eb@0 |
| 16 | 0 | Gm7 | mapping | Gm7@1 |
| 16 | 2 | Bbadd2 | recognition | Gm7@1 |
| 17 | 0 | Ebmaj7 | recognition | – |
| 17 | 2 | Bb | recognition | – |
| 19 | 0 | Bb/D | recognition | – |
| 19 | 2 | Fsus4 | recognition | – |
| 20 | 0 | F7 | recognition | – |
| 20 | 2 | Eb/Bb | recognition | – |
| 21 | 0 | Gm | recognition | – |
| 22 | 0 | Fsus4 | recognition | – |
| 22 | 2 | Cm7 | recognition | – |
| 23 | 0 | Ebmaj7 | recognition | – |

</details>

<details><summary><b>syn204-phone</b> (chord_only): 16 note/rest differences, 19 missed or wrong chords</summary>

| Bar (ref) | Beat | Expected | Found |
|---|---|---|---|
| 6 | 7/2 | G5/1/4 | A5/1/4 |
| 6 | 15/4 | G5/1/4 | A5/1/4 |
| 7 | 0 | G5/1/4 | A5/1/4 |
| 7 | 3/4 | G5/1/4 | A5/1/4 |
| 7 | 1 | G5/3/4 | A5/3/4 |
| 8 | 0 | G5/1 | A5/1 |
| 9 | 15/4 | G5/1/4 | A5/1/4 |
| 10 | 3 | G5/1/2 | A5/1/2 |
| 11 | 0 | G5/1/2 | A5/1/2 |
| 11 | 9/4 | E-5/1/4 | E-5/1/2 |
| 11 | 5/2 | G5/1/2 | A5/1/2 |
| 11 | 7/2 | rest/1/4 | (missing) |
| 12 | 0 | A5/3/2 | A5/1 |
| 19 | 0 | D6/3/4 | D6/1/2 |
| 24 | 1 | G5/3/2 | A5/3/2 |
| 24 | 15/4 | G5/1/4 | A5/1/4 |

| Bar (ref) | Beat | Expected chord | Class | Chords found in that bar |
|---|---|---|---|---|
| 4 | 2 | Cm7 | recognition | Eb@0 |
| 5 | 0 | Fsus4 | recognition | – |
| 6 | 0 | Cm7 | recognition | – |
| 6 | 2 | F7 | recognition | – |
| 7 | 0 | Fsus4 | recognition | – |
| 7 | 2 | Dm7 | recognition | – |
| 8 | 0 | Cm7 | recognition | – |
| 8 | 2 | Bb/D | recognition | – |
| 9 | 0 | Eb | recognition | – |
| 10 | 0 | Eb | recognition | – |
| 11 | 2 | Cm7 | mapping | Gm@0, Cm7@11/4 |
| 12 | 0 | Ebmaj7 | mapping | Ebmaj7@1, Fsus4@2 |
| 13 | 2 | Ebmaj7 | mapping | Eb@0, Ebmaj7@3 |
| 17 | 0 | Ebmaj7 | mapping | Bb@2 |
| 19 | 0 | Bb/D | recognition | Fsus4@7/4 |
| 22 | 0 | Fsus4 | recognition | – |
| 22 | 2 | Cm7 | recognition | – |
| 23 | 0 | Ebmaj7 | recognition | – |
| 24 | 0 | Bb | recognition | – |

</details>

<details><summary><b>syn204-musicxml</b> (full_score): 0 note/rest differences, 0 missed or wrong chords</summary>

</details>

<details><summary><b>syn205-clean</b> (chord_only): 14 note/rest differences, 2 missed or wrong chords</summary>

| Bar (ref) | Beat | Expected | Found |
|---|---|---|---|
| 15 | 2 | C5/1/4 | C5/1/6 |
| 15 | 9/4 | B-4/1/2 | B-4/1/3 |
| 15 | 11/4 | B-4/1/4 | B-4/1/6 |
| 15 | 3 | G4/1/2 | G4/1/3 |
| 17 | 2 | F4/3/4 | F4/1/2 |
| 17 | 11/4 | A-4/1/4 | A-4/1/6 |
| 17 | 3 | G4/1/2 | G4/1/3 |
| 21 | 0 | C5/1/2 | C5/1/3 |
| 21 | 1/2 | D5/1/2 | D5/1/3 |
| 21 | 1 | B-4/1/2 | B-4/1/3 |
| 21 | 3/2 | B-4/1/2 | B-4/1/3 |
| 21 | 2 | C5/1 | C5/2/3 |
| 21 | 3 | B-4/1/2 | B-4/1/3 |
| 21 | 7/2 | rest/1/2 | rest/1/3 |

| Bar (ref) | Beat | Expected chord | Class | Chords found in that bar |
|---|---|---|---|---|
| 21 | 2 | Bb | mapping | Bbadd2@0, Bb@4/3 |
| 24 | 2 | Gm7 | mapping | Dm7@0, Gm7@3 |

</details>

<details><summary><b>syn205-ordinary</b> (chord_only): 24 note/rest differences, 17 missed or wrong chords</summary>

| Bar (ref) | Beat | Expected | Found |
|---|---|---|---|
| 1 | 3 | G4/1/4 | G4/1 |
| 1 | 13/4 | rest/1/2 | (missing) |
| 1 | 15/4 | F4/1/4 | (missing) |
| 6 | 2 | rest/1 | (missing) |
| 9 | 1/2 | (extra) | rest/4 |
| 9 | 2 | B-5/1/4 | B-5/1/2 |
| 9 | 9/4 | A5/1/4 | A5/1/2 |
| 9 | 5/2 | A5/1/4 | A5/1/2 |
| 9 | 11/4 | A5/1/4 | A5/1/2 |
| 9 | 3 | G5/1 | (missing) |
| 23 | 0 | G4/1/2 | G5/1/2 |
| 23 | 1/2 | B-4/1/4 | B-5/1/4 |
| 23 | 3/4 | C5/1/4 | C6/1/4 |
| 23 | 1 | B-4/1/4 | B-5/1/4 |
| 23 | 3/2 | A4/1/2 | A5/1/2 |
| 23 | 2 | G4/1/4 | G5/1/4 |
| 23 | 9/4 | A4/1/4 | A5/1/4 |
| 23 | 5/2 | A4/1/2 | A5/1/2 |
| 23 | 3 | F4/1/2 | F5/1/2 |
| 23 | 7/2 | G4/1/2 | G5/1/2 |
| 24 | 0 | G4/3 | G5/3 |
| 24 | 3 | B-4/1/4 | B-5/1/4 |
| 24 | 13/4 | C5/1/4 | C6/1/4 |
| 24 | 7/2 | C5/1/2 | C6/1/2 |

| Bar (ref) | Beat | Expected chord | Class | Chords found in that bar |
|---|---|---|---|---|
| 2 | 0 | Eb/Bb | recognition | – |
| 4 | 0 | Cm7 | recognition | – |
| 5 | 0 | Bb | recognition | – |
| 6 | 0 | Eb/Bb | recognition | – |
| 6 | 2 | Dm7 | recognition | – |
| 7 | 0 | F | recognition | – |
| 8 | 0 | Cm7 | recognition | – |
| 9 | 0 | Bb | recognition | – |
| 9 | 2 | F | recognition | – |
| 10 | 0 | Ebmaj7 | recognition | – |
| 10 | 2 | Ebmaj7 | recognition | – |
| 11 | 0 | Bb/D | recognition | – |
| 12 | 0 | Bb/D | recognition | – |
| 17 | 2 | Dm7 | mapping | Gm7@1/4, Dm7@11/4 |
| 21 | 0 | Bbadd2 | recognition | – |
| 21 | 2 | Bb | recognition | – |
| 24 | 2 | Gm7 | recognition | Dm7@0 |

</details>

<details><summary><b>syn205-scan</b> (chord_only): 14 note/rest differences, 7 missed or wrong chords</summary>

| Bar (ref) | Beat | Expected | Found |
|---|---|---|---|
| 1 | 2 | G4/3/4 | G4/1/2 |
| 1 | 3 | G4/1/4 | G4/1 |
| 1 | 13/4 | rest/1/2 | (missing) |
| 2 | 1/2 | (extra) | F4/3/4 |
| 3 | 1/4 | A-4/1/4 | A4/1/4 |
| 3 | 1/2 | A-4/1/2 | A4/1/2 |
| 3 | 3 | B-4/3/4 | B-4/1/2 |
| 7 | 3 | rest/1/2 | (missing) |
| 7 | 15/4 | D6/1/4 | D6/1/2 |
| 14 | 1/2 | rest/1/2 | (missing) |
| 14 | 7/4 | C5/1/4 | C5/1/2 |
| 16 | 1 | F4/3/2 | F4/1 |
| 17 | 2 | F4/3/4 | F4/1/2 |
| 21 | 7/2 | rest/1/2 | (missing) |

| Bar (ref) | Beat | Expected chord | Class | Chords found in that bar |
|---|---|---|---|---|
| 14 | 0 | Ebmaj7 | recognition | Bb/D@2 |
| 15 | 0 | Bb | recognition | Gm@2 |
| 21 | 0 | Bbadd2 | recognition | – |
| 21 | 2 | Bb | recognition | – |
| 22 | 0 | Fsus4 | recognition | – |
| 23 | 0 | F | recognition | Cm7@2 |
| 24 | 2 | Gm7 | recognition | Dm7@0 |

</details>

<details><summary><b>syn205-phone</b> (chord_only): 5 note/rest differences, 9 missed or wrong chords</summary>

| Bar (ref) | Beat | Expected | Found |
|---|---|---|---|
| 1 | 3 | G4/1/4 | G4/1 |
| 1 | 13/4 | rest/1/2 | (missing) |
| 1 | 15/4 | F4/1/4 | (missing) |
| 6 | 2 | rest/1 | (missing) |
| 11 | 11/4 | G5/1/4 | A5/1/4 |

| Bar (ref) | Beat | Expected chord | Class | Chords found in that bar |
|---|---|---|---|---|
| 1 | 2 | Bb | recognition | Ebmaj7@1/2 |
| 3 | 0 | Eb | recognition | – |
| 6 | 0 | Eb/Bb | recognition | – |
| 6 | 2 | Dm7 | recognition | – |
| 8 | 0 | Cm7 | recognition | – |
| 9 | 0 | Bb | recognition | – |
| 9 | 2 | F | recognition | – |
| 21 | 2 | Bb | recognition | Bbadd2@0 |
| 24 | 2 | Gm7 | recognition | Dm7@0 |

</details>

<details><summary><b>syn205-musicxml</b> (full_score): 0 note/rest differences, 0 missed or wrong chords</summary>

</details>

<details><summary><b>syn206-clean</b> (full_score): 0 note/rest differences, 0 missed or wrong chords</summary>

</details>

<details><summary><b>syn206-ordinary</b> (full_score): 6 note/rest differences, 1 missed or wrong chords</summary>

| Bar (ref) | Beat | Expected | Found |
|---|---|---|---|
| 17 | 7/2 | E5/1/2 | (missing) |
| 20 | 7/4 | D4/1/4 | C4/1/4 |
| 20 | 9/4 | D4/1/2 | C4/1/2 |
| 20 | 11/4 | D4/1/4 | C4/1/4 |
| 20 | 3 | D4/1/4 | C4/1/4 |
| 20 | 7/2 | D4/1/2 | C4/1/2 |

| Bar (ref) | Beat | Expected chord | Class | Chords found in that bar |
|---|---|---|---|---|
| 5 | 0 | Am | recognition | C/E@2 |

</details>

<details><summary><b>syn206-scan</b> (chord_only): 40 note/rest differences, 5 missed or wrong chords</summary>

| Bar (ref) | Beat | Expected | Found |
|---|---|---|---|
| 1 | 0 | G4/3/4 | G4/1/2 |
| 1 | 3 | E4/3/4 | E4/1/2 |
| 2 | 1 | (extra) | rest/4 |
| 2 | 2 | C4/1/2 | C4/1 |
| 2 | 5/2 | C4/1/4 | C4/1/2 |
| 2 | 11/4 | C4/1/4 | C4/1/2 |
| 2 | 3 | D4/1 | (missing) |
| 3 | 1 | C4/3/4 | C4/1/2 |
| 3 | 15/4 | (extra) | rest/1/4 |
| 6 | 2 | E4/3/4 | E4/1/2 |
| 8 | 0 | rest/1/2 | (missing) |
| 8 | 1 | A4/3 | A4/2 |
| 10 | 2 | G4/3/4 | G4/1/2 |
| 12 | 1 | C5/3 | C5/2 |
| 13 | 3/4 | B4/1/4 | B4/7/16 |
| 13 | 1 | B4/1/4 | rest/2 |
| 13 | 5/4 | D5/1/2 | rest/1/2 |
| 13 | 7/4 | E5/1/4 | (missing) |
| 13 | 2 | E5/1/4 | (missing) |
| 13 | 9/4 | C5/1/4 | (missing) |
| 13 | 5/2 | B4/1/4 | (missing) |
| 13 | 11/4 | A4/1/4 | (missing) |
| 13 | 3 | A4/1 | rest/1/16 |
| 14 | 1 | rest/3/4 | rest/1/2 |
| 14 | 7/4 | C5/1/4 | C5/1/2 |
| 14 | 3 | C5/3/4 | C5/1 |
| 14 | 15/4 | C5/1/4 | C5/1 |
| 15 | 1/4 | (extra) | C5/1/2 |
| 15 | 3 | E5/3/4 | E5/1/2 |
| 16 | 1 | E5/3/2 | E5/1 |
| 17 | 0 | E5/3/4 | E5/1/2 |
| 17 | 3 | rest/1/2 | (missing) |
| 19 | 1 | A4/1/2 | A4/1 |
| 19 | 3/2 | G4/1/4 | (missing) |
| 19 | 7/4 | E4/1/4 | (missing) |
| 19 | 2 | D4/1/2 | (missing) |
| 19 | 5/2 | C4/1/2 | (missing) |
| 19 | 3 | A3/1/4 | (missing) |
| 19 | 13/4 | C4/1/4 | G5/1 |
| 19 | 7/2 | E4/1/2 | E4/1 |

| Bar (ref) | Beat | Expected chord | Class | Chords found in that bar |
|---|---|---|---|---|
| 3 | 0 | Em7 | mapping | Fmaj7@0, Em7@4 |
| 13 | 0 | C | recognition | – |
| 14 | 0 | Am7 | recognition | – |
| 19 | 0 | C/E | mapping | Cadd2@3 |
| 19 | 2 | Cadd2 | mapping | Cadd2@3 |

</details>

<details><summary><b>syn206-phone</b> (chord_only): 11 note/rest differences, 6 missed or wrong chords</summary>

| Bar (ref) | Beat | Expected | Found |
|---|---|---|---|
| 9 | 3/2 | D4/1/2 | C4/1/2 |
| 9 | 2 | E4/3/4 | E4/1/2 |
| 9 | 11/4 | G4/1/4 | G4/1/6 |
| 9 | 3 | G4/1/4 | G4/1/6 |
| 9 | 13/4 | F4/1/4 | F4/1/6 |
| 20 | 3/4 | D4/1/4 | C4/1/4 |
| 20 | 7/4 | D4/1/4 | C4/1/4 |
| 20 | 9/4 | D4/1/2 | C4/1/2 |
| 20 | 11/4 | D4/1/4 | C4/1/4 |
| 20 | 3 | D4/1/4 | C4/1/4 |
| 20 | 7/2 | D4/1/2 | C4/1/2 |

| Bar (ref) | Beat | Expected chord | Class | Chords found in that bar |
|---|---|---|---|---|
| 5 | 0 | Am | recognition | C/E@2 |
| 6 | 0 | F | recognition | – |
| 7 | 0 | C | recognition | – |
| 13 | 0 | C | recognition | – |
| 14 | 0 | Am7 | recognition | – |
| 17 | 0 | Fmaj7 | mapping | Fmaj7@3/4 |

</details>

<details><summary><b>syn206-musicxml</b> (full_score): 0 note/rest differences, 0 missed or wrong chords</summary>

</details>

<details><summary><b>syn207-clean</b> (full_score): 0 note/rest differences, 0 missed or wrong chords</summary>

</details>

<details><summary><b>syn207-ordinary</b> (full_score): 10 note/rest differences, 1 missed or wrong chords</summary>

| Bar (ref) | Beat | Expected | Found |
|---|---|---|---|
| 5 | 3 | C#5/1/2 | (missing) |
| 5 | 7/2 | C#5/1/2 | (missing) |
| 6 | 0 | D#5/1/2 | (missing) |
| 6 | 1/2 | C#5/1/4 | (missing) |
| 6 | 3/4 | C#5/1/4 | (missing) |
| 6 | 2 | B4/3/4 | (missing) |
| 6 | 11/4 | C#5/1/4 | (missing) |
| 6 | 3 | A4/1/2 | (missing) |
| 6 | 7/2 | A4/1/4 | (missing) |
| 6 | 15/4 | B4/1/4 | (missing) |

| Bar (ref) | Beat | Expected chord | Class | Chords found in that bar |
|---|---|---|---|---|
| 6 | 0 | E | mapping | C#m7@0, Esus4@2, E@7/2 |

</details>

<details><summary><b>syn207-scan</b> (chord_only): 15 note/rest differences, 5 missed or wrong chords</summary>

| Bar (ref) | Beat | Expected | Found |
|---|---|---|---|
| 4 | 3 | D5/3/4 | D5/1/2 |
| 6 | 2 | B4/3/4 | B4/1/2 |
| 7 | 0 | G#4/3/4 | G#4/1/2 |
| 7 | 1 | B4/3/4 | B4/1/2 |
| 7 | 2 | rest/1/2 | (missing) |
| 11 | 1 | rest/1 | (missing) |
| 12 | 1 | rest/3 | (missing) |
| 14 | 1 | (extra) | rest/4 |
| 14 | 5 | (extra) | C#6/1/4 |
| 14 | 1 | A5/1/2 | A5/1 |
| 14 | 3/2 | B5/1/4 | B5/1/2 |
| 14 | 7/4 | A5/1/4 | A5/1/2 |
| 14 | 3 | F#5/1 | (missing) |
| 16 | 0 | rest/1/2 | (missing) |
| 16 | 2 | C#5/3/2 | C#5/1 |

| Bar (ref) | Beat | Expected chord | Class | Chords found in that bar |
|---|---|---|---|---|
| 11 | 0 | A | recognition | D/A@1 |
| 11 | 2 | D/A | mapping | D/A@1 |
| 13 | 2 | A | recognition | D@0 |
| 14 | 0 | F#m7 | recognition | – |
| 14 | 2 | A | recognition | – |

</details>

<details><summary><b>syn207-phone</b> (chord_only): 13 note/rest differences, 13 missed or wrong chords</summary>

| Bar (ref) | Beat | Expected | Found |
|---|---|---|---|
| 1 | 2 | G#5/1 | A5/1 |
| 1 | 3 | G#5/1/2 | A5/1/2 |
| 1 | 15/4 | G#5/1/4 | A5/1/4 |
| 2 | 5/2 | G#5/1/2 | A5/1/2 |
| 2 | 13/4 | G#5/1/2 | A5/1/2 |
| 7 | 2 | rest/1/2 | (missing) |
| 8 | 0 | G#5/1/2 | A5/1/2 |
| 8 | 2 | G#5/1/4 | A5/1/4 |
| 8 | 9/4 | G#5/1/2 | A5/1/2 |
| 8 | 11/4 | G#5/1/4 | A5/1/4 |
| 11 | 1/2 | G#5/1/2 | A5/1/2 |
| 11 | 5/2 | G#5/1/2 | A5/1/2 |
| 14 | 5/2 | rest/1/4 | (missing) |

| Bar (ref) | Beat | Expected chord | Class | Chords found in that bar |
|---|---|---|---|---|
| 1 | 0 | A | recognition | – |
| 1 | 2 | A/C# | recognition | – |
| 4 | 2 | A/C# | recognition | Aadd2@0 |
| 5 | 0 | C#m7 | recognition | Esus4@2 |
| 7 | 0 | F#m | recognition | – |
| 8 | 0 | D/A | recognition | – |
| 8 | 2 | A | recognition | – |
| 9 | 0 | Dmaj7 | mapping | – |
| 11 | 0 | A | recognition | – |
| 11 | 2 | D/A | recognition | – |
| 13 | 2 | A | recognition | D@0 |
| 14 | 0 | F#m7 | recognition | – |
| 14 | 2 | A | recognition | – |

</details>

<details><summary><b>syn207-musicxml</b> (full_score): 0 note/rest differences, 0 missed or wrong chords</summary>

</details>

<details><summary><b>syn208-clean</b> (chord_only): 15 note/rest differences, 0 missed or wrong chords</summary>

| Bar (ref) | Beat | Expected | Found |
|---|---|---|---|
| 1 | 1/2 | F#4/1/2 | F#4/1/3 |
| 1 | 1 | E4/1/2 | E4/1/3 |
| 1 | 3/2 | C#4/1/4 | C#4/1/6 |
| 1 | 7/4 | B3/1/4 | B3/1/6 |
| 6 | 1 | D#4/1/4 | D#4/1/6 |
| 6 | 5/4 | E4/1/4 | E4/1/6 |
| 6 | 3/2 | E4/1/4 | E4/1/6 |
| 6 | 7/4 | E4/1/4 | E4/1/6 |
| 6 | 2 | E4/1/2 | E4/1/3 |
| 7 | 1 | G#4/1/4 | G#4/1/6 |
| 7 | 5/4 | F#4/1/4 | F#4/1/6 |
| 7 | 3/2 | D#4/1/2 | D#4/1/3 |
| 7 | 2 | D#4/1/2 | D#4/1/3 |
| 7 | 5/2 | D#4/1/4 | D#4/1/6 |
| 7 | 11/4 | E4/1/4 | E4/1/6 |

</details>

<details><summary><b>syn208-ordinary</b> (full_score): 7 note/rest differences, 3 missed or wrong chords</summary>

| Bar (ref) | Beat | Expected | Found |
|---|---|---|---|
| 4 | 3/2 | D#4/1/2 | C#4/1/2 |
| 8 | 1 | D#4/1/2 | C#4/1/2 |
| 8 | 3/2 | D#4/1/2 | C#4/1/2 |
| 9 | 5/4 | D#4/1/2 | C#4/1/2 |
| 9 | 7/4 | D#4/1/4 | C#4/1/4 |
| 10 | 3/4 | D#4/1/4 | C#4/1/4 |
| 13 | 11/4 | D#4/1/4 | C#4/1/4 |

| Bar (ref) | Beat | Expected chord | Class | Chords found in that bar |
|---|---|---|---|---|
| 14 | 0 | C#m7 | recognition | – |
| 15 | 0 | Amaj7 | recognition | – |
| 16 | 0 | E | recognition | – |

</details>

<details><summary><b>syn208-scan</b> (chord_only): 15 note/rest differences, 8 missed or wrong chords</summary>

| Bar (ref) | Beat | Expected | Found |
|---|---|---|---|
| 2 | 5/2 | rest/1/2 | (missing) |
| 4 | 0 | E4/3/2 | E4/1 |
| 6 | 2 | E4/1/2 | E4/1 |
| 6 | 5/2 | G#4/1/2 | (missing) |
| 8 | 0 | E4/1/4 | E4/1 |
| 8 | 1/4 | C#4/1/4 | B4/1 |
| 8 | 2 | B3/1/2 | (missing) |
| 8 | 5/2 | C#4/1/2 | (missing) |
| 13 | 1 | G#4/3/4 | G#4/1/2 |
| 14 | 0 | C#4/3/4 | C#4/1/2 |
| 14 | 1 | E4/1/4 | E4/1 |
| 14 | 3/2 | E4/1/4 | E4/1 |
| 14 | 7/4 | C#4/1/4 | (missing) |
| 14 | 2 | C#4/1/2 | (missing) |
| 14 | 5/2 | B3/1/2 | (missing) |

| Bar (ref) | Beat | Expected chord | Class | Chords found in that bar |
|---|---|---|---|---|
| 2 | 0 | E/G# | recognition | – |
| 4 | 0 | F#m7 | recognition | – |
| 6 | 0 | Bsus4 | mapping | Bsus4@1 |
| 10 | 0 | A/E | recognition | – |
| 11 | 0 | C#m | recognition | – |
| 13 | 0 | C#m | recognition | – |
| 14 | 0 | C#m7 | recognition | – |
| 15 | 0 | Amaj7 | recognition | – |

</details>

<details><summary><b>syn208-phone</b> (chord_only): 25 note/rest differences, 0 missed or wrong chords</summary>

| Bar (ref) | Beat | Expected | Found |
|---|---|---|---|
| 1 | 1/2 | F#4/1/2 | F#4/1/3 |
| 1 | 1 | E4/1/2 | E4/1/3 |
| 1 | 3/2 | C#4/1/4 | C#4/1/6 |
| 1 | 7/4 | B3/1/4 | B3/1/6 |
| 3 | 5/4 | D#4/1/2 | C#4/1/2 |
| 3 | 2 | rest/1/4 | (missing) |
| 4 | 3/2 | D#4/1/2 | C#4/1/2 |
| 5 | 5/2 | D#4/1/2 | C#4/1/2 |
| 6 | 0 | D#4/1 | C#4/1 |
| 6 | 1 | D#4/1/4 | C#4/1/4 |
| 7 | 1 | G#4/1/4 | G#4/1/6 |
| 7 | 5/4 | F#4/1/4 | F#4/1/6 |
| 7 | 3/2 | D#4/1/2 | D#4/1/3 |
| 7 | 2 | D#4/1/2 | D#4/1/3 |
| 7 | 5/2 | D#4/1/4 | C#4/1/6 |
| 7 | 11/4 | E4/1/4 | E4/1/6 |
| 8 | 1 | D#4/1/2 | C#4/1/2 |
| 8 | 3/2 | D#4/1/2 | C#4/1/2 |
| 9 | 5/4 | D#4/1/2 | C#4/1/2 |
| 9 | 7/4 | D#4/1/4 | C#4/1/4 |
| 10 | 3/4 | D#4/1/4 | C#4/1/4 |
| 13 | 11/4 | D#4/1/4 | C#4/1/4 |
| 14 | 1 | E4/1/4 | E4/1 |
| 14 | 2 | C#4/1/2 | C#4/1/4 |
| 15 | 1 | (extra) | C#4/1/4 |

</details>

<details><summary><b>syn208-musicxml</b> (full_score): 0 note/rest differences, 0 missed or wrong chords</summary>

</details>

