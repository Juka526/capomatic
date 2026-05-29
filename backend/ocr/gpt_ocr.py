"""GPT vision OCR for chord detection.

Returns the same item shape used by the PaddleOCR pipeline:
``{"text": str, "bbox": [x1, y1, x2, y2], "confidence": float}``.
"""
from __future__ import annotations

import base64
import io
import json
import mimetypes
import os
import time
import urllib.error
import urllib.request
from typing import Any

from PIL import Image

from backend.chords.normalize import normalize_chord_text
from backend.ocr.filter import is_chord_candidate

_OPENAI_URL = "https://api.openai.com/v1/chat/completions"
_MODEL = os.environ.get("OPENAI_OCR_MODEL", "gpt-5.4-mini")
_MAX_SIDE = os.environ.get("OPENAI_OCR_MAX_SIDE")
MAX_SIDE = int(_MAX_SIDE) if _MAX_SIDE else None
_PROMPT = (
    "List every chord symbol in this sheet music image. For each, return text "
    "and position as percentage of image width/height (x_pct, y_pct, w_pct, h_pct), "
    "plus approximate font style metadata: font_size_pct as percentage of image height, "
    "font_weight ('regular' or 'bold'), italic (true or false), and color ('black', "
    "'dark_gray', 'gray', 'blue', or 'other'). "
    "Exclude lyrics, numbers, and non-chord text. Respond in JSON only: "
    "{chords: [{text, x_pct, y_pct, w_pct, h_pct, font_size_pct, font_weight, italic, color}]}"
)


def _media_type(image_path: str) -> str:
    guessed, _ = mimetypes.guess_type(image_path)
    return guessed or "image/jpeg"


def _extract_json(raw_text: str) -> dict[str, Any]:
    """Parse a JSON object, tolerating fenced responses if the model emits one."""
    text = raw_text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object from OpenAI, got {type(data)}")
    return data


def _pct_to_unit(value: Any) -> float:
    number = float(value)
    if number > 1.0:
        number /= 100.0
    return max(0.0, min(1.0, number))


def _bbox_from_pct(chord: dict[str, Any], width: int, height: int) -> list[int]:
    x = _pct_to_unit(chord["x_pct"])
    y = _pct_to_unit(chord["y_pct"])
    w = _pct_to_unit(chord["w_pct"])
    h = _pct_to_unit(chord["h_pct"])

    x1 = min(width - 1, int(round(x * width)))
    y1 = min(height - 1, int(round(y * height)))
    x2 = int(round(min(1.0, x + w) * width))
    y2 = int(round(min(1.0, y + h) * height))
    return [x1, y1, min(width, max(x1 + 1, x2)), min(height, max(y1 + 1, y2))]


def _style_from_gpt(chord: dict[str, Any], height: int) -> dict:
    style: dict = {}
    try:
        font_size_pct = _pct_to_unit(chord["font_size_pct"])
        font_size = int(round(font_size_pct * height))
        if font_size > 0:
            style["font_size"] = font_size
    except (KeyError, TypeError, ValueError):
        pass

    weight = chord.get("font_weight")
    if isinstance(weight, str) and weight.lower() in {"regular", "bold"}:
        style["font_weight"] = weight.lower()

    italic = chord.get("italic")
    if isinstance(italic, bool):
        style["italic"] = italic

    color = chord.get("color")
    if isinstance(color, str):
        color = color.lower()
        palette = {
            "black": (25, 25, 25),
            "dark_gray": (55, 55, 55),
            "gray": (95, 95, 95),
            "blue": (30, 45, 120),
        }
        if color in palette:
            style["ink"] = palette[color]
            style["color_name"] = color
    return style


def _image_payload(image_path: str) -> tuple[str, str, tuple[int, int]]:
    """Return media type, base64 data, and the size sent to OpenAI."""
    media_type = _media_type(image_path)
    if MAX_SIDE is None:
        with open(image_path, "rb") as f:
            return media_type, base64.b64encode(f.read()).decode("ascii"), (0, 0)

    with Image.open(image_path) as img:
        img = img.convert("RGB")
        width, height = img.size
        scale = min(1.0, MAX_SIDE / max(width, height))
        if scale < 1.0:
            new_size = (max(1, round(width * scale)), max(1, round(height * scale)))
            img = img.resize(new_size, Image.Resampling.LANCZOS)

        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=92, optimize=True)
        return "image/jpeg", base64.b64encode(buf.getvalue()).decode("ascii"), img.size


def _request_openai(image_path: str) -> tuple[str, dict]:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY environment variable is not set")

    media_type, b64_data, sent_size = _image_payload(image_path)
    payload = {
        "model": _MODEL,
        "temperature": 0,
        "response_format": {"type": "json_object"},
        "messages": [{
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": _PROMPT,
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:{media_type};base64,{b64_data}",
                    },
                },
            ],
        }],
    }

    req = urllib.request.Request(
        _OPENAI_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:  # noqa: S310
            response_data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"OpenAI OCR request failed: {exc.code} {detail}") from exc

    try:
        raw_text = response_data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise ValueError(f"Unexpected OpenAI response shape: {response_data}") from exc
    return raw_text, {
        "usage": response_data.get("usage", {}),
        "sent_size": sent_size,
    }


def run_ocr_gpt_vision(image_path: str) -> tuple[list[dict], dict]:
    """Detect chord symbols with GPT vision and convert percent boxes to pixels."""
    t0 = time.perf_counter()
    with Image.open(image_path) as img:
        width, height = img.size

    raw_text, response_meta = _request_openai(image_path)
    data = _extract_json(raw_text)
    chords = data.get("chords")
    if not isinstance(chords, list):
        raise ValueError(f"Expected 'chords' list from OpenAI, got {type(chords)}")

    items: list[dict] = []
    for chord in chords:
        if not isinstance(chord, dict) or not isinstance(chord.get("text"), str):
            continue
        text = normalize_chord_text(chord["text"])
        if not is_chord_candidate(text):
            continue
        try:
            bbox = _bbox_from_pct(chord, width, height)
        except (KeyError, TypeError, ValueError):
            continue
        items.append({
            "text": text,
            "bbox": bbox,
            "confidence": 1.0,
            "style": _style_from_gpt(chord, height),
        })

    elapsed_ms = round((time.perf_counter() - t0) * 1000, 1)
    usage = response_meta["usage"]
    sent_width, sent_height = response_meta["sent_size"]
    if sent_width == 0 or sent_height == 0:
        sent_width, sent_height = width, height
    return items, {
        "ocr_engine": "gpt-vision",
        "model": _MODEL,
        "max_side": MAX_SIDE,
        "image_width": width,
        "image_height": height,
        "sent_image_width": sent_width,
        "sent_image_height": sent_height,
        "predict_ms": elapsed_ms,
        "total_ms": elapsed_ms,
        "input_tokens": usage.get("prompt_tokens"),
        "output_tokens": usage.get("completion_tokens"),
        "total_tokens": usage.get("total_tokens"),
        "ai_used": True,
        "raw_response_text": raw_text,
    }
