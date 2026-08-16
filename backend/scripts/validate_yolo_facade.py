"""Validate exported facade YOLO ONNX on the canonical rectified synthetic scene."""

from __future__ import annotations

import sys
from pathlib import Path

import cv2
import numpy as np

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from geomora_detect.pipeline import detect_facade


def _canonical_rectified(width: int = 800, height: int = 600) -> np.ndarray:
    image = np.full((height, width, 3), (210, 210, 210), dtype=np.uint8)
    cv2.rectangle(image, (20, 40), (width - 20, height - 40), (175, 168, 158), -1)
    windows = [
        (80, 140, 200, 320),
        (240, 140, 360, 320),
        (400, 140, 520, 320),
        (560, 140, 680, 320),
    ]
    for x1, y1, x2, y2 in windows:
        cv2.rectangle(image, (x1, y1), (x2, y2), (35, 35, 120), -1)
    cv2.rectangle(image, (10, 330), (70, 560), (25, 25, 90), -1)
    return image


def main() -> None:
    image = _canonical_rectified()
    path = BACKEND_ROOT / "cache" / "validate_rectified.jpg"
    path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(path), image)

    result = detect_facade(str(path), method="yolo_v1")
    windows = [element for element in result.elements if element.type == "window"]
    doors = [element for element in result.elements if element.type == "door"]

    print(f"method={result.method} confidence={result.confidence:.3f}")
    print(f"windows={len(windows)} doors={len(doors)}")
    for element in result.elements:
        bbox = element.bbox_norm
        print(f"  {element.type}: {bbox} conf={element.confidence:.3f}")

    if len(windows) < 3 or len(doors) < 1:
        raise SystemExit("Validation failed — expected >=3 windows and >=1 door")

    print("Validation passed.")


if __name__ == "__main__":
    main()
