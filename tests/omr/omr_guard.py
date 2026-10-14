"""Helpers for tests/omr (not a test module).

Content-free errors: exceptions may reach frontend/backend Sentry, so user
content (lyrics, titles, field names, raw input) must never appear in them.
"""
# Hangul + ASCII so a leak of either script is caught.
SENTINEL = "SNTL_가사_lyric_7f3a"


def leaks(exc: BaseException, needle: str = SENTINEL) -> bool:
    """True when the needle appears anywhere Sentry would serialize the exception."""
    return needle in str(exc) or needle in repr(exc) or any(needle in repr(a) for a in exc.args)
