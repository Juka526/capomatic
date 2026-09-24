# Issue #7: admission control, health isolation, and memory

`scripts/load_admission.py` runs the #7 load protocol against any API URL and checks each
acceptance criterion. This file records one **local** run. The release gate requires the same run
against the ready HF canary, which does not exist yet, so #7 is not closed by this evidence.

## Local run

| Item | Value |
| --- | --- |
| Date | 2026-09-24 |
| Code | `220fd18` (the #14 tree) plus this script |
| Host | Darwin arm64 workstation, one `uvicorn` process (not the Docker image, not HF `cpu-basic`) |
| Environment | The Dockerfile `ENV` values (mobile detector, 900000 stitched-pixel limits, resize scale 0.85, inpaint off), pinned `paddleocr 3.7.0` / `paddlepaddle 3.2.2` |
| Image | `fixtures/images/친구야.jpeg`, 966×1288, sha256 prefix `9025cf66ba1d9fab` |
| Command | `python scripts/load_admission.py --api-url http://127.0.0.1:7861 --image "fixtures/images/친구야.jpeg" --pid <uvicorn pid> --evict 21` |

The server was warmed with one `/detect` (200, 11.1 s) before the post-warm memory sample.

### Bursts (3 simultaneous `/detect` each)

| Burst | `/detect` status, seconds, `Retry-After` | Renders (both modes) | `/health` samples, max latency | RSS after |
| --- | --- | --- | --- | --- |
| 1 | 200 15.41 · **429 0.086 `5`** · 200 7.90 | 200 0.21 s, 200 0.18 s | 31, 0.025 s | 660 MB |
| 2 | **429 0.025 `5`** · 200 7.67 · 200 15.75 | 200 0.22 s, 200 0.16 s | 31, 0.031 s | 644 MB |
| 3 | **429 0.019 `5`** · 200 15.22 · 200 7.66 | 200 0.18 s, 200 0.17 s | 31, 0.024 s | 665 MB |

| Criterion | Local result |
| --- | --- |
| At most two detections admitted per burst | PASS: exactly 2 each |
| Excess requests get 429 within 5 s with `Retry-After: 5` | PASS: at most 0.086 s |
| No 5xx within the 240 s client timeout | PASS |
| `/health` within 2 s during OCR load | PASS: at most 0.031 s over 93 samples |
| Every admitted detection renders in Replace and Above | PASS: 6/6 |
| Memory returns near the post-warm baseline after eviction | 612 MB post-warm, 641 MB after 28 detections (+4.8%) |

For cache eviction, the run made 21 more sequential detections, all 200. That makes 28 detections
since warm-up, past the 20-entry cache limit.

## Not verified here

- **HF canary run**: the canary (#4) is not deployed. Run the same command with `--api-url` set to
  the canary and without `--pid`, and record the Space's memory graph against the replica limit.
- Local latencies reflect an arm64 workstation, not `cpu-basic`.
