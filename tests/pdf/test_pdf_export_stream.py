"""Streaming export: budget checked before every append, iterator lifetime, page counts.

Independent of the exporter: a tracking buffer records every write against the
cap, generators record their own closure, and weakrefs count live pages.
"""
import io
import os
import socket
import subprocess
import sys
import types
import weakref

import pytest
from PIL import Image

from backend.pdf import core
from backend.pdf.core import PageInfo, PdfError


class _CapBuffer(io.BytesIO):
    """BytesIO that records any write that would take it past ``cap``."""
    cap = None
    overruns: list = []

    def write(self, data):
        if self.cap is not None and self.tell() + len(data) > self.cap:
            type(self).overruns.append((self.tell(), len(data), self.cap))
        return super().write(data)


@pytest.fixture
def capped(monkeypatch):
    _CapBuffer.overruns = []

    def set_cap(cap):
        monkeypatch.setattr(core, "MAX_RESULT_BYTES", cap)
        _CapBuffer.cap = cap
    monkeypatch.setattr(core, "io", types.SimpleNamespace(BytesIO=_CapBuffer))
    yield set_cap
    _CapBuffer.cap = None


def _noise_pages(n, w=300, h=200):
    return [(PageInfo(i, 72.0, 48.0, 0), Image.frombytes("RGB", (w, h), os.urandom(w * h * 3)))
            for i in range(n)]


def test_cap_buffer_detects_a_known_overrun():
    buf = _CapBuffer()
    _CapBuffer.overruns, _CapBuffer.cap = [], 10
    buf.write(b"x" * 11)
    assert _CapBuffer.overruns == [(0, 11, 10)]
    _CapBuffer.cap = None


def test_budget_guard_fires_on_known_overlimit(capped):
    pages = _noise_pages(2)
    full = len(core.export_raster_pdf(pages))  # cap not yet set
    capped(full // 2)
    with pytest.raises(PdfError) as info:
        core.export_raster_pdf(pages)
    assert info.value.code == "pdf_result_too_large"


def test_output_never_grows_past_cap_before_rejection(capped):
    pages = _noise_pages(2)
    full = len(core.export_raster_pdf(pages))
    # Caps just below the final size: compressed data fits, object headers,
    # page tree, xref and trailer do not.
    for cap in (full - 1, full - 50, full - 200, full - 400):
        capped(cap)
        _CapBuffer.overruns = []
        with pytest.raises(PdfError):
            core.export_raster_pdf(pages)
        assert _CapBuffer.overruns == [], f"cap={cap}: writes past cap {_CapBuffer.overruns[:2]}"
    capped(full)
    _CapBuffer.overruns = []
    assert len(core.export_raster_pdf(pages)) == full and _CapBuffer.overruns == []


# --- iterator lifetime ------------------------------------------------------

class _Producer:
    def __init__(self, n, bad_at=None):
        self.n, self.bad_at = n, bad_at
        self.closed = False
        self.yielded = 0
        self.live_at_yield = []
        self._refs = []

    def __iter__(self):
        try:
            for i in range(self.n):
                self.live_at_yield.append(sum(r() is not None for r in self._refs))
                img = Image.new("RGB", (8, 4), (i * 20 % 256, 0, 0))
                self._refs.append(weakref.ref(img))
                w = float("nan") if i == self.bad_at else 16.0
                self.yielded += 1
                yield PageInfo(i, w, 8.0, 0), img
                del img
        finally:
            self.closed = True


def test_generator_ten_pages_ok_and_one_page_live():
    p = _Producer(core.MAX_PAGES)
    gen = iter(p)
    out = core.export_raster_pdf(gen)
    assert out.startswith(b"%PDF-") and p.closed and p.yielded == 10
    assert max(p.live_at_yield) == 0  # earlier pages released before the next is made


@pytest.mark.parametrize("make", [lambda p: iter(p), lambda p: list(p)])
def test_eleven_pages_rejected(make):
    p = _Producer(core.MAX_PAGES + 1)
    with pytest.raises(PdfError) as info:
        core.export_raster_pdf(make(p))
    assert info.value.code == "pdf_bad_page_count" and p.closed


@pytest.mark.parametrize("producer, code", [
    (_Producer(3, bad_at=1), "pdf_bad_page_size"),
    (_Producer(0), "pdf_bad_page_count"),
])
def test_generator_closed_on_error(producer, code):
    with pytest.raises(PdfError) as info:
        core.export_raster_pdf(iter(producer))
    assert info.value.code == code and producer.closed
    assert str(info.value) == code


def test_generator_closed_when_budget_exceeded(capped):
    capped(5_000)
    p = _Producer(core.MAX_PAGES)
    big = (PageInfo(0, 72.0, 48.0, 0), Image.frombytes("RGB", (100, 100), os.urandom(30_000)))

    def gen():
        try:
            yield big
            yield from p
        finally:
            p.closed = True
    g = gen()
    with pytest.raises(PdfError) as info:
        core.export_raster_pdf(g)
    assert info.value.code == "pdf_result_too_large" and p.closed


# --- independent reader (optional second interpreter with pypdf) ------------

_READER = os.environ.get("PDF_INDEPENDENT_PYTHON")
_PYPDF_CHECK = r"""
import io, sys
from pypdf import PdfReader
r = PdfReader(io.BytesIO(sys.stdin.buffer.read()), strict=True)
for p in r.pages:
    im = p.images[0].image.convert("RGB")
    print([float(v) for v in p.mediabox], int(p.get("/Rotate", 0)), im.size, sorted(c for _, c in im.getcolors()))
"""


@pytest.mark.skipif(not _READER, reason="set PDF_INDEPENDENT_PYTHON to an interpreter with pypdf")
def test_independent_pypdf_reads_export_strictly():
    pages = [(PageInfo(0, 100.0, 200.0, 90), Image.new("RGB", (4, 8), (255, 0, 0))),
             (PageInfo(1, 300.5, 50.25, 0), Image.new("RGB", (6, 1), (0, 0, 255)))]
    out = core.export_raster_pdf(pages)
    res = subprocess.run([_READER, "-I", "-c", _PYPDF_CHECK], input=out,
                         capture_output=True, check=True, timeout=60)
    assert res.stderr == b""
    assert res.stdout.decode().splitlines() == [
        "[0.0, 0.0, 100.0, 200.0] 0 (4, 8) [(255, 0, 0)]",
        "[0.0, 0.0, 300.5, 50.25] 0 (6, 1) [(0, 0, 255)]",
    ]


# --- exact pixel guard, both raster paths -----------------------------------

def test_explicit_scale_exact_pixel_boundary():
    at = PageInfo(0, 2000.0, 4000.0, 0)       # 2000 * 4000 = 8,000,000 exactly
    over = PageInfo(0, 2000.0, 4000.01, 0)    # ceil -> 4001 rows
    assert core.raster_scale(at, 1.0) == 1.0
    with pytest.raises(PdfError):
        core.raster_scale(over, 1.0)


@pytest.mark.parametrize("w, h", [(2000.0, 4000.01), (7_000_000.0, 1.01), (3999.5, 2000.5),
                                  (2829.0, 2828.0), (595.0, 842.0)])
def test_default_scale_exact_pixel_bound(w, h):
    import math
    info = PageInfo(0, w, h, 0)
    try:
        s = core.raster_scale(info)
    except PdfError as exc:
        assert exc.code == "pdf_page_too_large"
        return
    assert math.ceil(w * s) * math.ceil(h * s) <= core.MAX_RASTER_PIXELS
    assert core.MIN_SCALE <= s <= core.DEFAULT_SCALE


# --- network blocker known positive -----------------------------------------

def test_network_blocker_catches_known_attempt(no_network):
    s = socket.socket()
    try:
        with pytest.raises(AssertionError):
            s.connect(("127.0.0.1", 9))
    finally:
        s.close()
    assert no_network == [(("127.0.0.1", 9),)]
    no_network.clear()  # this one was deliberate
