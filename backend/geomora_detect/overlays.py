from __future__ import annotations

import base64

import cv2
import numpy as np

from .models import DetectedElement


COLORS = {
    "window": (66, 133, 244),
    "door": (52, 168, 83),
}


def draw_overlay(image: np.ndarray, elements: list[DetectedElement]) -> np.ndarray:
    overlay = image.copy()
    height, width = overlay.shape[:2]

    for element in elements:
        x1 = int(element.bbox_norm[0] * width)
        y1 = int(element.bbox_norm[1] * height)
        x2 = int(element.bbox_norm[2] * width)
        y2 = int(element.bbox_norm[3] * height)
        color = COLORS.get(element.type, (255, 200, 0))
        cv2.rectangle(overlay, (x1, y1), (x2, y2), color, 2)
        label = f"{element.type} {element.confidence:.2f}"
        cv2.putText(
            overlay,
            label,
            (x1, max(18, y1 - 6)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
            color,
            1,
            cv2.LINE_AA,
        )

    return overlay


def encode_overlay_jpeg(image: np.ndarray) -> str | None:
    ok, encoded = cv2.imencode(".jpg", image, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
    if not ok:
        return None
    return base64.b64encode(encoded.tobytes()).decode("ascii")
