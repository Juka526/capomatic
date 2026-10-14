"""T5 positive controls for the detectors the other tests/omr files rely on."""
import socket

import pytest

from omr_guard import SENTINEL, leaks


def test_network_guard_fires_on_deliberate_harmless_connection():
    # Loopback, discard port: harmless even if the guard were missing.
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        with pytest.raises(RuntimeError, match="network disabled"):
            s.connect(("127.0.0.1", 9))
    finally:
        s.close()


def test_leak_detector_catches_known_leak_and_passes_clean_error():
    assert leaks(ValueError(f"unknown fields: ['{SENTINEL}']"))
    assert leaks(KeyError(SENTINEL))
    assert not leaks(ValueError("unknown fields"))
