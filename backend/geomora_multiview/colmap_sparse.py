from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import cv2
import numpy as np

from .colmap_model import read_images_text, read_points3d_text
from .feature_match import estimate_planar_homography, homography_confidence
from .models import MultiviewResult, ViewRegistration


def colmap_available() -> bool:
    return shutil.which("colmap") is not None


def _run_colmap(args: list[str], *, cwd: Path) -> None:
    command = ["colmap", *args]
    completed = subprocess.run(
        command,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        stderr = (completed.stderr or completed.stdout or "").strip()
        raise RuntimeError(stderr or f"COLMAP failed: {' '.join(command)}")


def _shared_observations(
    primary_image,
    secondary_image,
) -> tuple[np.ndarray, np.ndarray, int]:
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

    workspace = primary.parent / "colmap_workspace"
    image_dir = workspace / "images"
    database_path = workspace / "database.db"
    sparse_dir = workspace / "sparse"
    if workspace.exists():
        shutil.rmtree(workspace)
    image_dir.mkdir(parents=True)
    sparse_dir.mkdir(parents=True)

    shutil.copy2(primary, image_dir / "primary.jpg")
    shutil.copy2(secondary, image_dir / "secondary.jpg")

    _run_colmap(
        [
            "feature_extractor",
            "--database_path",
            str(database_path),
            "--image_path",
            str(image_dir),
            "--ImageReader.single_camera_per_image",
            "1",
            "--SiftExtraction.max_num_features",
            "4096",
        ],
        cwd=workspace,
    )
    _run_colmap(
        [
            "exhaustive_matcher",
            "--database_path",
            str(database_path),
        ],
        cwd=workspace,
    )
    _run_colmap(
        [
            "mapper",
            "--database_path",
            str(database_path),
            "--image_path",
            str(image_dir),
            "--output_path",
            str(sparse_dir),
        ],
        cwd=workspace,
    )

    model_dir = sparse_dir / "0"
    images_path = model_dir / "images.txt"
    points_path = model_dir / "points3D.txt"
    if not images_path.exists() or not points_path.exists():
        raise RuntimeError("COLMAP mapper did not produce a sparse reconstruction")

    images = read_images_text(images_path)
    points3d = read_points3d_text(points_path)
    primary_image = next((image for image in images.values() if image.name.endswith("primary.jpg")), None)
    secondary_image = next((image for image in images.values() if image.name.endswith("secondary.jpg")), None)
    if primary_image is None or secondary_image is None:
        raise RuntimeError("COLMAP reconstruction missing one or both input images")

    points_primary, points_secondary, match_count = _shared_observations(
        primary_image,
        secondary_image,
    )
    homography, inlier_count = estimate_planar_homography(points_primary, points_secondary)
    if homography is None:
        raise RuntimeError("Unable to estimate homography from COLMAP observations")

    primary_bgr = cv2.imread(str(primary))
    secondary_bgr = cv2.imread(str(secondary))
    if primary_bgr is None or secondary_bgr is None:
        raise ValueError("Unable to read one or both images")

    primary_h, primary_w = primary_bgr.shape[:2]
    secondary_h, secondary_w = secondary_bgr.shape[:2]
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
        },
    )
