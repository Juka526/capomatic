import json
import sys
from unittest.mock import Mock

import httpx
import pytest

from scripts import eval_ocr


def test_api_runner_posts_fixture_through_detect(monkeypatch, tmp_path):
    image_path = tmp_path / "sheet.png"
    image_path.write_bytes(b"png")
    response = Mock()
    response.json.return_value = {
        "chords": [{"text": "Am", "confidence": 0.9, "bbox": [1, 2, 3, 4]}],
        "meta": {"ocr_engine": "paddle", "predict_ms": 123},
    }
    response.headers = {"access-control-allow-origin": "https://capomatic.vercel.app"}
    client = Mock()
    client.post.return_value = response
    monkeypatch.setattr(httpx, "Client", Mock(return_value=client))

    runner = eval_ocr.build_api_runner(
        "https://example.hf.space/",
        "paddle",
        240,
        "https://capomatic.vercel.app",
    )

    assert runner(str(image_path))[0]["text"] == "Am"
    assert runner.last_meta["predict_ms"] == 123
    assert runner.last_meta["detection_id"] is None
    assert client.post.call_args.kwargs["data"] == {"ocr_engine": "paddle"}
    response.raise_for_status.assert_called_once()


def test_api_runner_rejects_silent_engine_fallback(monkeypatch, tmp_path):
    image_path = tmp_path / "sheet.png"
    image_path.write_bytes(b"png")
    response = Mock()
    response.json.return_value = {"chords": [], "meta": {"ocr_engine": "paddle-only"}}
    response.headers = {"access-control-allow-origin": "https://capomatic.vercel.app"}
    client = Mock()
    client.post.return_value = response
    monkeypatch.setattr(httpx, "Client", Mock(return_value=client))
    runner = eval_ocr.build_api_runner(
        "https://example.hf.space",
        "paddle-gpt",
        240,
        "https://capomatic.vercel.app",
    )

    try:
        runner(str(image_path))
    except RuntimeError as exc:
        assert "expected 'paddle-gpt-hybrid'" in str(exc)
    else:
        raise AssertionError("silent hybrid fallback should fail the benchmark")


def test_evaluate_enforces_expected_total_range(tmp_path, monkeypatch):
    monkeypatch.setattr(eval_ocr, "IMAGES_DIR", str(tmp_path))
    (tmp_path / "sheet.png").write_bytes(b"png")
    result = eval_ocr.evaluate(
        "sheet.png",
        {
            "expected_unique_chords": ["Am"],
            "expected_total_chords_min": 2,
            "expected_total_chords_max": 3,
        },
        lambda _: [{"text": "Am"}],
    )

    assert result["coverage"] == 1.0
    assert result["unique_precision"] == 1.0
    assert result["total_count_ok"] is False


def test_evaluate_scores_repeated_chord_occurrences(tmp_path):
    image_path = tmp_path / "sheet.png"
    image_path.write_bytes(b"png")
    label = {
        "image": "sheet.png",
        "expected_unique_chords": ["Am", "G"],
        "expected_chord_sequence": ["Am", "Am", "G"],
        "expected_total_chords_min": 3,
        "expected_total_chords_max": 3,
    }

    result = eval_ocr.evaluate(
        str(image_path),
        label,
        lambda _: [{"text": "Am"}, {"text": "G"}],
    )

    assert result["coverage"] == 1.0
    assert result["occurrence_coverage"] == pytest.approx(2 / 3)
    assert result["occurrence_precision"] == 1.0
    assert result["occurrence_exact"] is False
    assert result["detected_chord_sequence"] == ["Am", "G"]


def test_failing_gate_still_writes_report(monkeypatch, tmp_path):
    images_dir = tmp_path / "images"
    labels_dir = tmp_path / "labels"
    images_dir.mkdir()
    labels_dir.mkdir()
    (images_dir / "sheet.png").write_bytes(b"png")
    (labels_dir / "sheet.json").write_text(json.dumps({
        "image": "sheet.png",
        "expected_unique_chords": ["Am"],
        "expected_total_chords_min": 2,
        "expected_total_chords_max": 2,
    }))
    report_path = tmp_path / "report.json"
    monkeypatch.setattr(eval_ocr, "IMAGES_DIR", str(images_dir))
    monkeypatch.setattr(eval_ocr, "LABELS_DIR", str(labels_dir))
    monkeypatch.setattr(eval_ocr, "build_runner", lambda _: lambda __: [{"text": "Am"}])
    monkeypatch.setattr(sys, "argv", [
        "eval_ocr.py",
        "--engine", "stub",
        "--report-json", str(report_path),
    ])

    with pytest.raises(SystemExit, match="1"):
        eval_ocr.main()

    report = json.loads(report_path.read_text())
    assert report["summary"]["passed"] is False
    assert report["summary"]["failure_reasons"] == ["fixture_quality"]
    assert report["results"][0]["image_sha256"]


def test_runner_error_still_writes_report(monkeypatch, tmp_path):
    images_dir = tmp_path / "images"
    labels_dir = tmp_path / "labels"
    images_dir.mkdir()
    labels_dir.mkdir()
    (images_dir / "sheet.png").write_bytes(b"png")
    (labels_dir / "sheet.json").write_text(json.dumps({
        "image": "sheet.png",
        "expected_unique_chords": ["Am"],
    }))
    report_path = tmp_path / "report.json"

    def fail(_):
        raise httpx.RemoteProtocolError("server disconnected")

    monkeypatch.setattr(eval_ocr, "IMAGES_DIR", str(images_dir))
    monkeypatch.setattr(eval_ocr, "LABELS_DIR", str(labels_dir))
    monkeypatch.setattr(eval_ocr, "build_runner", lambda _: fail)
    monkeypatch.setattr(sys, "argv", [
        "eval_ocr.py", "--report-json", str(report_path),
    ])

    with pytest.raises(SystemExit, match="1"):
        eval_ocr.main()

    report = json.loads(report_path.read_text())
    assert report["summary"]["passed"] is False
    assert report["errors"][0]["error"].startswith("RemoteProtocolError:")
