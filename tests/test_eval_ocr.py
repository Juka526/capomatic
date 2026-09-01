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


def test_api_runner_render_check_keeps_detect_timing_separate(monkeypatch, tmp_path):
    image_path = tmp_path / "sheet.png"
    image_path.write_bytes(b"png")

    detect_response = Mock()
    detect_response.json.return_value = {
        "detection_id": "abc",
        "chords": [{"text": "Am"}],
        "meta": {"ocr_engine": "paddle"},
    }
    detect_response.headers = {"access-control-allow-origin": "https://capomatic.vercel.app"}
    render_response = Mock()
    render_response.json.return_value = {"render_ms": 12}
    render_response.headers = {}

    client = Mock()
    client.post.side_effect = [
        detect_response,
        render_response,
        render_response,
        render_response,
        render_response,
        render_response,
        render_response,
    ]
    monkeypatch.setattr(httpx, "Client", Mock(return_value=client))
    ticks = iter([0.0, 1.0, 1.0, 11.0, 11.0, 21.0, 21.0, 31.0, 31.0, 41.0])
    monkeypatch.setattr(eval_ocr.time, "perf_counter", lambda: next(ticks))

    runner = eval_ocr.build_api_runner(
        "https://example.hf.space/",
        "paddle",
        240,
        "https://capomatic.vercel.app",
        render_check=True,
        render_repeats=2,
    )

    assert runner(str(image_path)) == [{"text": "Am"}]
    assert runner.last_meta["detect_wall_ms"] == 1000.0
    assert runner.last_meta["replace_render_median_ms"] == 12.0
    assert runner.last_meta["replace_render_ms_samples"] == [12.0, 12.0]
    assert runner.last_meta["replace_render_wall_ms_samples"] == [10000.0, 10000.0]
    assert runner.last_meta["above_render_wall_median_ms"] == 10000.0
    assert runner.last_meta["above_render_wall_ms_samples"] == [10000.0, 10000.0]


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


def test_evaluate_uses_api_detect_wall_time_when_present(tmp_path, monkeypatch):
    image_path = tmp_path / "sheet.png"
    image_path.write_bytes(b"png")

    def run(_):
        run.last_meta["detect_wall_ms"] = 1234.0
        return [{"text": "Am"}]

    run.last_meta = {}
    ticks = iter([0.0, 99.0])
    monkeypatch.setattr(eval_ocr.time, "perf_counter", lambda: next(ticks))

    result = eval_ocr.evaluate(
        str(image_path),
        {"image": "sheet.png", "expected_unique_chords": ["Am"]},
        run,
    )

    assert result["ocr_time_s"] == 1.234


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
    assert result["sequence_exact"] is False
    assert result["detected_chord_sequence"] == ["Am", "G"]


def test_evaluate_requires_sequence_order_when_present(tmp_path):
    image_path = tmp_path / "sheet.png"
    image_path.write_bytes(b"png")
    label = {
        "image": "sheet.png",
        "expected_unique_chords": ["Am", "G"],
        "expected_chord_sequence": ["Am", "G"],
        "expected_total_chords_min": 2,
        "expected_total_chords_max": 2,
    }

    result = eval_ocr.evaluate(
        str(image_path),
        label,
        lambda _: [{"text": "G"}, {"text": "Am"}],
    )

    assert result["occurrence_exact"] is True
    assert result["sequence_exact"] is False


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
