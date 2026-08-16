from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from .colmap_common import (
    colmap_available,
    copy_view_images,
    load_primary_secondary_images,
    prepare_workspace,
    read_image_shape,
    run_sparse_reconstruction,
)
from .colmap_geometry import rasterize_depth_from_points
from .colmap_model import read_cameras_text
from .feature_match import estimate_planar_homography, homography_confidence
from .models import MultiviewResult, ViewRegistration


def _shared_observations(primary_image, secondary_image) -> tuple[np.ndarray, np.ndarray, int]:
    primary_lookup = {
        point3d_id: (x, y)
        for x, y, point3d_id in primary_image.points2d
        if point3d_id >= 0
    }
    secondary_lookup = {
        point3d_id: (x, y)
        for x, y, point3d_id in secondary_image.points2d
        if point3d_id >= 0
    }
    shared_ids = sorted(set(primary_lookup).intersection(secondary_lookup))
    if not shared_ids:
        return np.empty((0, 2), dtype=np.float32), np.empty((0, 2), dtype=np.float32), 0

    points_primary = np.float32([primary_lookup[point_id] for point_id in shared_ids])
    points_secondary = np.float32([secondary_lookup[point_id] for point_id in shared_ids])
    return points_primary, points_secondary, len(shared_ids)


def register_views_colmap(primary_path: str, secondary_path: str) -> MultiviewResult:
    if not colmap_available():
        raise RuntimeError("COLMAP executable not found on PATH")

    primary = Path(primary_path)
    secondary = Path(secondary_path)
    if not primary.exists():
        raise ValueError(f"Primary image not found: {primary_path}")
    if not secondary.exists():
        raise ValueError(f"Secondary image not found: {secondary_path}")

    workspace = prepare_workspace(primary.parent)
    copy_view_images(workspace, primary, secondary)
    sparse_model_dir = run_sparse_reconstruction(workspace)
    images, points3d, primary_image, secondary_image = load_primary_secondary_images(sparse_model_dir)

    points_primary, points_secondary, match_count = _shared_observations(primary_image, secondary_image)
    homography, inlier_count = estimate_planar_homography(points_primary, points_secondary)
    if homography is None:
        raise RuntimeError("Unable to estimate homography from COLMAP observations")

    primary_h, primary_w = read_image_shape(primary)
    secondary_h, secondary_w = read_image_shape(secondary)
    homography_list = homography.astype(float).tolist()
    confidence = homography_confidence(match_count, inlier_count)

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
        method="colmap_sparse_v1",
        confidence=confidence,
        match_count=match_count,
        inlier_count=inlier_count,
        views=views,
        homography=homography_list,
        debug={
            "registration_backend": "colmap",
            "primary_pose": {
                "qvec": list(primary_image.qvec),
                "tvec": list(primary_image.tvec),
            },
            "secondary_pose": {
                "qvec": list(secondary_image.qvec),
                "tvec": list(secondary_image.tvec),
            },
            "sparse_points": len(points3d),
            "workspace": str(workspace.root),
        },
    )
