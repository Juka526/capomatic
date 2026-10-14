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
from dataclasses import dataclass

import pypdfium2 as pdfium
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
    try:
        doc = pdfium.PdfDocument(data)
    except pdfium.PdfiumError as exc:
        # FPDF_GetLastError is process-global and can be stale after a load
        # that sets no error, so also require the /Encrypt trailer key.
        encrypted = exc.err_code == _ERR_PASSWORD and b"/Encrypt" in data
        code = "pdf_encrypted" if encrypted else "pdf_corrupt"
        raise PdfError(code) from None
    try:
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


def raster_scale(info: PageInfo, scale: float | None = None) -> float:
    """Scale for ``info``; checked against the pixel limit before any allocation.

    ``None`` -> DEFAULT_SCALE, reduced to fit MAX_RASTER_PIXELS. An explicit
    scale over the limit is rejected, not silently reduced.
    """
    area = info.width_pt * info.height_pt
    if scale is None:
        scale = min(DEFAULT_SCALE, 0.995 * math.sqrt(MAX_RASTER_PIXELS / area))  # margin: PDFium rounds dims up
        if scale < MIN_SCALE:
            raise PdfError("pdf_page_too_large")
    elif not (math.isfinite(scale) and scale > 0) or area * scale * scale > MAX_RASTER_PIXELS * 0.99:
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


def export_raster_pdf(pages: list[tuple[PageInfo, Image.Image]]) -> bytes:
    """Build a new PDF of one page-sized image per page, in the given order.

    Nothing is copied from the source file, so links, actions, forms and
    embedded files cannot carry over. Page size comes from ``PageInfo``.
    """
    if not 0 < len(pages) <= MAX_PAGES:
        raise PdfError("pdf_bad_page_count")
    for info, img in pages:
        if img.width * img.height > MAX_RASTER_PIXELS:
            raise PdfError("pdf_page_too_large")
        if not (math.isfinite(info.width_pt) and math.isfinite(info.height_pt)
                and info.width_pt > 0 and info.height_pt > 0):
            raise PdfError("pdf_bad_page_size")
    with _PDFIUM_LOCK:
        out = pdfium.PdfDocument.new()
        try:
            for info, img in pages:
                _add_image_page(out, info, img)
            buf = io.BytesIO()
            out.save(buf)
        except pdfium.PdfiumError:
            raise PdfError("pdf_export_failed") from None
        finally:
            out.close()
    if buf.tell() > MAX_RESULT_BYTES:
        raise PdfError("pdf_result_too_large")
    return buf.getvalue()


def _add_image_page(out: pdfium.PdfDocument, info: PageInfo, img: Image.Image) -> None:
    page = out.new_page(info.width_pt, info.height_pt)
    try:
        bitmap = pdfium.PdfBitmap.from_pil(img.convert("RGB"))
        try:
            obj = pdfium.PdfImage.new(out)
            obj.set_bitmap(bitmap)
            obj.set_matrix(pdfium.PdfMatrix().scale(info.width_pt, info.height_pt))
            page.insert_obj(obj)
        finally:
            bitmap.close()
        page.gen_content()
    finally:
        page.close()
