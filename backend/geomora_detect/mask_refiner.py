from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path

import cv2
import numpy as np

from .models import DetectedElement, DetectionResult
from .overlays import draw_overlay, encode_overlay_jpeg

BACKEND_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG_PATH = BACKEND_ROOT / "models" / "sam_config.json"

INNER_MARGIN = 0.06
MIN_AREA_RATIO = 0.10
MAX_AREA_RATIO = 0.96
MIN_IOU_WITH_PROMPT = 0.35


@lru_cache(maxsize=1)
def _load_config(config_path: str) -> dict:
    with Path(config_path).open(encoding="utf-8") as handle:
        return json.load(handle)


def load_sam_config(config_path: str | None = None) -> dict:
    path = Path(config_path or os.environ.get("GEOMORA_SAM_CONFIG", DEFAULT_CONFIG_PATH))
    if not path.exists():
        return {
            "preferred_backend": "grabcut_v1",
            "grabcut_iterations": 4,
            "inner_margin": INNER_MARGIN,
        }
    return _load_config(str(path))


def sam_model_available(config_path: str | None = None) -> bool:
    try:
        return resolve_sam_model_path(load_sam_config(config_path)).exists()
    except FileNotFoundError:
        return False


def resolve_sam_model_path(config: dict) -> Path:
    env_path = os.environ.get("GEOMORA_SAM_MODEL")
    if env_path:
        path = Path(env_path)
        if path.exists():
            return path

    model_file = config.get("model_file", "mobile_sam_v1.onnx")
    path = BACKEND_ROOT / "models" / model_file
    if path.exists():
        return path

    raise FileNotFoundError(f"SAM ONNX model not found: {path}")


def bbox_area(bbox: list[float]) -> float:
    return max(0.0, bbox[2] - bbox[0]) * max(0.0, bbox[3] - bbox[1])


def bbox_iou(a: list[float], b: list[float]) -> float:
    x1 = max(a[0], b[0])
    y1 = max(a[1], b[1])
    x2 = min(a[2], b[2])
    y2 = min(a[3], b[3])
    inter = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    if inter <= 0:
        return 0.0
    union = bbox_area(a) + bbox_area(b) - inter
    return inter / union if union > 0 else 0.0


def clamp_bbox(bbox: list[float]) -> list[float]:
    x1, y1, x2, y2 = bbox
    x1, x2 = sorted((max(0.0, x1), min(1.0, x2)))
    y1, y2 = sorted((max(0.0, y1), min(1.0, y2)))
    if x2 <= x1 or y2 <= y1:
        return bbox
    return [x1, y1, x2, y2]


def _pixels_from_norm(bbox_norm: list[float], width: int, height: int) -> tuple[int, int, int, int]:
    x1 = int(round(bbox_norm[0] * width))
    y1 = int(round(bbox_norm[1] * height))
    x2 = int(round(bbox_norm[2] * width))
    y2 = int(round(bbox_norm[3] * height))
    x1 = max(0, min(width - 1, x1))
    y1 = max(0, min(height - 1, y1))
    x2 = max(x1 + 1, min(width, x2))
    y2 = max(y1 + 1, min(height, y2))
    return x1, y1, x2, y2


def _norm_from_pixels(x1: int, y1: int, x2: int, y2: int, width: int, height: int) -> list[float]:
    return clamp_bbox([x1 / width, y1 / height, x2 / width, y2 / height])


def _inner_rect(x1: int, y1: int, x2: int, y2: int, margin: float) -> tuple[int, int, int, int]:
    width = x2 - x1
    height = y2 - y1
    pad_x = int(round(width * margin))
    pad_y = int(round(height * margin))
    return x1 + pad_x, y1 + pad_y, x2 - pad_x, y2 - pad_y


def _mask_to_bbox(mask: np.ndarray) -> list[float] | None:
    if mask is None or mask.size == 0:
        return None
    ys, xs = np.where(mask > 0)
    if xs.size == 0:
        return None
    return [
        float(xs.min()),
        float(ys.min()),
        float(xs.max() + 1),
        float(ys.max() + 1),
    ]


def _score_candidate(prompt: list[float], candidate: list[float]) -> float:
    area_ratio = bbox_area(candidate) / max(bbox_area(prompt), 1e-6)
    if area_ratio < MIN_AREA_RATIO or area_ratio > MAX_AREA_RATIO:
        return -1.0
    iou = bbox_iou(prompt, candidate)
    if iou < MIN_IOU_WITH_PROMPT:
        return -1.0
    tightness_bonus = 1.0 - abs(1.0 - area_ratio)
    return iou * 0.45 + tightness_bonus * 0.55


def refine_bbox_grabcut(
    bgr: np.ndarray,
    bbox_norm: list[float],
    *,
    iterations: int = 4,
    inner_margin: float = INNER_MARGIN,
) -> tuple[list[float] | None, np.ndarray | None]:
    height, width = bgr.shape[:2]
    x1, y1, x2, y2 = _pixels_from_norm(bbox_norm, width, height)
    ix1, iy1, ix2, iy2 = _inner_rect(x1, y1, x2, y2, inner_margin)
    if ix2 - ix1 < 4 or iy2 - iy1 < 4:
        return None, None

    roi = bgr[y1:y2, x1:x2].copy()
    mask = np.zeros(roi.shape[:2], np.uint8)
    bgd_model = np.zeros((1, 65), np.float64)
    fgd_model = np.zeros((1, 65), np.float64)
    rect = (
        max(0, ix1 - x1),
        max(0, iy1 - y1),
        max(1, ix2 - ix1),
        max(1, iy2 - iy1),
    )

    try:
        cv2.grabCut(roi, mask, rect, bgd_model, fgd_model, iterations, cv2.GC_INIT_WITH_RECT)
    except cv2.error:
        return None, None

    fg_mask = np.where((mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD), 255, 0).astype(np.uint8)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_OPEN, kernel, iterations=1)
    fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_CLOSE, kernel, iterations=1)

    local_bbox = _mask_to_bbox(fg_mask)
    if local_bbox is None:
        return None, None

    lx1, ly1, lx2, ly2 = local_bbox
    global_bbox = _norm_from_pixels(x1 + int(lx1), y1 + int(ly1), x1 + int(lx2), y1 + int(ly2), width, height)
    full_mask = np.zeros((height, width), dtype=np.uint8)
    full_mask[y1:y2, x1:x2] = fg_mask
    return global_bbox, full_mask


def refine_bbox_threshold(
    bgr: np.ndarray,
    bbox_norm: list[float],
    *,
    element_type: str,
) -> tuple[list[float] | None, np.ndarray | None]:
    height, width = bgr.shape[:2]
    x1, y1, x2, y2 = _pixels_from_norm(bbox_norm, width, height)
    roi = bgr[y1:y2, x1:x2]
    if roi.size == 0:
        return None, None

    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    _, binary = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    if element_type == "door":
        binary = cv2.bitwise_not(binary)

    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel, iterations=1)
    binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel, iterations=2)

    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None, None

    best = max(contours, key=cv2.contourArea)
    lx, ly, lw, lh = cv2.boundingRect(best)
    if lw < 2 or lh < 2:
        return None, None

    global_bbox = _norm_from_pixels(x1 + lx, y1 + ly, x1 + lx + lw, y1 + ly + lh, width, height)
    full_mask = np.zeros((height, width), dtype=np.uint8)
    cv2.drawContours(full_mask[y1:y2, x1:x2], [best], -1, 255, thickness=cv2.FILLED)
    return global_bbox, full_mask


def refine_bbox(
    bgr: np.ndarray,
    bbox_norm: list[float],
    *,
    element_type: str,
    config: dict | None = None,
) -> tuple[list[float], str, np.ndarray | None]:
    config = config or load_sam_config()
    prompt = clamp_bbox(bbox_norm)
    candidates: list[tuple[list[float], str, np.ndarray | None, float]] = []

    grabcut_bbox, grabcut_mask = refine_bbox_grabcut(
        bgr,
        prompt,
        iterations=int(config.get("grabcut_iterations", 4)),
        inner_margin=float(config.get("inner_margin", INNER_MARGIN)),
    )
    if grabcut_bbox:
        score = _score_candidate(prompt, grabcut_bbox)
        if score >= 0:
            candidates.append((grabcut_bbox, "grabcut_v1", grabcut_mask, score))

    threshold_bbox, threshold_mask = refine_bbox_threshold(bgr, prompt, element_type=element_type)
    if threshold_bbox:
        score = _score_candidate(prompt, threshold_bbox)
        if score >= 0:
            candidates.append((threshold_bbox, "threshold_v1", threshold_mask, score))

    if not candidates:
        return prompt, "prompt_only", None

    best_bbox, backend, mask, _ = max(candidates, key=lambda item: item[3])
    if _score_candidate(prompt, best_bbox) <= _score_candidate(prompt, prompt):
        return prompt, "prompt_only", None

    return best_bbox, backend, mask


def refine_elements(
    bgr: np.ndarray,
    elements: list[DetectedElement],
    *,
    config_path: str | None = None,
) -> tuple[list[DetectedElement], list[np.ndarray | None], dict]:
    config = load_sam_config(config_path)
    refined: list[DetectedElement] = []
    masks: list[np.ndarray | None] = []
    changed = 0
    backends: set[str] = set()

    for element in elements:
        new_bbox, backend, mask = refine_bbox(
            bgr,
            element.bbox_norm,
            element_type=element.type,
            config=config,
        )
        backends.add(backend)
        if new_bbox != clamp_bbox(element.bbox_norm):
            changed += 1
        refined.append(
            DetectedElement(
                type=element.type,
                bbox_norm=new_bbox,
                confidence=element.confidence,
            )
        )
        masks.append(mask)

    backend_label = sorted(backends)[0] if len(backends) == 1 else "hybrid_v1"
    if sam_model_available(config_path):
        backend_label = f"{backend_label}+onnx_ready"

    return refined, masks, {
        "refine_backend": backend_label,
        "refined_count": changed,
        "element_count": len(refined),
    }


def draw_refined_overlay(
    image: np.ndarray,
    elements: list[DetectedElement],
    masks: list[np.ndarray | None],
) -> np.ndarray:
    overlay = draw_overlay(image, elements)
    tint = overlay.copy()
    for mask in masks:
        if mask is None:
            continue
        colored = np.zeros_like(tint)
        colored[:, :, 1] = 180
        alpha = 0.28
        mask_bool = mask > 0
        tint[mask_bool] = cv2.addWeighted(tint[mask_bool], 1 - alpha, colored[mask_bool], alpha, 0)
    return tint


def refine_detection_result(
    image: np.ndarray,
    result: DetectionResult,
    *,
    return_overlay: bool = True,
    config_path: str | None = None,
) -> DetectionResult:
    if not result.elements:
        return DetectionResult(
            method="sam_v1",
            confidence=result.confidence,
            image_width=result.image_width,
            image_height=result.image_height,
            elements=[],
            overlay_base64=result.overlay_base64,
            debug={**result.debug, "refine_backend": "none", "base_method": result.method},
            scale_hint=result.scale_hint,
        )

    refined_elements, masks, refine_debug = refine_elements(
        image,
        result.elements,
        config_path=config_path,
    )

    overlay_base64 = result.overlay_base64
    if return_overlay:
        overlay = draw_refined_overlay(image, refined_elements, masks)
        overlay_base64 = encode_overlay_jpeg(overlay)

    confidence = (
        sum(element.confidence for element in refined_elements) / len(refined_elements)
        if refined_elements
        else result.confidence
    )

    return DetectionResult(
        method="sam_v1",
        confidence=confidence,
        image_width=result.image_width,
        image_height=result.image_height,
        elements=refined_elements,
        overlay_base64=overlay_base64,
        debug={
            **result.debug,
            **refine_debug,
            "base_method": result.method,
        },
        scale_hint=result.scale_hint,
    )
