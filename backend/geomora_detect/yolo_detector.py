from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path

import cv2
import numpy as np

from .models import DetectedElement, DetectionResult
from .nms import dedupe_doors, suppress_overlaps
from .overlays import draw_overlay, encode_overlay_jpeg

BACKEND_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG_PATH = BACKEND_ROOT / "models" / "detection_config.json"


class YoloModelNotFoundError(FileNotFoundError):
    """Raised when the ONNX model file is missing."""


@lru_cache(maxsize=1)
def _load_config(config_path: str) -> dict:
    path = Path(config_path)
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


@lru_cache(maxsize=1)
def _load_session(model_path: str):
    import onnxruntime as ort

    return ort.InferenceSession(
        model_path,
        providers=["CPUExecutionProvider"],
    )


def resolve_model_path(config: dict) -> Path:
    env_path = os.environ.get("GEOMORA_YOLO_MODEL")
    if env_path:
        path = Path(env_path)
        if path.exists():
            return path

    model_file = config.get("model_file", "facade_yolo_v1.onnx")
    path = BACKEND_ROOT / "models" / model_file
    if path.exists():
        return path

    raise YoloModelNotFoundError(f"YOLO model not found: {path}")


def model_available(config_path: str | None = None) -> bool:
    try:
        config = load_detection_config(config_path)
        resolve_model_path(config)
        return True
    except (YoloModelNotFoundError, FileNotFoundError, json.JSONDecodeError):
        return False


def load_detection_config(config_path: str | None = None) -> dict:
    path = Path(config_path or os.environ.get("GEOMORA_DETECTION_CONFIG", DEFAULT_CONFIG_PATH))
    if not path.exists():
        raise FileNotFoundError(f"Detection config not found: {path}")
    return _load_config(str(path))


def _letterbox(
    image: np.ndarray,
    input_size: int,
) -> tuple[np.ndarray, float, tuple[int, int]]:
    height, width = image.shape[:2]
    scale = min(input_size / width, input_size / height)
    new_width = int(round(width * scale))
    new_height = int(round(height * scale))
    resized = cv2.resize(image, (new_width, new_height), interpolation=cv2.INTER_LINEAR)

    pad_x = (input_size - new_width) // 2
    pad_y = (input_size - new_height) // 2
    padded = np.full((input_size, input_size, 3), 114, dtype=np.uint8)
    padded[pad_y:pad_y + new_height, pad_x:pad_x + new_width] = resized

    return padded, scale, (pad_x, pad_y)


def _prepare_input(image: np.ndarray, input_size: int) -> tuple[np.ndarray, float, tuple[int, int]]:
    letterboxed, scale, padding = _letterbox(image, input_size)
    blob = letterboxed.astype(np.float32) / 255.0
    blob = np.transpose(blob, (2, 0, 1))
    blob = np.expand_dims(blob, axis=0)
    return blob, scale, padding


def _xywh_to_xyxy(boxes: np.ndarray) -> np.ndarray:
    half_w = boxes[:, 2] / 2.0
    half_h = boxes[:, 3] / 2.0
    return np.stack(
        [
            boxes[:, 0] - half_w,
            boxes[:, 1] - half_h,
            boxes[:, 0] + half_w,
            boxes[:, 1] + half_h,
        ],
        axis=1,
    )


def _scale_boxes_to_original(
    boxes_xyxy: np.ndarray,
    scale: float,
    padding: tuple[int, int],
    image_width: int,
    image_height: int,
) -> np.ndarray:
    pad_x, pad_y = padding
    scaled = boxes_xyxy.copy()
    scaled[:, [0, 2]] = (scaled[:, [0, 2]] - pad_x) / scale
    scaled[:, [1, 3]] = (scaled[:, [1, 3]] - pad_y) / scale
    scaled[:, [0, 2]] = np.clip(scaled[:, [0, 2]], 0, image_width)
    scaled[:, [1, 3]] = np.clip(scaled[:, [1, 3]], 0, image_height)
    return scaled


def _nms_indices(boxes: np.ndarray, scores: np.ndarray, iou_threshold: float) -> list[int]:
    if len(boxes) == 0:
        return []

    x1 = boxes[:, 0]
    y1 = boxes[:, 1]
    x2 = boxes[:, 2]
    y2 = boxes[:, 3]
    areas = (x2 - x1) * (y2 - y1)
    order = scores.argsort()[::-1]
    keep: list[int] = []

    while order.size > 0:
        index = int(order[0])
        keep.append(index)
        if order.size == 1:
            break

        rest = order[1:]
        xx1 = np.maximum(x1[index], x1[rest])
        yy1 = np.maximum(y1[index], y1[rest])
        xx2 = np.minimum(x2[index], x2[rest])
        yy2 = np.minimum(y2[index], y2[rest])

        inter = np.maximum(0.0, xx2 - xx1) * np.maximum(0.0, yy2 - yy1)
        union = areas[index] + areas[rest] - inter
        iou_values = np.where(union > 0, inter / union, 0.0)
        order = rest[iou_values <= iou_threshold]

    return keep


def _parse_predictions(
    output: np.ndarray,
    class_names: list[str],
    confidence_threshold: float,
    iou_threshold: float,
    image_width: int,
    image_height: int,
    scale: float,
    padding: tuple[int, int],
) -> list[DetectedElement]:
    predictions = np.squeeze(output)
    if predictions.ndim != 2:
        raise ValueError(f"Unexpected YOLO output shape: {output.shape}")

    if predictions.shape[0] < 6:
        raise ValueError(f"YOLO output has too few channels: {predictions.shape}")

    # Ultralytics ONNX export: (4 + num_classes, num_boxes)
    if predictions.shape[0] < predictions.shape[1]:
        predictions = predictions.T

    boxes_xywh = predictions[:, :4]
    class_scores = predictions[:, 4:]
    if class_scores.shape[1] == 0:
        return []

    class_ids = np.argmax(class_scores, axis=1)
    confidences = class_scores[np.arange(class_scores.shape[0]), class_ids]
    mask = confidences >= confidence_threshold
    if not np.any(mask):
        return []

    boxes_xywh = boxes_xywh[mask]
    class_ids = class_ids[mask]
    confidences = confidences[mask]

    boxes_xyxy = _xywh_to_xyxy(boxes_xywh)
    keep = _nms_indices(boxes_xyxy, confidences, iou_threshold)
    boxes_xyxy = boxes_xyxy[keep]
    class_ids = class_ids[keep]
    confidences = confidences[keep]

    boxes_xyxy = _scale_boxes_to_original(
        boxes_xyxy,
        scale,
        padding,
        image_width,
        image_height,
    )

    elements: list[DetectedElement] = []
    for box, class_id, confidence in zip(boxes_xyxy, class_ids, confidences, strict=True):
        x1, y1, x2, y2 = box.tolist()
        if x2 <= x1 or y2 <= y1:
            continue

        label_index = int(class_id)
        if label_index < 0 or label_index >= len(class_names):
            continue

        bbox_norm = [
            x1 / image_width,
            y1 / image_height,
            x2 / image_width,
            y2 / image_height,
        ]
        elements.append(
            DetectedElement(
                type=class_names[label_index],
                bbox_norm=bbox_norm,
                confidence=float(confidence),
            )
        )

    return elements


def detect_yolo_elements(
    image: np.ndarray,
    *,
    return_overlay: bool = True,
    config_path: str | None = None,
) -> DetectionResult:
    if image.ndim == 2:
        bgr = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
    else:
        bgr = image.copy()

    height, width = bgr.shape[:2]
    config = load_detection_config(config_path)
    model_path = resolve_model_path(config)
    input_size = int(config.get("input_size", 640))
    class_names = list(config.get("class_names", ["window", "door"]))
    confidence_threshold = float(config.get("confidence_threshold", 0.25))
    iou_threshold = float(config.get("iou_threshold", 0.45))

    session = _load_session(str(model_path))
    input_name = session.get_inputs()[0].name
    blob, scale, padding = _prepare_input(bgr, input_size)
    outputs = session.run(None, {input_name: blob})
    raw_elements = _parse_predictions(
        outputs[0],
        class_names,
        confidence_threshold,
        iou_threshold,
        width,
        height,
        scale,
        padding,
    )

    elements = suppress_overlaps(raw_elements, iou_threshold=0.4)
    elements = dedupe_doors(elements)
    confidence = (
        sum(element.confidence for element in elements) / len(elements) if elements else 0.35
    )

    overlay_base64 = None
    if return_overlay:
        overlay = draw_overlay(bgr, elements)
        overlay_base64 = encode_overlay_jpeg(overlay)

    return DetectionResult(
        method="yolo_v1",
        confidence=confidence,
        image_width=width,
        image_height=height,
        elements=elements,
        overlay_base64=overlay_base64,
        debug={
            "model_path": str(model_path),
            "candidate_count": len(raw_elements),
            "element_count": len(elements),
            "class_names": class_names,
        },
    )
