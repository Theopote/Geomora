from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .models import DetectedElement


@dataclass
class ClassMetrics:
    true_positives: int = 0
    false_positives: int = 0
    false_negatives: int = 0

    @property
    def precision(self) -> float:
        denom = self.true_positives + self.false_positives
        return self.true_positives / denom if denom else 1.0

    @property
    def recall(self) -> float:
        denom = self.true_positives + self.false_negatives
        return self.true_positives / denom if denom else 1.0

    @property
    def f1(self) -> float:
        p = self.precision
        r = self.recall
        return (2 * p * r / (p + r)) if (p + r) else 0.0

    def to_dict(self) -> dict[str, float | int]:
        return {
            "true_positives": self.true_positives,
            "false_positives": self.false_positives,
            "false_negatives": self.false_negatives,
            "precision": round(self.precision, 4),
            "recall": round(self.recall, 4),
            "f1": round(self.f1, 4),
        }


@dataclass
class ImageEvaluation:
    image_path: str
    label_path: str | None
    method: str
    confidence: float
    window_count: int
    door_count: int
    scale_hint: dict[str, Any] | None
    metrics: dict[str, ClassMetrics] | None = None
    passed: bool = True
    notes: list[str] | None = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "image_path": self.image_path,
            "label_path": self.label_path,
            "method": self.method,
            "confidence": round(self.confidence, 4),
            "window_count": self.window_count,
            "door_count": self.door_count,
            "scale_hint": self.scale_hint,
            "passed": self.passed,
            "notes": self.notes or [],
        }
        if self.metrics:
            payload["metrics"] = {key: value.to_dict() for key, value in self.metrics.items()}
        return payload


YOLO_CLASS_NAMES = {0: "window", 1: "door"}


def yolo_line_to_bbox_norm(line: str) -> tuple[str, list[float]] | None:
    parts = line.strip().split()
    if len(parts) != 5:
        return None

    class_id = int(float(parts[0]))
    cx, cy, width, height = (float(value) for value in parts[1:])
    if class_id not in YOLO_CLASS_NAMES:
        return None
    if width <= 0 or height <= 0:
        return None

    x_min = cx - width / 2.0
    y_min = cy - height / 2.0
    x_max = cx + width / 2.0
    y_max = cy + height / 2.0
    return YOLO_CLASS_NAMES[class_id], [x_min, y_min, x_max, y_max]


def parse_yolo_label_file(label_path: Path) -> list[tuple[str, list[float]]]:
    if not label_path.exists():
        return []

    boxes: list[tuple[str, list[float]]] = []
    for line in label_path.read_text(encoding="utf-8").splitlines():
        parsed = yolo_line_to_bbox_norm(line)
        if parsed:
            boxes.append(parsed)
    return boxes


def bbox_iou(a: list[float], b: list[float]) -> float:
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    inter_x1 = max(ax1, bx1)
    inter_y1 = max(ay1, by1)
    inter_x2 = min(ax2, bx2)
    inter_y2 = min(ay2, by2)
    inter_w = max(0.0, inter_x2 - inter_x1)
    inter_h = max(0.0, inter_y2 - inter_y1)
    inter_area = inter_w * inter_h
    if inter_area <= 0:
        return 0.0

    area_a = max(0.0, ax2 - ax1) * max(0.0, ay2 - ay1)
    area_b = max(0.0, bx2 - bx1) * max(0.0, by2 - by1)
    union = area_a + area_b - inter_area
    return inter_area / union if union else 0.0


def match_class_boxes(
    predictions: list[list[float]],
    ground_truth: list[list[float]],
    *,
    iou_threshold: float = 0.5,
) -> ClassMetrics:
    remaining_truth = ground_truth[:]
    metrics = ClassMetrics()

    for prediction in predictions:
        best_index = None
        best_iou = 0.0
        for index, truth in enumerate(remaining_truth):
            iou = bbox_iou(prediction, truth)
            if iou > best_iou:
                best_iou = iou
                best_index = index

        if best_index is not None and best_iou >= iou_threshold:
            metrics.true_positives += 1
            remaining_truth.pop(best_index)
        else:
            metrics.false_positives += 1

    metrics.false_negatives = len(remaining_truth)
    return metrics


def evaluate_elements(
    elements: list[DetectedElement],
    ground_truth: list[tuple[str, list[float]]],
    *,
    iou_threshold: float = 0.5,
    window_recall_min: float = 0.7,
    window_precision_min: float = 0.6,
    door_recall_min: float = 0.5,
    door_precision_min: float = 0.5,
) -> tuple[dict[str, ClassMetrics], bool, list[str]]:
    gt_by_type: dict[str, list[list[float]]] = {"window": [], "door": []}
    pred_by_type: dict[str, list[list[float]]] = {"window": [], "door": []}

    for class_name, bbox in ground_truth:
        if class_name in gt_by_type:
            gt_by_type[class_name].append(bbox)

    for element in elements:
        if element.type in pred_by_type and element.bbox_norm:
            pred_by_type[element.type].append(element.bbox_norm)

    metrics = {
        class_name: match_class_boxes(
            pred_by_type[class_name],
            gt_by_type[class_name],
            iou_threshold=iou_threshold,
        )
        for class_name in ("window", "door")
    }

    notes: list[str] = []
    passed = True

    window_metrics = metrics["window"]
    if gt_by_type["window"]:
        if window_metrics.recall < window_recall_min:
            passed = False
            notes.append(
                f"window recall {window_metrics.recall:.2f} < {window_recall_min:.2f}"
            )
        if window_metrics.precision < window_precision_min:
            passed = False
            notes.append(
                f"window precision {window_metrics.precision:.2f} < {window_precision_min:.2f}"
            )

    door_metrics = metrics["door"]
    if gt_by_type["door"]:
        if door_metrics.recall < door_recall_min:
            passed = False
            notes.append(f"door recall {door_metrics.recall:.2f} < {door_recall_min:.2f}")
        if door_metrics.precision < door_precision_min:
            passed = False
            notes.append(
                f"door precision {door_metrics.precision:.2f} < {door_precision_min:.2f}"
            )

    return metrics, passed, notes


def resolve_label_path(image_path: Path, labels_dir: Path | None = None) -> Path | None:
    if labels_dir is None:
        labels_dir = image_path.parent.parent / "labels"
    candidate = labels_dir / f"{image_path.stem}.txt"
    return candidate if candidate.exists() else None


def discover_images(root: Path) -> list[Path]:
    patterns = ("*.jpg", "*.jpeg", "*.png", "*.webp")
    images: list[Path] = []
    for pattern in patterns:
        images.extend(root.glob(pattern))
    return sorted(images)


def discover_dataset_images(dataset_root: Path, split: str | None = None) -> list[tuple[Path, Path | None]]:
    splits = [split] if split else ("train", "val")
    pairs: list[tuple[Path, Path | None]] = []

    for current_split in splits:
        images_dir = dataset_root / current_split / "images"
        labels_dir = dataset_root / current_split / "labels"
        if not images_dir.exists():
            continue
        for image_path in discover_images(images_dir):
            label_path = resolve_label_path(image_path, labels_dir)
            pairs.append((image_path, label_path))

    return pairs
