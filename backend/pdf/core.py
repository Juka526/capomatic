"""Bounded PDF structure check, page rasterization and flattened raster export.

Every PDFium native call runs under ``_PDFIUM_LOCK`` (PDFium is not thread-safe,
even across documents). The public functions take and return plain bytes,
dataclasses and PIL images -- no native handle escapes -- so the lock can later
be replaced by a single worker process without changing callers.

Errors carry a fixed ``code`` only: no filenames, parser messages or content.
"""
import io
import math
import threading
import zlib
from collections.abc import Iterable, Sized
from dataclasses import dataclass

import pypdfium2 as pdfium
import pypdfium2.raw as pdfium_c
from PIL import Image

MAX_PDF_BYTES = 20 * 1024 * 1024
MAX_PAGES = 10
MAX_RASTER_PIXELS = 8_000_000
MAX_RESULT_BYTES = 128 * 1024 * 1024
DEFAULT_SCALE = 2.0  # 144 dpi
MIN_SCALE = 0.5

# FPDF_ERR_PASSWORD in PDFium's fpdfview.h.
_ERR_PASSWORD = 4

# ponytail: one process-wide mutex; a worker process if PDF load blocks OCR.
_PDFIUM_LOCK = threading.Lock()


class PdfError(ValueError):
    """Rejected input. ``code`` is the only detail kept."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class PageInfo:
    """Source page identity and geometry.

    ``index`` is the 0-based source order. ``width_pt``/``height_pt`` are the
    displayed size in PDF points (1/72 in) after applying ``rotation``, the
    source /Rotate value (0/90/180/270). A raster of this page is already
    upright, so the exported page has rotation 0 and the same displayed size.
    """

    index: int
    width_pt: float
    height_pt: float
    rotation: int


def _open(data: bytes) -> pdfium.PdfDocument:
    """Caller must hold the lock and close the result."""
    if not data:
        raise PdfError("pdf_empty")
    if len(data) > MAX_PDF_BYTES:
        raise PdfError("pdf_too_large")
    # FPDF_GetLastError is process-global and not reset by a successful load;
    # a failed load of garbage deterministically sets it to "format error".
    try:
        pdfium.PdfDocument(b"x")
    except pdfium.PdfiumError:
        pass
    try:
        doc = pdfium.PdfDocument(data)
    except pdfium.PdfiumError as exc:
        raise PdfError("pdf_encrypted" if exc.err_code == _ERR_PASSWORD else "pdf_corrupt") from None
    try:
        # Policy: reject every encrypted file, incl. owner-password-only ones
        # that open with an empty user password. -1 = no security handler.
        if pdfium_c.FPDF_GetSecurityHandlerRevision(doc) != -1:
            raise PdfError("pdf_encrypted")
        n = len(doc)
        if n == 0:
            raise PdfError("pdf_empty")
        if n > MAX_PAGES:
            raise PdfError("pdf_too_many_pages")
    except BaseException:
        doc.close()
        raise
    return doc


def _page_info(doc: pdfium.PdfDocument, index: int) -> PageInfo:
    page = doc[index]
    try:
        w, h = page.get_size()  # already rotated
        rot = page.get_rotation()
    finally:
        page.close()
    if not (math.isfinite(w) and math.isfinite(h) and w > 0 and h > 0):
        raise PdfError("pdf_bad_page_size")
    return PageInfo(index, w, h, rot)


def inspect_pdf(data: bytes) -> list[PageInfo]:
    """Structural check; returns per-page identity/geometry in source order."""
    with _PDFIUM_LOCK:
        doc = _open(data)
        try:
            try:
                return [_page_info(doc, i) for i in range(len(doc))]
            except pdfium.PdfiumError:
                raise PdfError("pdf_corrupt") from None
        finally:
            doc.close()


def _pixels(info: PageInfo, scale: float) -> float:
    """Pixels PDFium will allocate: it rounds each dimension up."""
    try:
        return math.ceil(info.width_pt * scale) * math.ceil(info.height_pt * scale)
    except (OverflowError, ValueError):
        return math.inf


def raster_scale(info: PageInfo, scale: float | None = None) -> float:
    """Scale for ``info``; the exact ceil(w*s)*ceil(h*s) is checked before any allocation.

    ``None`` -> DEFAULT_SCALE, reduced until it fits MAX_RASTER_PIXELS (rejected
    below MIN_SCALE). An explicit scale over the limit is rejected, not reduced.
    """
    if scale is not None:
        if not (math.isfinite(scale) and scale > 0) or _pixels(info, scale) > MAX_RASTER_PIXELS:
            raise PdfError("pdf_page_too_large")
        return scale
    scale = DEFAULT_SCALE
    while _pixels(info, scale) > MAX_RASTER_PIXELS:
        scale *= 0.97
        if scale < MIN_SCALE:
            raise PdfError("pdf_page_too_large")
    return scale


def rasterize_page(data: bytes, index: int, scale: float | None = None) -> tuple[PageInfo, Image.Image]:
    """Render one page upright as RGB; reopens the document so no handle outlives the call."""
    with _PDFIUM_LOCK:
        doc = _open(data)
        try:
            if not 0 <= index < len(doc):
                raise PdfError("pdf_page_out_of_range")
            info = _page_info(doc, index)
            s = raster_scale(info, scale)
            page = doc[index]
            try:
                bitmap = page.render(scale=s, may_draw_forms=False)
                try:
                    return info, bitmap.to_pil().convert("RGB")
                finally:
                    bitmap.close()
            except pdfium.PdfiumError:
                raise PdfError("pdf_render_failed") from None
            finally:
                page.close()
        finally:
            doc.close()


def export_raster_pdf(pages: Iterable[tuple[PageInfo, Image.Image]]) -> bytes:
    """Write a new PDF of one lossless (Flate, 8-bit RGB) page-sized image per page.

    ``pages`` may be a generator: each page is compressed straight into the
    output and then released, so only one decoded page is live here, and the
    output is refused the moment it passes MAX_RESULT_BYTES (never grown past
    it). The PDF is written directly, so no PDFium handle or lock is involved
    and nothing is copied from the source (no links, actions or files).
    Memory is bounded by the output budget plus one page's raw bytes.
    """
    if isinstance(pages, Sized) and not 0 < len(pages) <= MAX_PAGES:
        raise PdfError("pdf_bad_page_count")
    out = io.BytesIO()
    out.write(b"%PDF-1.4\n")
    offsets: dict[int, int] = {}
    it = iter(pages)
    try:
        n = 0
        for info, img in it:
            n += 1
            if n > MAX_PAGES:
                raise PdfError("pdf_bad_page_count")
            _write_page(out, offsets, n, info, img)
            del img
        if n == 0:
            raise PdfError("pdf_bad_page_count")
    finally:
        close = getattr(it, "close", None)
        if close:
            close()
    kids = " ".join(f"{3 + 3 * i} 0 R" for i in range(n))
    _write_obj(out, offsets, 2, f"<</Type/Pages/Kids[{kids}]/Count {n}>>".encode())
    _write_obj(out, offsets, 1, b"<</Type/Catalog/Pages 2 0 R>>")
    xref = out.tell()
    size = 3 + 3 * n
    out.write(f"xref\n0 {size}\n0000000000 65535 f \n".encode())
    for i in range(1, size):
        out.write(f"{offsets[i]:010d} 00000 n \n".encode())
    out.write(f"trailer<</Size {size}/Root 1 0 R>>\nstartxref\n{xref}\n%%EOF\n".encode())
    _check_budget(out.tell())
    return out.getvalue()


def _check_budget(size: int) -> None:
    if size > MAX_RESULT_BYTES:
        raise PdfError("pdf_result_too_large")


def _num(x: float) -> str:
    return f"{x:.6f}".rstrip("0").rstrip(".")


def _write_obj(out: io.BytesIO, offsets: dict[int, int], num: int, body: bytes) -> None:
    offsets[num] = out.tell()
    out.write(b"%d 0 obj\n%s\nendobj\n" % (num, body))


def _write_page(out: io.BytesIO, offsets: dict[int, int], n: int, info: PageInfo, img: Image.Image) -> None:
    if not (math.isfinite(info.width_pt) and math.isfinite(info.height_pt)
            and info.width_pt > 0 and info.height_pt > 0):
        raise PdfError("pdf_bad_page_size")
    if img.width * img.height > MAX_RASTER_PIXELS:
        raise PdfError("pdf_page_too_large")
    w, h = _num(info.width_pt), _num(info.height_pt)
    page, content, image = 3 * n, 3 * n + 1, 3 * n + 2
    raw = img.convert("RGB").tobytes()
    comp = zlib.compressobj(6)
    chunks, size = [], 0
    for i in range(0, len(raw), 1 << 20):
        c = comp.compress(raw[i:i + (1 << 20)])
        size += len(c)
        chunks.append(c)
        _check_budget(out.tell() + size)  # abort during serialization
    del raw
    chunks.append(comp.flush())
    size += len(chunks[-1])
    _check_budget(out.tell() + size)
    # Page /Rotate stays 0: the raster is already upright.
    _write_obj(out, offsets, page, (
        f"<</Type/Page/Parent 2 0 R/MediaBox[0 0 {w} {h}]/Rotate 0"
        f"/Resources<</XObject<</Im0 {image} 0 R>>>>/Contents {content} 0 R>>").encode())
    cs = f"q {w} 0 0 {h} 0 0 cm /Im0 Do Q".encode()
    _write_obj(out, offsets, content, b"<</Length %d>>\nstream\n%s\nendstream" % (len(cs), cs))
    offsets[image] = out.tell()
    out.write((f"{image} 0 obj\n<</Type/XObject/Subtype/Image/Width {img.width}/Height {img.height}"
               f"/ColorSpace/DeviceRGB/BitsPerComponent 8/Filter/FlateDecode/Length {size}>>\nstream\n").encode())
    for c in chunks:
        out.write(c)
    out.write(b"\nendstream\nendobj\n")
