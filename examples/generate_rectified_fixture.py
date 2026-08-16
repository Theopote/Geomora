"""Generate a rectified synthetic facade for Geomora detection acceptance."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

OUTPUT = Path(__file__).with_name("facade_rectified_synthetic.jpg")
WIDTH, HEIGHT = 800, 600


def main() -> None:
    image = np.full((HEIGHT, WIDTH, 3), (210, 210, 210), dtype=np.uint8)
    cv2.rectangle(image, (20, 40), (WIDTH - 20, HEIGHT - 40), (175, 168, 158), -1)

    windows = [
        (80, 140, 200, 320),
        (240, 140, 360, 320),
        (400, 140, 520, 320),
        (560, 140, 680, 320),
    ]
    for x1, y1, x2, y2 in windows:
        cv2.rectangle(image, (x1, y1), (x2, y2), (35, 35, 120), -1)

    cv2.rectangle(image, (10, 330), (70, 560), (25, 25, 90), -1)
    cv2.imwrite(str(OUTPUT), image, [int(cv2.IMWRITE_JPEG_QUALITY), 92])
    print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    main()
