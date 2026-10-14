"""P1 acceptance: backend/pdf/core.py against hand-built PDFs and golden values.

Truth never comes from the rasterizer under test: inputs are hand-written PDF
bytes (_pdf_bytes.py), expected sizes/colours are written down here, and the
exported PDF is read back with a small independent parser (zlib + regex).
"""
import contextlib
import re
import threading
import time
import zlib

import pypdfium2 as pdfium
import pytest
from PIL import Image

from backend.pdf import core
from backend.pdf.core import PageInfo, PdfError
from _pdf_bytes import build_pdf, fill

RED, BLUE, WHITE = (1, 0, 0), (0, 0, 1), (1, 1, 1)
RED8, BLUE8, WHITE8 = (255, 0, 0), (0, 0, 255), (255, 255, 255)
CODE_RE = re.compile(r"^pdf_[a-z_]+$")


def _left_red_right_blue(w=200, h=100):
    return fill(RED, 0, 0, w / 2, h) + fill(BLUE, w / 2, 0, w / 2, h)


def _colors(img):
    return {c for _, c in img.getcolors(maxcolors=1 << 24)}


def _rejects(code, fn, *args, **kwargs):
    with pytest.raises(PdfError) as info:
        fn(*args, **kwargs)
    assert info.value.code == code
    assert str(info.value) == code and CODE_RE.match(code)
    assert not core._PDFIUM_LOCK.locked()
    return info.value


# --- geometry and pixels ----------------------------------------------------

@pytest.mark.parametrize("rotate, size, probes", [
    # PDF /Rotate turns the page clockwise for display.
    (0,   (200, 100), {(50, 50): RED8, (150, 50): BLUE8}),
    (90,  (100, 200), {(50, 50): RED8, (50, 150): BLUE8}),
    (180, (200, 100), {(50, 50): BLUE8, (150, 50): RED8}),
    (270, (100, 200), {(50, 50): BLUE8, (50, 150): RED8}),
])
def test_rotation_geometry_and_upright_pixels(rotate, size, probes):
    data = build_pdf([{"media": [0, 0, 200, 100], "rotate": rotate,
                       "content": _left_red_right_blue()}])
    [info] = core.inspect_pdf(data)
    assert (info.width_pt, info.height_pt, info.rotation) == (*size, rotate)
    info2, img = core.rasterize_page(data, 0, 1.0)
    assert info2 == info and img.mode == "RGB" and img.size == size
    for xy, rgb in probes.items():
        assert img.getpixel(xy) == rgb


def test_cropbox_defines_visible_page():
    data = build_pdf([{"media": [0, 0, 300, 300], "crop": [100, 100, 200, 200],
                       "content": fill(RED, 0, 0, 300, 300) + fill(BLUE, 100, 100, 100, 100)}])
    info, img = core.rasterize_page(data, 0, 1.0)
    assert (info.width_pt, info.height_pt) == (100, 100) and img.size == (100, 100)
    assert _colors(img) == {BLUE8}


def test_transparent_page_renders_white_and_mixed_sizes_keep_order():
    data = build_pdf([{"media": [0, 0, 50, 80]},
                      {"media": [0, 0, 612, 792], "content": fill(RED, 0, 0, 612, 792)},
                      {"media": [0, 0, 595, 842], "content": fill(BLUE, 0, 0, 595, 842)}])
    infos = core.inspect_pdf(data)
    assert [(i.index, i.width_pt, i.height_pt) for i in infos] == [
        (0, 50, 80), (1, 612, 792), (2, 595, 842)]
    _, blank = core.rasterize_page(data, 0, 1.0)
    assert _colors(blank) == {WHITE8}
    _, a4 = core.rasterize_page(data, 2)  # default 2.0 = 144 dpi
    assert a4.size == (1190, 1684) and a4.getpixel((600, 800)) == BLUE8


@pytest.mark.parametrize("media", [
    [0, 0, 595, 842],
    [0, 0, 7_000_000, 1.01],   # very wide, thin: ceil() on the short side doubles it
    [0, 0, 40_000_000, 0.004],
])
def test_default_raster_never_exceeds_pixel_limit(media):
    data = build_pdf([{"media": media}])
    try:
        _, img = core.rasterize_page(data, 0)
    except PdfError as exc:
        assert exc.code == "pdf_page_too_large"
        return
    assert img.width * img.height <= core.MAX_RASTER_PIXELS


def test_explicit_scale_never_exceeds_pixel_limit():
    data = build_pdf([{"media": [0, 0, 7_000_000, 1.01]}])
    try:
        _, img = core.rasterize_page(data, 0, 1.0)
    except PdfError as exc:
        assert exc.code == "pdf_page_too_large"
        return
    assert img.width * img.height <= core.MAX_RASTER_PIXELS


# --- rejected inputs (each is a known positive for its error path) ----------

def _pages(n):
    return build_pdf([{"media": [0, 0, 100, 100]} for _ in range(n)])


def test_page_count_limits():
    assert len(core.inspect_pdf(_pages(core.MAX_PAGES))) == core.MAX_PAGES
    _rejects("pdf_too_many_pages", core.inspect_pdf, _pages(core.MAX_PAGES + 1))
    # PDFium itself refuses a zero-page tree, so either explicit code is acceptable.
    with pytest.raises(PdfError) as zero:
        core.inspect_pdf(_pages(0))
    assert zero.value.code in {"pdf_empty", "pdf_corrupt"}
    _rejects("pdf_empty", core.inspect_pdf, b"")


def test_byte_limit_boundary():
    base = _pages(1)
    at_limit = base + b" " * (core.MAX_PDF_BYTES - len(base))
    assert len(core.inspect_pdf(at_limit)) == 1
    _rejects("pdf_too_large", core.inspect_pdf, at_limit + b" ")


@pytest.mark.parametrize("data", [
    b"not a pdf at all",
    b"%PDF-1.4\n1 0 obj << /Type /Catalog >> endobj\n%%EOF",
    b"%PDF-1.4\n<< /Encrypt 1 0 R >> garbage\n%%EOF",  # /Encrypt text alone is not encryption
])
def test_malformed_is_corrupt(data):
    _rejects("pdf_corrupt", core.inspect_pdf, data)


def test_user_password_is_encrypted_not_corrupt():
    data = build_pdf([{"media": [0, 0, 100, 100], "content": fill(RED, 0, 0, 100, 100)}],
                     encrypt=(b"user", b"owner"))
    _rejects("pdf_encrypted", core.inspect_pdf, data)
    _rejects("pdf_encrypted", core.rasterize_page, data, 0)


def test_escaped_encrypt_key_is_labelled_encrypted():
    data = build_pdf([{"media": [0, 0, 100, 100]}], encrypt=(b"user", b"owner"),
                     encrypt_key_name=b"/Encr#79pt")
    _rejects("pdf_encrypted", core.inspect_pdf, data)


def test_owner_password_only_pdf_is_rejected():
    data = build_pdf([{"media": [0, 0, 100, 100], "content": fill(RED, 0, 0, 100, 100)}],
                     encrypt=(b"", b"owner"))
    _rejects("pdf_encrypted", core.inspect_pdf, data)


@pytest.mark.parametrize("index", [-1, 2, 99])
def test_page_index_out_of_range(index):
    _rejects("pdf_page_out_of_range", core.rasterize_page, _pages(2), index)


@pytest.mark.parametrize("scale", [0.0, -1.0, float("nan"), float("inf"), 30.0])  # 100 pt * 30 = 9 MP
def test_bad_or_oversized_explicit_scale(scale):
    _rejects("pdf_page_too_large", core.rasterize_page, _pages(1), 0, scale)


def test_page_too_large_for_min_scale():
    _rejects("pdf_page_too_large", core.rasterize_page,
             build_pdf([{"media": [0, 0, 14400, 14400]}]), 0)


def test_errors_carry_no_content():
    sentinel = b"SENTINEL_TITLE_AMAZING_GRACE_Cmaj7"
    data = b"%PDF-1.4\n(" + sentinel + b")\n%%EOF"
    assert sentinel in data  # known positive for the scan below
    exc = _rejects("pdf_corrupt", core.inspect_pdf, data)
    assert exc.__cause__ is None and exc.__suppress_context__
    assert sentinel.decode() not in repr(exc) + str(exc.args)


# --- export ----------------------------------------------------------------

def _objects(pdf: bytes) -> dict[int, bytes]:
    return {int(m.group(1)): m.group(2)
            for m in re.finditer(rb"(\d+) 0 obj\s*(.*?)\s*endobj", pdf, re.S)}


def _stream(body: bytes) -> bytes:
    raw = re.search(rb"stream\r?\n(.*)\r?\nendstream", body, re.S).group(1)
    return zlib.decompress(raw) if b"/FlateDecode" in body else raw


def _read_export(pdf: bytes):
    """Independent reader: page order, MediaBox, Rotate, image size/pixels, matrix."""
    objs = _objects(pdf)
    root = int(re.search(rb"/Root (\d+) 0 R", pdf).group(1))
    tree = int(re.search(rb"/Pages (\d+) 0 R", objs[root]).group(1))
    kids = [int(k) for k in re.findall(rb"(\d+) 0 R", re.search(rb"/Kids\[(.*?)\]", objs[tree]).group(1))]
    pages = []
    for k in kids:
        page = objs[k]
        box = [float(v) for v in re.search(rb"/MediaBox\[([^\]]*)\]", page).group(1).split()]
        rot = int(re.search(rb"/Rotate (\d+)", page).group(1))
        content = _stream(objs[int(re.search(rb"/Contents (\d+) 0 R", page).group(1))])
        xobj = objs[int(re.search(rb"/XObject<</\w+ (\d+) 0 R", page).group(1))]
        w = int(re.search(rb"/Width (\d+)", xobj).group(1))
        h = int(re.search(rb"/Height (\d+)", xobj).group(1))
        img = Image.frombytes("RGB", (w, h), _stream(xobj))
        pages.append((box, rot, content, img))
    return pages


def test_export_geometry_order_and_pixels():
    pages = [(PageInfo(0, 100.0, 200.0, 90), Image.new("RGB", (4, 8), RED8)),
             (PageInfo(1, 300.0, 50.0, 0), Image.new("RGB", (6, 1), BLUE8)),
             (PageInfo(2, 612.0, 792.0, 0), Image.new("RGB", (3, 3), WHITE8))]
    got = _read_export(core.export_raster_pdf(pages))
    assert [g[0] for g in got] == [[0, 0, 100, 200], [0, 0, 300, 50], [0, 0, 612, 792]]
    assert [g[1] for g in got] == [0, 0, 0]
    for (info, src), (_, _, content, img) in zip(pages, got):
        assert img.size == src.size and _colors(img) == _colors(src)
        # image drawn over the whole page: [w 0 0 h 0 0] cm
        m = [float(v) for v in re.search(rb"([-\d. ]+) cm", content).group(1).split()]
        assert m == [info.width_pt, 0, 0, info.height_pt, 0, 0]


ACTIVE = [b"/JavaScript", b"/JS", b"/OpenAction", b"/Annots", b"/URI", b"/AA",
          b"/EmbeddedFile", b"/Launch", b"/AcroForm"]


def test_export_drops_active_content():
    src = build_pdf(
        [{"media": [0, 0, 200, 100], "content": _left_red_right_blue(),
          "extra": b" /Annots [5 0 R] /AA << /O 6 0 R >>"}],
        catalog_extra=b" /OpenAction 6 0 R /Names << /EmbeddedFiles << /Names [(x) 7 0 R] >> >>"
                      b" /AcroForm << /Fields [] >>",
        extra_objects=[
            b"<< /Type /Annot /Subtype /Link /Rect [0 0 50 50] /A << /S /URI /URI (https://example.invalid) >> >>",
            b"<< /S /JavaScript /JS (app.alert(1)) >>",
            b"<< /Type /Filespec /F (x) /EF << /F 3 0 R >> >>",
            b"<< /S /Launch /F (calc) >>",
        ])
    for token in ACTIVE:  # the scanner's known positives
        assert token in src, token
    info, img = core.rasterize_page(src, 0, 1.0)
    out = core.export_raster_pdf([(info, img)])
    for token in ACTIVE:
        assert token not in out, token
    [(box, _, _, back)] = _read_export(out)
    assert box == [0, 0, 200, 100]
    assert back.getpixel((50, 50)) == RED8 and back.getpixel((150, 50)) == BLUE8


def test_export_input_limits():
    ok = (PageInfo(0, 10.0, 10.0, 0), Image.new("RGB", (2, 2)))
    _rejects("pdf_bad_page_count", core.export_raster_pdf, [])
    _rejects("pdf_bad_page_count", core.export_raster_pdf, [ok] * (core.MAX_PAGES + 1))
    _rejects("pdf_bad_page_size", core.export_raster_pdf, [(PageInfo(0, float("nan"), 10.0, 0), ok[1])])
    _rejects("pdf_bad_page_size", core.export_raster_pdf, [(PageInfo(0, 0.0, 10.0, 0), ok[1])])
    big = Image.new("RGB", (4000, 2001))
    _rejects("pdf_page_too_large", core.export_raster_pdf, [(ok[0], big)])


def test_export_result_budget():
    import os
    w, h = 2400, 3333  # just under 8 MP; noise does not deflate
    noise = Image.frombytes("RGB", (w, h), os.urandom(w * h * 3))
    pages = [(PageInfo(i, 595.0, 842.0, 0), noise) for i in range(6)]  # ~144 MB > 128 MiB
    _rejects("pdf_result_too_large", core.export_raster_pdf, pages)


# --- PDFium serialization (T5: the detector must see overlap without the lock) ---

@contextlib.contextmanager
def _overlap_probe(monkeypatch):
    state = {"active": 0, "max": 0}
    guard = threading.Lock()

    def wrap(name):
        original = getattr(pdfium.PdfPage, name)

        def probe(self, *args, **kwargs):
            with guard:
                state["active"] += 1
                state["max"] = max(state["max"], state["active"])
            try:
                time.sleep(0.02)
                return original(self, *args, **kwargs)
            finally:
                with guard:
                    state["active"] -= 1
        monkeypatch.setattr(pdfium.PdfPage, name, probe)

    wrap("render")
    wrap("get_size")
    wrap("gen_content")
    yield state


def _hammer():
    data = build_pdf([{"media": [0, 0, 200, 100], "content": _left_red_right_blue()}] * 2)
    errors = []

    def work(i):
        try:
            if i % 3 == 0:
                core.inspect_pdf(data)
            elif i % 3 == 1:
                core.rasterize_page(data, i % 2, 1.0)
            else:
                core.export_raster_pdf([(PageInfo(0, 20.0, 10.0, 0), Image.new("RGB", (2, 1)))])
        except Exception as exc:  # surfaced below
            errors.append(exc)

    threads = [threading.Thread(target=work, args=(i,)) for i in range(9)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert not errors


def test_overlap_detector_catches_unlocked_calls(monkeypatch):
    monkeypatch.setattr(core, "_PDFIUM_LOCK", contextlib.nullcontext())
    with _overlap_probe(monkeypatch) as state:
        _hammer()
    assert state["max"] > 1


def test_pdfium_calls_never_overlap(monkeypatch):
    with _overlap_probe(monkeypatch) as state:
        _hammer()
    assert state["max"] == 1
    assert not core._PDFIUM_LOCK.locked()
