# GT-05B native OCR root-cause study

**Decision: NATIVE_ROOT_CAUSE_UNRESOLVED.** The immediate fault is identified in the bundled threaded BLAS path: a null destination write in `libphi_core.so::sgemm_itcopy+232`. Why that worker buffer becomes null is not established. A single-thread predictor control succeeds, but a workaround is not a proven general root cause or production fix.

Branch `experiment/v4-gt05-native-ocr`; worktree `/private/tmp/capomatic-v4-gt05-native`; base **`d35b6f3d7e5258ef48131c52c1b051b2ee507385`**. [Five-case design](V4_GT05_NATIVE_PREREGISTRATION.json) and actual experiment code were committed as **`2e7593121a8dbba7f2447b7f846e9c680b5ee704`** before inference. GT-05A has an independent branch/output and no changes are transferred between tracks.

## Unchanged environment and evidence

Existing image **`sha256:fb3c1ff7f6428a499b18aae5dc0b71a5c8b03ee709b10ab82e3ab1f28e332b1e`**, Linux AArch64, Python 3.12.15, PaddlePaddle **3.2.2**, PaddleOCR **3.7.0**, PaddleX **3.7.2**. Only exact GT-03/04 SHA-bound existing model copies are used; the original caches and failed score/synthetic outputs are preserved. No model/runtime installation, substitution or download.

Every input is the fixed GT-04 **640×160 white RGB synthetic Latin text**; raw array SHA-256 `241ff02b70ddb576ac355c36b1ce6534ae131d4ce7a28c1eceda660aa1f20edb`. No score, reference, lyrics, coordinator answers or V3 runtime callback is mounted. **Bb score OCR calls: 0.** No chord-coverage or musical-accuracy inference follows from these controls.

Processes are serial, network disabled, 2 CPUs, 4 GiB memory cap, 60 s per case, same copied model files and `enable_mkldnn=False`. Default predictor CPU threads are 10; baseline OMP environment is 2. Common observability disables Paddle's SIGSEGV handler and enables Python faulthandler, flushed stage markers and read-only function profiling. These are signal/trace diagnostics, not inference configuration changes. Only the initial recognizer requests a bounded core; other cases have core soft limit zero.

The image has no gdb/lldb/compiler/symbolizer installed. No packages were installed. The host's already available LLDB can load the AArch64 ELF core, so core analysis proceeds offline without rerunning inference or changing the environment.

## Five frozen experiments

| Case | One requested inference change | Exit | Seconds | Result |
| --- | --- | ---: | ---: | --- |
| recognizer-baseline-trace | None | **139** | 8.400 | Python stack and core retained |
| recognizer-omp1 | OMP_NUM_THREADS 2→1 only | **139** | 2.840 | Still crashes in native prediction |
| recognizer-cpu1 | Predictor cpu_threads 10→1 only | **0** | 4.014 | Synthetic recognizer returns |
| recognizer-newir-off | enable_new_ir=False request only | **139** | 2.807 | Still crashes |
| detector-newir-off | Same IR request, relative to GT-04 detector baseline | **139** | 2.294 | Still crashes |

No cases combine thread/backend changes; no parameter search or sixth model experiment follows these outcomes. The successful recognizer returns `B F Gm BbD` on this synthetic input; that is execution evidence, not full OCR correctness or a score chord result. No success is claimed for the detector at cpu_threads=1, because that combination was **not tested**.

Before prediction, measured process high-water RSS was about 477.3 MiB in the baseline log (488,788 KiB); the successful cpu1 case reported 509,168 KiB (about 497.2 MiB) after returning. Failed-process post-crash peak was not captured; do not treat the pre-predict value as the whole run's peak. No case reached its timeout. Core generation contributes to the baseline's elapsed time, so timings are not a fair speed comparison.

The requested constructor/engine options and environment are retained verbatim. Installed source snapshots show configuration propagation, but the generic object-tree probe did not emit a `PaddlePredictorOption` dump. Therefore the IR request's exact effective low-level state is not independently demonstrated; do not claim that every PIR-related hypothesis is ruled out. Source-level defaults and the successful cpu-thread control are evidence, not an exhaustive effective-configuration certificate.

Specifically, installed `paddleocr/_common_args.py` maps `cpu_threads` into the static engine configuration; the CPU branch of `paddlex/.../paddle_static/runner.py` lines 487–489 calls `config.set_cpu_math_library_num_threads(self._config.get("cpu_threads", 10))`. The same source applies the requested IR setting before creating the predictor. This supports the intended single-variable propagation without pretending an absent effective-config dump exists.

## Core and native stack

Python faulthandler localizes the failure to `paddlex/inference/models/runners/paddle_static/runner.py`, line 265, inside native prediction. The retained core's Linux NT_FILE mappings identify the faulting PC inside the same image's `libphi_core.so`, not Python preprocessing.

The first host LLDB load produced addresses but no associated executable images. Exact `libphi_core.so`, libc and Python binary copies were then extracted from the immutable local image solely for symbolization. NT_FILE load addresses were applied with `target modules add/load`. The second LLDB run exits 0 and resolves:

```text
phi::ConvKernelImpl<float, phi::CPUContext>
  -> phi::funcs::Blas<phi::CPUContext>::MatMul<float>
  -> cblas_sgemm
  -> sgemm_thread_nn
  -> exec_blas
  -> sgemm_itcopy + 232
```

Several worker threads are in `sgemm_itcopy`; another is in `sgemm_beta`. At the faulting instruction:

```text
PC  = 0x0000ffff8421f3e8
x22 = 0x0000000000000000
st1 { v0.4s, v1.4s, v2.4s, v3.4s }, [x22]
```

Earlier disassembly moves the destination argument into x22. The source pointer is nonzero. This demonstrates an attempted vector store to a null destination, rather than merely guessing from exit 139 or a generic package warning. It narrows the observed recognizer crash to the threaded SGEMM packing/convolution path in the bundled native library. The core does not explain which allocation, initialization, lifetime or ABI condition supplied the null buffer.

No source-line debug symbols were installed. LLDB uses available symbols from the exact shared library, with unresolved internal frames preserved. Extracted-library SHA-256s, mappings, registers, disassembly, exact debugger commands and logs are retained; missing symbols are not filled in by speculation.

The core's apparent size is **586,838,016 bytes**, with **324,677,632 allocated disk bytes**, and the process core rlimit was 536,870,912 bytes. Apparent sparse-file length differs from allocated storage; both actual sizes are recorded rather than claiming the file is below 512 MiB in logical length. Core and libraries are large local/untracked evidence, never committed.

## What is and is not established

**High confidence:** the baseline recognizer's immediate native crash is a null write in the threaded BLAS path; constructor cpu_threads=1 avoids the failure in one fixed synthetic case. OMP_NUM_THREADS=1 alone does not do so. This distinguishes the predictor thread setting from the OMP environment warning.

**Unresolved:** why the worker buffer is null, whether the detector has exactly the same native fault, whether cpu1 remains successful across repetitions/shapes, and which model/runtime/build issue is responsible. A small tensor operation passing in GT-04 is compatible with a failure specific to a larger threaded convolution path, but does not prove the precise defect. The two IR-request crashes and metadata-compatible package versions do not establish that the native runtime is generally compatible.

Resource exhaustion is not proved or conclusively excluded. The observed instruction/NULL destination and thread-dependent control provide much stronger localization than an OOM guess; full allocation diagnostics would still be needed. No root-cause claim is made from one successful configuration alone, and no production dependency/thread setting is changed.

## Outputs, validation and next step

Untracked `gt05-native-output/` contains five per-case `process.log` files, `results.json` with exact Docker commands/limits/exits, `model-binding.json`, `recognizer-baseline-trace/core`, `core-file-mappings.json`, original and symbolized LLDB transcripts/command manifests, exact native libraries, installed configuration-source snapshots and `root-cause-report.json`.

The final helper rejects unregistered/combined cases; this validation-only change does not alter the five recorded experiments. Configuration tests cover baseline/OMP constructor equality, cpu1 as one extra option, the fixed IR request without a thread combination, unknown-case rejection and absence of any score/production recognition call. Targeted tests and `git diff --check` are recorded in local `validation-summary.json`; no Full Acceptance.

Final targeted GT-01–05B/V4/V3 music/gate tests: **347 passed, 1 skipped** (existing external MuseScore dependency). No test executes a model or Audiveris.

Next recommended native experiment is a **separately frozen, synthetic-only** reproduction of detector and recognizer thread controls with effective native thread configuration captured, followed by source/debug-symbol investigation of the null SGEMM worker buffer. The five-case stop remains honored here. No Bb OCR rerun, runtime/model replacement, production fix or recognition-coverage claim is authorized by these results.

GT-01/02/03/04 artifacts, independent 111-case packet and 14-case pilot remain unchanged and isolated; actual independent human labels remain **0**. No source raster edits, V1/V3 changes, ownership/gate relaxation, full-score renderer, API/frontend/runtime route, merge or deployment.
