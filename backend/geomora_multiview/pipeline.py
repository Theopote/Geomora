from __future__ import annotations

from pathlib import Path

from .feature_match import (
    detect_and_match,
    estimate_planar_homography,
    homography_confidence,
    load_gray,
)
from .models import MultiviewResult, ViewRegistration


def register_views(primary_path: str, secondary_path: str) -> MultiviewResult:
    primary = Path(primary_path)
    secondary = Path(secondary_path)
    if not primary.exists():
        raise ValueError(f"Primary image not found: {primary_path}")
    if not secondary.exists():
        raise ValueError(f"Secondary image not found: {secondary_path}")

    primary_gray = load_gray(str(primary))
    secondary_gray = load_gray(str(secondary))
    primary_h, primary_w = primary_gray.shape[:2]
    secondary_h, secondary_w = secondary_gray.shape[:2]

    points_primary, points_secondary, match_count = detect_and_match(primary_gray, secondary_gray)
    homography, inlier_count = estimate_planar_homography(points_primary, points_secondary)
    confidence = homography_confidence(match_count, inlier_count)

    homography_list = homography.astype(float).tolist() if homography is not None else None
    views = [
        ViewRegistration(
            id="view_001",
            role="primary",
            image_width=primary_w,
            image_height=primary_h,
        ),
        ViewRegistration(
            id="view_002",
            role="secondary",
            image_width=secondary_w,
            image_height=secondary_h,
            transform_to_primary=homography_list,
        ),
    ]

    return MultiviewResult(
        method="feature_homography_v1",
        confidence=confidence,
        match_count=match_count,
        inlier_count=inlier_count,
        views=views,
        homography=homography_list,
        debug={
            "detector": "ORB",
            "matcher": "BF_HAMMING_CROSSCHECK",
            "ransac_threshold": 5.0,
        },
    )
