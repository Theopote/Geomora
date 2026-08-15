"""Train a small YOLO facade detector and export ONNX for Geomora Phase 3.5.

Dev-only — requires ultralytics (see backend/requirements-dev.txt).

Usage:
  cd backend
  .venv\\Scripts\\pip install -r requirements-dev.txt
  .venv\\Scripts\\python scripts/train_yolo_facade.py
"""

from __future__ import annotations

import random
import shutil
from pathlib import Path

import cv2
import numpy as np

BACKEND_ROOT = Path(__file__).resolve().parents[1]
DATASET_ROOT = BACKEND_ROOT / "data" / "facade_yolo"
MODELS_DIR = BACKEND_ROOT / "models"
ONNX_OUTPUT = MODELS_DIR / "facade_yolo_v1.onnx"


def _random_facade(width: int = 800, height: int = 600) -> tuple[np.ndarray, list[tuple[str, float, float, float, float]]]:
    image = np.full((height, width, 3), (210, 205, 198), dtype=np.uint8)
    labels: list[tuple[str, float, float, float, float]] = []

    margin = 40
    facade_x1 = random.randint(20, margin)
    facade_y1 = random.randint(20, margin)
    facade_x2 = width - random.randint(20, margin)
    facade_y2 = height - random.randint(20, margin)
    cv2.rectangle(image, (facade_x1, facade_y1), (facade_x2, facade_y2), (175, 168, 158), -1)

    window_count = random.randint(2, 5)
    facade_w = facade_x2 - facade_x1
    facade_h = facade_y2 - facade_y1
    slot_w = facade_w / window_count

    for index in range(window_count):
        win_w = int(slot_w * random.uniform(0.55, 0.85))
        win_h = int(facade_h * random.uniform(0.18, 0.32))
        cx_slot = facade_x1 + int(slot_w * (index + 0.5))
        x1 = max(facade_x1, cx_slot - win_w // 2)
        y1 = facade_y1 + int(facade_h * random.uniform(0.12, 0.22))
        x2 = min(facade_x2, x1 + win_w)
        y2 = min(facade_y2 - int(facade_h * 0.08), y1 + win_h)
        color = (
            random.randint(80, 140),
            random.randint(140, 200),
            random.randint(180, 240),
        )
        cv2.rectangle(image, (x1, y1), (x2, y2), color, -1)
        labels.append(_yolo_label("window", x1, y1, x2, y2, width, height))

    if random.random() < 0.85:
        door_w = int(facade_w * random.uniform(0.08, 0.14))
        door_h = int(facade_h * random.uniform(0.42, 0.58))
        x1 = facade_x1 + random.randint(0, max(1, int(facade_w * 0.08)))
        y2 = facade_y2 - random.randint(5, 20)
        y1 = y2 - door_h
        x2 = min(facade_x2, x1 + door_w)
        cv2.rectangle(image, (x1, y1), (x2, y2), (70, 110, 80), -1)
        labels.append(_yolo_label("door", x1, y1, x2, y2, width, height))

    return image, labels


def _yolo_label(
    class_name: str,
    x1: int,
    y1: int,
    x2: int,
    y2: int,
    width: int,
    height: int,
) -> tuple[str, float, float, float, float]:
    class_id = 0 if class_name == "window" else 1
    cx = ((x1 + x2) / 2.0) / width
    cy = ((y1 + y2) / 2.0) / height
    box_w = (x2 - x1) / width
    box_h = (y2 - y1) / height
    return (str(class_id), cx, cy, box_w, box_h)


def generate_dataset(train_count: int = 160, val_count: int = 40) -> Path:
    if DATASET_ROOT.exists():
        shutil.rmtree(DATASET_ROOT)

    for split, count in (("train", train_count), ("val", val_count)):
        images_dir = DATASET_ROOT / split / "images"
        labels_dir = DATASET_ROOT / split / "labels"
        images_dir.mkdir(parents=True, exist_ok=True)
        labels_dir.mkdir(parents=True, exist_ok=True)

        for index in range(count):
            image, labels = _random_facade()
            stem = f"{split}_{index:04d}"
            image_path = images_dir / f"{stem}.jpg"
            label_path = labels_dir / f"{stem}.txt"
            cv2.imwrite(str(image_path), image)
            label_lines = [
                f"{class_id} {cx:.6f} {cy:.6f} {box_w:.6f} {box_h:.6f}"
                for class_id, cx, cy, box_w, box_h in labels
            ]
            label_path.write_text("\n".join(label_lines) + ("\n" if label_lines else ""), encoding="utf-8")

    yaml_path = DATASET_ROOT / "facade.yaml"
    yaml_path.write_text(
        "\n".join(
            [
                f"path: {DATASET_ROOT.as_posix()}",
                "train: train/images",
                "val: val/images",
                "names:",
                "  0: window",
                "  1: door",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return yaml_path


def train_and_export(epochs: int = 40) -> Path:
    from ultralytics import YOLO

    yaml_path = generate_dataset()
    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    model = YOLO("yolov8n.pt")
    results = model.train(
        data=str(yaml_path),
        epochs=epochs,
        imgsz=640,
        batch=16,
        patience=10,
        project=str(BACKEND_ROOT / "runs"),
        name="facade_yolo_v1",
        exist_ok=True,
        verbose=False,
    )

    best_weights = Path(results.save_dir) / "weights" / "best.pt"
    if not best_weights.exists():
        raise FileNotFoundError(f"Training did not produce weights: {best_weights}")

    export_model = YOLO(str(best_weights))
    export_model.export(format="onnx", imgsz=640, simplify=True)

    exported = best_weights.with_suffix(".onnx")
    if not exported.exists():
        raise FileNotFoundError(f"ONNX export missing: {exported}")

    shutil.copy2(exported, ONNX_OUTPUT)
    print(f"Exported ONNX model -> {ONNX_OUTPUT}")
    return ONNX_OUTPUT


def main() -> None:
    path = train_and_export()
    print(f"Done. Model ready at {path}")


if __name__ == "__main__":
    main()
