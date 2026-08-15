"""Generate a synthetic perspective facade image for Geomora acceptance tests."""

from __future__ import annotations

import math
from pathlib import Path

import cv2
import numpy as np

OUTPUT = Path(__file__).with_name("facade_perspective_synthetic.jpg")
WIDTH, HEIGHT = 640, 480


def main() -> None:
    image = np.full((HEIGHT, WIDTH, 3), (210, 205, 198), dtype=np.uint8)

    src = np.float32(
        [
            [80, 60],
            [WIDTH - 60, 40],
            [WIDTH - 40, HEIGHT - 50],
            [50, HEIGHT - 30],
        ]
    )
    dst = np.float32([[0, 0], [WIDTH - 1, 0], [WIDTH - 1, HEIGHT - 1], [0, HEIGHT - 1]])
    homography = cv2.getPerspectiveTransform(dst, src)

    def draw_rect(x1: int, y1: int, x2: int, y2: int, color: tuple[int, int, int]) -> None:
        corners = np.float32(
            [
                [x1, y1],
                [x2, y1],
                [x2, y2],
                [x1, y2],
            ]
        ).reshape(-1, 1, 2)
        warped = cv2.perspectiveTransform(corners, homography).astype(np.int32)
        cv2.fillPoly(image, [warped], color)

    draw_rect(40, 40, WIDTH - 40, HEIGHT - 40, (175, 168, 158))
    draw_rect(120, 90, 220, 210, (120, 175, 220))
    draw_rect(280, 90, 380, 210, (120, 175, 220))
    draw_rect(440, 90, 540, 210, (120, 175, 220))
    draw_rect(200, 250, 320, 430, (90, 140, 95))

    for angle_deg, origin in ((12, (0, HEIGHT // 2)), (-10, (WIDTH, HEIGHT // 3))):
        angle = math.radians(angle_deg)
        length = max(WIDTH, HEIGHT) * 2
        dx = math.cos(angle) * length
        dy = math.sin(angle) * length
        pt1 = (int(origin[0] - dx), int(origin[1] - dy))
        pt2 = (int(origin[0] + dx), int(origin[1] + dy))
        cv2.line(image, pt1, pt2, (130, 125, 118), 2, cv2.LINE_AA)

    cv2.imwrite(str(OUTPUT), image, [int(cv2.IMWRITE_JPEG_QUALITY), 92])
    print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    main()
