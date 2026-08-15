from __future__ import annotations

import base64
import json
from pathlib import Path

import cv2
import numpy as np

from .homography import (
    compute_rectifying_homography,
    estimate_facade_quad_from_vps,
    quad_confidence,
    warp_image,
)
from .line_detection import classify_line_families, detect_lines, load_image
from .models import RectificationResult
from .vanishing_point import estimate_vanishing_points


def rectify_image(
    image_path: str,
    output_path: str | None = None,
    corners: list[list[float]] | None = None,
    return_base64: bool = False,
) -> RectificationResult:
    image = load_image(image_path)
    height, width = image.shape[:2]

    lines = detect_lines(image)
    family_a, family_b = classify_line_families(lines)
    vanishing_points = estimate_vanishing_points(family_a, family_b, width, height)

    manual = corners is not None and len(corners) == 4
    if manual:
        corners_src = corners
        method = "manual_corners"
    else:
        corners_src = estimate_facade_quad_from_vps(width, height, vanishing_points)
        method = "auto_vanishing_point"

    homography, corners_dst, output_size = compute_rectifying_homography(corners_src)
    rectified = warp_image(image, homography, output_size)

    saved_path = None
    if output_path:
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(output_file), rectified)
        saved_path = str(output_file)

    encoded = None
    if return_base64:
        success, buffer = cv2.imencode(".jpg", rectified, [int(cv2.IMWRITE_JPEG_QUALITY), 90])
        if success:
            encoded = base64.b64encode(buffer).decode("ascii")

    confidence = quad_confidence(
        corners_src,
        width,
        height,
        len(lines),
        vanishing_points,
        manual=manual,
    )

    vp_payload: list[list[float | None]] = []
    for vp in vanishing_points:
        if vp is None:
            vp_payload.append([None, None])
        else:
            vp_payload.append([vp[0], vp[1]])

    return RectificationResult(
        rectified_image_path=saved_path,
        rectified_image_base64=encoded,
        homography=homography.tolist(),
        vanishing_points=vp_payload,
        corners_src=corners_src,
        corners_dst=corners_dst.astype(float).tolist(),
        confidence=confidence,
        method=method,
        line_count=len(lines),
        output_width=output_size[0],
        output_height=output_size[1],
        debug={
            "family_a_lines": len(family_a),
            "family_b_lines": len(family_b),
            "input_width": width,
            "input_height": height,
        },
    )


def parse_corners(raw: str | None) -> list[list[float]] | None:
    if not raw:
        return None
    data = json.loads(raw)
    if not isinstance(data, list) or len(data) != 4:
        raise ValueError("corners must be a JSON array of four [x, y] points")
    return [[float(point[0]), float(point[1])] for point in data]
