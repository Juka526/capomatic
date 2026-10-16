"""Stage 2 of the reliability gate and the final full-score / chord-only decision.

Adapted from the V3 completion package (``omr_v3_final/decision.py``). The
post-OMR signals are the ones the evaluation showed to track real errors:

* bars whose recognised content does not add up to the time signature
  (the held-out 745 px JPEG had 10 such bars out of 31 and scored 78 % on
  notes; the 300 dpi sheets had none);
* whether Audiveris' measure geometry could be mapped onto the exported
  measures (needed for chord placement and repairs);
* Audiveris' own contextual confidence on note heads;
* a recognised time signature at all.

The policy: never hand back a plausible-looking full score when the page or
the recognition is not trustworthy; fall back to Capomatic's chord-only
transposition and say why. Time is never a reason (30 s/page is a target).
"""
from __future__ import annotations

import os
from dataclasses import asdict, dataclass

from .quality import ProcessingMode, QualityDecision

# Calibrated on the development sheets only; see REPORT.md. Env overrides for tuning.
MAX_BAD_BAR_RATIO = 0.10
MIN_MEAN_HEAD_GRADE = 0.60
MIN_CONFIDENCE = 0.80


@dataclass(frozen=True)
class PostOmrSignals:
    bars: int
    bad_bars: int
    geometry_aligned: bool
    heads: int
    mean_head_grade: float | None
    low_grade_heads: int
    has_time_signature: bool
    notes: int

    @property
    def bad_bar_ratio(self) -> float:
        return self.bad_bars / self.bars if self.bars else 1.0

    @property
    def confidence(self) -> float:
        """0..1 summary used for the decision and shown to the user."""
        if not self.bars or not self.notes:
            return 0.0
        c = 1.0 - min(1.0, 2.0 * self.bad_bar_ratio)
        if self.mean_head_grade is not None:
            c *= min(1.0, self.mean_head_grade / 0.75)
        if not self.geometry_aligned:
            c *= 0.9
        return round(max(0.0, c), 3)

    def to_dict(self) -> dict:
        d = asdict(self)
        d.update(bad_bar_ratio=round(self.bad_bar_ratio, 3), confidence=self.confidence)
        return d


@dataclass(frozen=True)
class FinalDecision:
    mode: ProcessingMode
    reason: str
    preflight_score: float | None
    post_omr_confidence: float | None

    def to_dict(self) -> dict:
        return {'mode': self.mode.value, 'reason': self.reason,
                'preflight_score': self.preflight_score, 'post_omr_confidence': self.post_omr_confidence}


def post_omr_signals(score, geometry, aligned: bool, bad_bars: int) -> PostOmrSignals:
    from music21 import meter, note, stream

    measures = list(score.parts[0].getElementsByClass(stream.Measure)) if score.parts else []
    heads = [h for s in geometry.systems for h in s.heads] if geometry is not None else []
    grades = [h.grade for h in heads]
    return PostOmrSignals(
        bars=len(measures),
        bad_bars=bad_bars,
        geometry_aligned=bool(aligned),
        heads=len(heads),
        mean_head_grade=round(sum(grades) / len(grades), 3) if grades else None,
        low_grade_heads=sum(1 for g in grades if g < 0.5),
        has_time_signature=any(True for _ in score.recurse().getElementsByClass(meter.TimeSignature)),
        notes=sum(1 for _ in score.recurse().getElementsByClass(note.Note)),
    )


def decide(preflight: QualityDecision | None, signals: PostOmrSignals | None) -> FinalDecision:
    """Combine the two stages. Either stage can force chord-only."""
    max_bad = float(os.environ.get('CAPOMATIC_OMR_MAX_BAD_BAR_RATIO', MAX_BAD_BAR_RATIO))
    min_conf = float(os.environ.get('CAPOMATIC_OMR_MIN_CONFIDENCE', MIN_CONFIDENCE))
    pre_score = preflight.score if preflight else None
    conf = signals.confidence if signals else None
    if preflight is not None and preflight.mode is ProcessingMode.CHORD_ONLY:
        return FinalDecision(ProcessingMode.CHORD_ONLY, 'preflight:' + ','.join(preflight.reasons), pre_score, conf)
    if signals is not None:
        if not signals.notes or not signals.bars:
            return FinalDecision(ProcessingMode.CHORD_ONLY, 'omr:no_music_recognised', pre_score, conf)
        if not signals.has_time_signature:
            return FinalDecision(ProcessingMode.CHORD_ONLY, 'omr:no_time_signature', pre_score, conf)
        if signals.bad_bar_ratio > max_bad:
            return FinalDecision(ProcessingMode.CHORD_ONLY, 'omr:too_many_inconsistent_bars', pre_score, conf)
        if signals.mean_head_grade is not None and signals.mean_head_grade < MIN_MEAN_HEAD_GRADE:
            return FinalDecision(ProcessingMode.CHORD_ONLY, 'omr:low_note_confidence', pre_score, conf)
        if conf is not None and conf < min_conf:
            return FinalDecision(ProcessingMode.CHORD_ONLY, 'omr:confidence_below_threshold', pre_score, conf)
    return FinalDecision(ProcessingMode.FULL_SCORE, 'full_score_allowed', pre_score, conf)
