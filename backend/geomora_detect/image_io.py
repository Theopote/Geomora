from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np


def imread_bgr(path: str | Path) -> np.ndarray:
    """Read BGR image; works with Unicode paths on Windows (cv2.imread fails)."""
    file_path = Path(path)
    if not file_path.exists():
        raise ValueError(f"Image not found: {file_path}")

    data = np.fromfile(str(file_path), dtype=np.uint8)
    image = cv2.imdecode(data, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError(f"Unable to read image: {file_path}")
    return image


def imwrite_bgr(path: str | Path, image: np.ndarray, *, quality: int = 90) -> None:
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    ok, encoded = cv2.imencode(".jpg", image, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
    if not ok:
        raise ValueError(f"Unable to encode image: {file_path}")
    encoded.tofile(str(file_path))
