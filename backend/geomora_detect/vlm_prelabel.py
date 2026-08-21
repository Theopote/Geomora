from __future__ import annotations

import base64
import json
import os
import re
import ssl
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

import cv2
import httpx
import numpy as np

from .image_io import imread_bgr, imwrite_bgr
from .overlays import draw_overlay
from .models import DetectedElement

CLASS_IDS = {"window": 0, "door": 1}

GEMINI_MODEL_CANDIDATES = (
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-flash-latest",
    "gemini-2.0-flash-lite",
)

SYSTEM_PROMPT = """You are a facade opening detector for rectified building elevation photos.
Identify visible window and door openings only.

Rules:
- Image is already fronto-parallel (rectified facade).
- bbox_norm uses [x_min, y_min, x_max, y_max] with values 0.0-1.0 relative to image width/height.
- type must be "window" or "door".
- Box the visible glass/panel area, tight to the opening, not the whole wall bay.
- Do NOT label air conditioners, signs, shadows, reflections, or decorative frames only.
- If no openings are visible, return an empty elements list.

Respond with JSON only:
{
  "elements": [
    {"type": "window", "bbox_norm": [0.1, 0.2, 0.25, 0.5], "confidence": 0.9}
  ],
  "notes": "optional short note"
}"""


@dataclass
class VlmElement:
    type: str
    bbox_norm: list[float]
    confidence: float = 0.5


@dataclass
class VlmPrelabelResult:
    image_path: str
    provider: str
    model: str
    elements: list[VlmElement] = field(default_factory=list)
    notes: str = ""
    raw_response: str = ""
    error: str | None = None

    @property
    def window_count(self) -> int:
        return sum(1 for element in self.elements if element.type == "window")

    @property
    def door_count(self) -> int:
        return sum(1 for element in self.elements if element.type == "door")


class VlmClient(Protocol):
    def detect_openings(self, image_path: Path, *, model: str) -> VlmPrelabelResult: ...


def ssl_verify_enabled() -> bool:
    value = os.environ.get("GEOMORA_SSL_VERIFY", "1").strip().lower()
    return value not in {"0", "false", "no", "off"}


def _is_retryable_request_error(exc: Exception) -> bool:
    message = str(exc).lower()
    retry_tokens = (
        "ssl",
        "eof occurred",
        "connection reset",
        "timed out",
        "timeout",
        "temporary failure",
        "connection aborted",
        "502",
        "503",
        "504",
        "429",
    )
    return any(token in message for token in retry_tokens)


def _post_json_urllib(
    url: str,
    payload: dict[str, Any],
    *,
    headers: dict[str, str] | None = None,
    timeout: float,
) -> dict[str, Any]:
    body = json.dumps(payload).encode("utf-8")
    request_headers = {"Content-Type": "application/json"}
    if headers:
        request_headers.update(headers)
    request = urllib.request.Request(
        url,
        data=body,
        headers=request_headers,
        method="POST",
    )
    if ssl_verify_enabled():
        context = ssl.create_default_context()
    else:
        context = ssl._create_unverified_context()  # noqa: SLF001
    with urllib.request.urlopen(request, timeout=timeout, context=context) as response:
        return json.loads(response.read().decode("utf-8"))


def post_json_with_retries(
    url: str,
    payload: dict[str, Any],
    *,
    headers: dict[str, str] | None = None,
    timeout: float = 120.0,
    attempts: int = 4,
) -> dict[str, Any]:
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            with httpx.Client(
                timeout=timeout,
                http2=False,
                verify=ssl_verify_enabled(),
                trust_env=True,
                follow_redirects=True,
            ) as client:
                response = client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                return response.json()
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            if attempt < attempts and _is_retryable_request_error(exc):
                time.sleep(min(2.0 * attempt, 8.0))
                continue
            break

    if last_error is not None and _is_retryable_request_error(last_error):
        try:
            return _post_json_urllib(url, payload, headers=headers, timeout=timeout)
        except Exception as urllib_exc:  # noqa: BLE001
            raise RuntimeError(f"{last_error}; urllib fallback failed: {urllib_exc}") from urllib_exc

    if last_error is not None:
        raise last_error
    raise RuntimeError("Request failed without an error message")


def encode_image_base64(image_path: Path, *, max_dim: int = 1600, jpeg_quality: int = 88) -> tuple[str, str]:
    bgr = imread_bgr(image_path)
    height, width = bgr.shape[:2]
    longest = max(height, width)
    if longest > max_dim:
        scale = max_dim / float(longest)
        bgr = cv2.resize(
            bgr,
            (int(round(width * scale)), int(round(height * scale))),
            interpolation=cv2.INTER_AREA,
        )
    ok, encoded = cv2.imencode(".jpg", bgr, [int(cv2.IMWRITE_JPEG_QUALITY), jpeg_quality])
    if not ok:
        raise ValueError(f"Unable to encode image: {image_path}")
    mime = "image/jpeg"
    data = base64.b64encode(encoded.tobytes()).decode("ascii")
    return mime, data


def sanitize_error_message(message: str, api_key: str | None = None) -> str:
    redacted = message
    if api_key:
        redacted = redacted.replace(api_key, "***REDACTED***")
    return re.sub(r"key=[^&\s'\"]+", "key=***REDACTED***", redacted)


def gemini_generate_url(model: str) -> str:
    return f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


def gemini_headers(api_key: str) -> dict[str, str]:
    return {
        "Content-Type": "application/json",
        "x-goog-api-key": api_key,
    }


def list_gemini_models(api_key: str, *, timeout: float = 30.0) -> list[str]:
    url = "https://generativelanguage.googleapis.com/v1beta/models"
    with httpx.Client(
        timeout=timeout,
        http2=False,
        verify=ssl_verify_enabled(),
        trust_env=True,
        follow_redirects=True,
    ) as client:
        response = client.get(url, headers=gemini_headers(api_key))
        response.raise_for_status()
        body = response.json()
    models: list[str] = []
    for item in body.get("models", []):
        name = str(item.get("name", ""))
        methods = item.get("supportedGenerationMethods", []) or item.get("supported_generation_methods", [])
        if not name or "generateContent" not in methods:
            continue
        models.append(name.removeprefix("models/"))
    return models


def resolve_gemini_models(requested: str, api_key: str) -> list[str]:
    ordered = [requested, *GEMINI_MODEL_CANDIDATES]
    unique: list[str] = []
    for model in ordered:
        if model and model not in unique:
            unique.append(model)
    try:
        available = set(list_gemini_models(api_key))
    except Exception:
        return unique
    if not available:
        return unique
    preferred = [model for model in unique if model in available]
    return preferred or sorted(available)


def extract_json_payload(text: str) -> dict[str, Any]:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped)
        stripped = re.sub(r"\s*```$", "", stripped)
    return json.loads(stripped)


def clamp_bbox_norm(bbox: list[float]) -> list[float] | None:
    if len(bbox) != 4:
        return None
    x1, y1, x2, y2 = (float(value) for value in bbox)
    x1, x2 = sorted((max(0.0, x1), min(1.0, x2)))
    y1, y2 = sorted((max(0.0, y1), min(1.0, y2)))
    if x2 - x1 < 0.02 or y2 - y1 < 0.02:
        return None
    return [x1, y1, x2, y2]


def parse_elements(payload: dict[str, Any]) -> list[VlmElement]:
    elements: list[VlmElement] = []
    for item in payload.get("elements", []):
        if not isinstance(item, dict):
            continue
        element_type = str(item.get("type", "")).strip().lower()
        if element_type not in CLASS_IDS:
            continue
        bbox = clamp_bbox_norm(list(item.get("bbox_norm", [])))
        if bbox is None:
            continue
        confidence = float(item.get("confidence", 0.5))
        elements.append(
            VlmElement(
                type=element_type,
                bbox_norm=bbox,
                confidence=max(0.0, min(1.0, confidence)),
            )
        )
    return elements


def bbox_norm_to_yolo_line(element_type: str, bbox_norm: list[float]) -> str:
    class_id = CLASS_IDS[element_type]
    x1, y1, x2, y2 = bbox_norm
    cx = (x1 + x2) / 2.0
    cy = (y1 + y2) / 2.0
    width = x2 - x1
    height = y2 - y1
    return f"{class_id} {cx:.6f} {cy:.6f} {width:.6f} {height:.6f}"


def elements_to_detected(elements: list[VlmElement]) -> list[DetectedElement]:
    return [
        DetectedElement(
            type=element.type,
            bbox_norm=element.bbox_norm,
            confidence=element.confidence,
        )
        for element in elements
    ]


def write_yolo_label(path: Path, elements: list[VlmElement]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [bbox_norm_to_yolo_line(element.type, element.bbox_norm) for element in elements]
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def write_review_overlay(image_path: Path, elements: list[VlmElement], output_path: Path) -> None:
    bgr = imread_bgr(image_path)
    overlay = draw_overlay(bgr, elements_to_detected(elements))
    imwrite_bgr(output_path, overlay)


class OpenAIVlmClient:
    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = "https://api.openai.com/v1",
        timeout: float = 120.0,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def detect_openings(self, image_path: Path, *, model: str) -> VlmPrelabelResult:
        mime, data = encode_image_base64(image_path)
        payload = {
            "model": model,
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                "Detect all windows and doors on this rectified facade image. "
                                "Return JSON only."
                            ),
                        },
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:{mime};base64,{data}"},
                        },
                    ],
                },
            ],
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        url = f"{self.base_url}/chat/completions"
        try:
            body = post_json_with_retries(url, payload, headers=headers, timeout=self.timeout)
            content = body["choices"][0]["message"]["content"]
            parsed = extract_json_payload(content)
            elements = parse_elements(parsed)
            return VlmPrelabelResult(
                image_path=str(image_path),
                provider="openai",
                model=model,
                elements=elements,
                notes=str(parsed.get("notes", "")),
                raw_response=content,
            )
        except Exception as exc:  # noqa: BLE001 - surface provider errors to CLI
            return VlmPrelabelResult(
                image_path=str(image_path),
                provider="openai",
                model=model,
                error=sanitize_error_message(str(exc), self.api_key),
            )


class GeminiVlmClient:
    def __init__(
        self,
        api_key: str,
        *,
        timeout: float = 120.0,
    ) -> None:
        self.api_key = api_key
        self.timeout = timeout

    def detect_openings(self, image_path: Path, *, model: str) -> VlmPrelabelResult:
        mime, data = encode_image_base64(image_path, max_dim=1024, jpeg_quality=82)
        payload = {
            "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {
                            "text": (
                                "Detect all windows and doors on this rectified facade image. "
                                "Return JSON only."
                            ),
                        },
                        {"inline_data": {"mime_type": mime, "data": data}},
                    ],
                }
            ],
            "generationConfig": {
                "temperature": 0.1,
                "responseMimeType": "application/json",
            },
        }
        models_to_try = resolve_gemini_models(model, self.api_key)
        last_error: Exception | None = None
        for active_model in models_to_try:
            url = gemini_generate_url(active_model)
            try:
                body = post_json_with_retries(
                    url,
                    payload,
                    headers=gemini_headers(self.api_key),
                    timeout=self.timeout,
                )
                content = body["candidates"][0]["content"]["parts"][0]["text"]
                parsed = extract_json_payload(content)
                elements = parse_elements(parsed)
                notes = str(parsed.get("notes", ""))
                if active_model != model:
                    notes = f"fallback_model={active_model}; {notes}".strip("; ")
                return VlmPrelabelResult(
                    image_path=str(image_path),
                    provider="gemini",
                    model=active_model,
                    elements=elements,
                    notes=notes,
                    raw_response=content,
                )
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                if "404" in str(exc) and active_model != models_to_try[-1]:
                    continue
                break

        return VlmPrelabelResult(
            image_path=str(image_path),
            provider="gemini",
            model=model,
            error=sanitize_error_message(str(last_error or "Gemini request failed"), self.api_key),
        )


def build_client(provider: str, api_key: str | None = None, *, base_url: str | None = None) -> VlmClient:
    normalized = provider.strip().lower()
    if normalized == "openai":
        key = api_key or __import__("os").environ.get("OPENAI_API_KEY")
        if not key:
            raise ValueError("Missing OpenAI API key. Set OPENAI_API_KEY or pass --api-key.")
        return OpenAIVlmClient(key, base_url=base_url or "https://api.openai.com/v1")
    if normalized == "gemini":
        import os

        key = api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if not key:
            raise ValueError("Missing Gemini API key. Set GEMINI_API_KEY or pass --api-key.")
        return GeminiVlmClient(key)
    raise ValueError(f"Unsupported provider: {provider}. Use openai or gemini.")


def default_model(provider: str) -> str:
    if provider == "gemini":
        return "gemini-2.5-flash"
    return "gpt-4o-mini"
