# GT-04 native OCR investigation

**Verdict: NATIVE_INFERENCE_SIGSEGV_REPRODUCED_ON_SYNTHETIC_INPUT. Exact native cause remains UNKNOWN.** This is not recognition accuracy evidence. Bb score OCR calls in GT-04: **0**. The independent visual prototype continued using frozen Audiveris-only semantics.

Starting commit `4a2e1eddc74f1d67b4598da7325e55cac13c7718`; branch `experiment/v4-gt04-visual-rendering`, worktree `/private/tmp/capomatic-v4-gt04-visual`. [Preregistration](V4_GT04_PREREGISTRATION.json) was committed as `924da25` before probes/rendering. The corrected probe and renderer are committed in `b64107b3a437ea8611c3add342bdd4b900c60c29`. Historical GT-03 exit 139 at 6.37 seconds remains unchanged.

## Environment and provenance

Existing local image: `sha256:fb3c1ff7f6428a499b18aae5dc0b71a5c8b03ee709b10ab82e3ab1f28e332b1e`. Packages: PaddlePaddle **3.2.2**, PaddleOCR **3.7.0**, PaddleX **3.7.2**, Python 3.12.15. No install/download/model substitution. The exact four GT-03 SHA-bound model directories were copied into a new GT-04 cache; original host/GT-03 files remain unchanged. Full hashes and retained repository revisions are in [GT-03 model binding](V4_GT03_CHORD_PATH_PREREGISTRATION.json) and local `initial-input-binding.json`.

The Linux process reports **aarch64**. `libpaddle.so` is ELF64, `e_machine=183` (AArch64), consistent with the execution architecture. `/proc/cpuinfo` reports ARMv8 features including `fp`, `asimd`, `fphp`, `asimdhp`, `asimddp`, atomics and CRC/AES/SHA capabilities. This rules out a simple x86/ARM library mismatch, not every possible unsupported instruction or kernel defect. Observed failures are SIGSEGV, not SIGILL; that alone does not identify an instruction-level root cause.

`ldd libpaddle.so` exits 0 with listed direct dependencies resolved, including `libphi_core`, `libpir`, `libcommon`, glibc and libstdc++. Paddle imports and a CPU matrix operation succeed. `/proc/self/maps` from the tensor control records loaded libraries. These observations do not prove all lazily loaded inference kernels are compatible.

`pip check` returns 0, “No broken requirements found.” PaddleOCR's installed requirement permits PaddleX `>=3.7.0,<3.8.0`; 3.7.2 meets that metadata constraint. Dependency metadata consistency is **not** a runtime compatibility certificate for this particular ARM wheel/model/backend combination.

Each model probe uses a new serial container, 4 GiB limit, 2 CPUs, `OMP_NUM_THREADS=2`, `PADDLE_ENABLE_MKLDNN=0`, network disabled, read-only root/backend/probe, writable `/tmp` and isolated cache. No score, reference or coordinator inventory is mounted. CPU-only Paddle is reported; CUDA support is false. The default image detector remains v6-medium. Image preprocessing/model thresholds were not tuned.

## Synthetic experiment and results

The input is generated inside each process: 640×160 white RGB canvas, fixed black Latin text `Bb  F  Gm7  Bb/D`. It is not a score or an independent musical annotation. Per-stage host deadline is 60 seconds; all stages finished before timeout. Each log flushes markers before initialization and prediction, and Python faulthandler is enabled.

| Process | Exit | Seconds | Evidence |
| --- | ---: | ---: | --- |
| Environment only | 0 | 0.824 | CPU capabilities, limits and package versions recorded |
| Paddle CPU tensor/matmul | 0 | 1.916 | `[[7,10],[15,22]]`; native import and basic computation succeed |
| Detector initialization only | 0 | 3.349 | `detector_initialized` reached with existing v6-medium weights |
| Detector prediction | **139** | 2.403 | Initialization completed; fault after `before_detector_predict`, no result |
| Recognizer prediction | **139** | 2.534 | Initialization completed; fault after `before_recognizer_predict`, no result |
| Pipeline, initial harness | 1 | 1.046 | Diagnostic ImportError: nonexistent `_get_ocr`; not a native failure |
| Pipeline, corrected harness | **139** | 3.639 | Existing `get_ocr` initializes; fault after prediction marker |
| Existing Paddle-only hybrid | **139** | 3.171 | Synthetic-only existing wrapper path faults; no returned items |

The initial pipeline probe used a wrong function name. Its log is retained; only the harness was corrected to the existing public `get_ocr`, with no production/model/parameter change. The separate corrected execution has its own identity and log. No successful stage was rerun to seek better OCR coverage. Metadata-only linker/package evidence was saved separately without inference.

The four native inference logs show a null-address SIGSEGV and Paddle's message that no useful C++ stack was available. Python faulthandler did not recover a useful native backtrace. Matplotlib reports a read-only default config path and successfully falls back to `/tmp`; this warning is recorded, not assumed causal. Paddle also warns about `OMP_NUM_THREADS=2` and potential OpenBLAS limitations. Because tensor computation succeeds and no controlled single-thread/backend experiment was run, this warning is a **hypothesis**, not an established cause.

No process timed out. Exit 139 does not look like the usual SIGKILL/OOM exit, but peak RSS/cgroup OOM counters were not captured, so resource causes are not conclusively excluded. Memory limits are measured configuration; no peak-memory estimate is presented as a measurement.

## Interpretation and stopping point

The crash is reproducible without copyrighted score content, before OCR filtering, V3 chord alignment, merging or transposition. Detector and recognizer initialize independently; each fails on first inference. This materially narrows the failure to the common native inference execution path, while leaving CPU kernel/backend/PIR/runtime interaction unresolved. It does not establish that changing a particular version, thread count or model would fix it.

GT-04 does not repeat Bb score OCR. There is no new assisted chord inventory, coverage improvement, false-positive count or full-integrity result. The historical 24 coordinator source candidates / 7 Audiveris harmonies / 17 omissions remain unchanged. The separately guarded visual experiment uses only the frozen recognized baseline.

A next native experiment should preregister a non-score single-variable control and obtain a native backtrace/core or compatible debug symbols before attempting any score recognition. Resource/thread and inference-backend hypotheses should be separated. Any model/runtime replacement or return to Bb OCR needs a separately justified configuration and source-only preregistration; nothing here changes production dependencies or authorizes a retry in this run.

## Evidence and safety

Local untracked artifacts: `ground-truth-04-output/native/{environment,tensor,detector_init,detector_predict,recognizer_predict,pipeline_predict,hybrid_predict}.log`, `results.json`, `pipeline_predict-harness-fixed.log`, `harness-fix-result.json`, `environment-supplement.json` and exact command manifests. GT-03 original/copy weights and GT-04 copied model hashes are verified after execution. No binaries, model cache, scores or core files are committed.

Targeted tests, source/reference bindings, immutable GT-02 111-case packet and GT-03 14-case pilot checks are recorded in the GT-04 validation summary. There are still **0 actual independent human labels**. No predictions are distributed to blinded readers.

No production V1/V3 behavior, ownership/admission/integrity gates, feature flags or API/frontend routes changed. No source editing, production renderer, merge, deployment or Full Acceptance.
