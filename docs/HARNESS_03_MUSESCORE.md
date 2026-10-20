# MuseScore dependency and regression readiness

The unchanged V3 test `tests/test_omr_v3_gate.py:190` skips `test_musicxml_fast_path_skips_gate_and_passes_integrity` when neither `mscore3` nor `mscore` is available. The test is an actual MusicXML-to-PDF fast-path/integrity check, not an optional demonstration. No corresponding executable or MuseScore application was found on this Mac.

Production `backend/omr_v3/core.py` already supports a configured `CAPOMATIC_MUSESCORE_BIN` and several executable names and sets `QT_QPA_PLATFORM=offscreen` for tool processes. The existing Dockerfile installs `musescore3`, Poppler and Korean fonts. Neither production code, Dockerfile nor test decorator was modified. Merely adding a fake executable/symlink or changing the skip condition would not establish a functioning renderer and was not done. See [official command-line usage](https://musescore.org/en/handbook/4/command-line-usage).

The regression process returned 652 passed and one existing skip. The Controller's JUnit summary marks this **BLOCKED**, even though pytest returned zero. The exact command, package versions, skipped case and JUnit SHA-256 are recorded under `docs/harness03/`.

## Reproducibility requirements

The retained 0.1 validation dependency directory had drift: Pillow 13.0.0 and pytest 7.4.4 differed from `requirements.txt` pins 12.3.0 and 9.1.1. Its results are separate from the clean-environment attempt. A clean virtual environment was installed successfully with the repository pins, including Pillow 12.3.0 and pytest 9.1.1. `pip check` passed. The selected regressions and harness tests were rerun there. All resolved Python package versions and artifact hashes are captured in [runtime-validation.lock.txt](../harness/runtime-validation.lock.txt) and [dependency evidence](harness03/dependency-lock.json). The prior drifted-environment evidence is retained under `retained-environment-*`. No system or production requirements were changed.

A Python virtual environment is dependency separation, not an OS security boundary, and cannot supply the missing native renderer by itself. Complete readiness needs a reviewed, content-addressed runtime image with compatible MuseScore, Python/dependency wheel hashes, exact font hashes and minimal readonly approved fixtures. Record the actual MuseScore binary/version and image digest; run the unchanged V3/V4 gates with no skips and confirm PDF output starts with `%PDF-`. Do not substitute fonts, edit source fixtures, or regenerate historical notation to make the gate pass.

The Docker daemon is currently unavailable, so no such native dependency image was built or qualified. Existing production Dockerfile tags and unpinned apt transitives alone are not a reproducible image identity. A future build must record resolved artifact digests and versions rather than claiming a moving tag is fixed. The frozen external source/font packet also needs exact hash-checked availability in the isolated verifier; mounting an unrestricted host directory is unacceptable.

The lock is for Python 3.12 on macOS ARM, the observed platform. To recreate the Python package set in a fresh environment on that platform:

```bash
python -m venv .harness-state/validation-venv
.harness-state/validation-venv/bin/python -m pip install --require-hashes -r harness/runtime-validation.lock.txt
.harness-state/validation-venv/bin/python -m pip check
.harness-state/validation-venv/bin/python -m pytest tests/harness -q
```

This fixes Python package identity for the tested subset; it is not a complete native-runtime/image/font lock or an OS isolation qualification. The first installer request timed out in automatic approval review before execution; the one permitted retry completed the local install.
