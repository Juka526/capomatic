"""One isolated PaddleOCR invocation for full-score chord assistance."""
import json
import sys
from pathlib import Path
import numpy as np

from backend.ocr.paddle_ocr import run_ocr_paddle
from backend.ocr.filter import filter_candidates_with_recovery


def json_scalar(value):
    if isinstance(value, np.generic):
        return value.item()
    raise TypeError(f'Unsupported OCR value: {type(value).__name__}')

if __name__ == '__main__':
    raw, meta = run_ocr_paddle(sys.argv[1], read_title=False)
    items, _, _, _ = filter_candidates_with_recovery(raw)
    Path(sys.argv[2]).write_text(json.dumps({'items': items, 'meta': meta},
                                          ensure_ascii=False, default=json_scalar))
