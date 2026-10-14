# V2-1 approved preparation: first slice report

Owner approval: "모든 작업 승인", 2026-10-14. Production engine implementation remains HOLD until the independent data/baseline gates pass. This is preparation, not a 99% / 2x result.

Implemented: original self-made CI PNG and generator/rights manifest; narrowly approved workflow input replacement and training/data build exclusions; fail-closed data/split/readiness validator; human-label format. The independent tester also replaces the integration suite's refused input reference. No API, home, protected assets, Dockerfile or deployment changes.

CI-only font decision: reuse the independently verified DejaVu 2.35 file already available, with exact hash and Bitstream Vera/public-domain notices. Candidate training fonts remain the separate 2.37 proposal; no silent change to that pin. The diagnostic fixture is CC0 and synthetic, never primary holdout truth.

| Check | Result |
| --- | --- |
| Clean-shell `.venv/bin/python -m pytest tests/ocr_v2 -q -p no:cacheprovider` | 74 passed. NumPy 1.26.4, PaddlePaddle 3.2.2, PaddleOCR 3.7.0, Pillow 12.3.0. |
| Decoder regression | 3 corrupt/opaque/truncated cases fail against pre-fix `1ed5c60`, pass against `02758f6`; valid PNG positive reaches READY in synthetic calibration. |
| Other T2/T5 controls | Missing rights, unsafe paths, split/composer leakage, duplicate bytes, geometry/type/human-role claims, generator pixel drift, minimum counts and socket/network detector each calibrated with known positives. |
| Diagnostic baseline OCR | Cleared self-made CI image only: 12/12 occurrences, zero extras, one local run 6.2 seconds. This is not current production p50 or a held-out accuracy measure. |
| Existing unit suite | 609 passed, 11 skipped before the final decoder fix; not redundantly rerun afterwards. |
| Real readiness CLI | HOLD, exit 2; 0/60 primary holdout pages, no independent frozen human truth. |
| Hosted/production tests | GitHub CI, Docker/Linux/HF cost/latency and authenticated integration: NOT RUN at this report. |

The validator now fully decodes each page before counting it, with the existing 50MP limit checked before allocation. It verifies actual byte hashes, safe data paths, finite ordered image geometry and split isolation. It cannot establish that asserted rights or human independence are true; independent sign-off remains required. No candidate training or serving fallback exists.

Tester: Claude Opus 5.5, final token `c1tstl`; both return markers recovered. Developer: Sonnet 5.5. Final product fix at `02758f6`; tester files are separately committed by the orchestrator. Real WELOVE/local user inputs are excluded from training and formal held-out claims. Unknown/manual title handling is the approved feasibility choice.

Stop: no S2 tuning/training until rights-cleared independent real-recapture truth and the baseline are frozen. Preserve current production. Rollback is an ordinary new commit; no merge, deployment, console changes or history rewrite. Existing privacy/terms remain untouched; policy changes are mapped in the plan.

## CI reproducibility follow-up

GitHub Ubuntu backend run [38552030943](https://github.com/Juka526/capomatic/actions/runs/38552030943) failed two regeneration checks (681 passed, 11 skipped), while the committed PNG hash remained correct. The developer fix `8483f6e` explicitly selects Pillow `Layout.BASIC` for both font sizes; fixture/font/manifest bytes and strict hash/pixel guards are unchanged. The prior default can select RAQM on builds providing it. Actual RAQM availability on that runner is not established, so this remains a cause hypothesis until the Linux rerun.

Independent Opus verification (`c1linuxt`, both markers recovered): clean-shell `tests/ocr_v2` **75 passed**. The new font-selection spy records a deliberately non-BASIC request before checking generator calls; pre-fix generator fails that regression, the fixed version passes. This verifies explicit selection only, not actual RAQM rendering. Local build: Pillow 12.3.0, FreeType 2.14.3, RAQM unavailable. Ubuntu CI is the remaining integration gate; no skipped check or synthetic diagnostic is a production accuracy/speed claim.
