from .stub_ocr import run_ocr_stub
from .filter import filter_candidates, is_chord_candidate
from .quality_gate import evaluate_ocr_quality, GateDecision
from .ai_fallback import ai_detect_chords_rows, flatten_rows_to_items, AIFallbackResult

# paddle_ocr, preprocess, and hybrid_detect are imported on demand to avoid
# requiring PaddlePaddle when running with --engine stub.
