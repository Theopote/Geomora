from __future__ import annotations

from pathlib import Path

import numpy as np

from .colmap_common import (
    colmap_available,
    copy_view_images,
    load_primary_secondary_images,
    prepare_workspace,
    read_image_shape,
    run_colmap,
    run_sparse_reconstruction,
)
from .colmap_geometry import (
    rasterize_depth_from_points,
    read_ply_vertex_count,
    read_ply_vertices,
)
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


def _run_dense_pipeline(workspace, sparse_model_dir: Path) -> tuple[Path | None, str]:
    dense_workspace = workspace.dense_dir
    try:
        run_colmap(
            [
                "image_undistorter",
                "--image_path",
                str(workspace.image_dir),
                "--input_path",
                str(sparse_model_dir),
                "--output_path",
                str(dense_workspace),
                "--output_type",
                "COLMAP",
            ],
            cwd=workspace.root,
        )
        run_colmap(
            [
                "patch_match_stereo",
                "--workspace_path",
                str(dense_workspace),
                "--workspace_format",
                "COLMAP",
            ],
            cwd=workspace.root,
        )
        fused_path = dense_workspace / "fused.ply"
        run_colmap(
            [
                "stereo_fusion",
                "--workspace_path",
                str(dense_workspace),
                "--workspace_format",
                "COLMAP",
                "--output_path",
                str(fused_path),
            ],
            cwd=workspace.root,
        )
        if fused_path.exists():
            return fused_path, "dense"
        return None, "dense_failed"
    except RuntimeError as error:
        return None, f"dense_failed:{error}"


def _save_depth_map(depth_map: np.ndarray, workspace_root: Path) -> str:
    path = workspace_root / "primary_depth.npy"
    np.save(path, depth_map.astype(np.float32))
    return str(path)


def register_views_colmap_dense(primary_path: str, secondary_path: str) -> MultiviewResult:
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
    cameras = read_cameras_text(sparse_model_dir / "cameras.txt")

    points_primary, points_secondary, match_count = _shared_observations(primary_image, secondary_image)
    homography, inlier_count = estimate_planar_homography(points_primary, points_secondary)
    if homography is None:
        raise RuntimeError("Unable to estimate homography from COLMAP observations")

    primary_h, primary_w = read_image_shape(primary)
    secondary_h, secondary_w = read_image_shape(secondary)
    primary_camera = cameras[primary_image.camera_id]

    fused_path, dense_status = _run_dense_pipeline(workspace, sparse_model_dir)
    dense_vertices = 0
    if fused_path is not None:
        dense_vertices = read_ply_vertex_count(fused_path)
        fused_xyz = read_ply_vertices(fused_path)
        if fused_xyz.size > 0:
            from .colmap_geometry import project_points

            pixels, depths = project_points(fused_xyz, primary_image, primary_camera)
            depth_map = np.zeros((primary_h, primary_w), dtype=np.float32)
            z_buffer = np.full((primary_h, primary_w), np.inf, dtype=np.float32)
            for (u, v), depth in zip(pixels, depths):
                if depth <= 0:
                    continue
                x = int(round(u))
                y = int(round(v))
                if x < 0 or y < 0 or x >= primary_w or y >= primary_h:
                    continue
                if depth < z_buffer[y, x]:
                    z_buffer[y, x] = depth
                    depth_map[y, x] = depth
            observed = depth_map > 0
            if observed.any():
                min_depth = depth_map[observed].min()
                max_depth = depth_map[observed].max()
                depth_map[observed] = 1.0 - ((depth_map[observed] - min_depth) / (max_depth - min_depth + 1e-6))
            depth_map = np.clip(depth_map, 0.0, 1.0)
        else:
            depth_map = rasterize_depth_from_points(points3d, primary_image, primary_camera, primary_h, primary_w)
    else:
        depth_map = rasterize_depth_from_points(points3d, primary_image, primary_camera, primary_h, primary_w)

    depth_map_path = _save_depth_map(depth_map, workspace.root)
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
        method="colmap_dense_v1",
        confidence=confidence,
        match_count=match_count,
        inlier_count=inlier_count,
        views=views,
        homography=homography_list,
        debug={
            "registration_backend": "colmap_dense",
            "dense_status": dense_status,
            "dense_vertices": dense_vertices,
            "sparse_points": len(points3d),
            "depth_map_path": depth_map_path,
            "workspace": str(workspace.root),
            "primary_pose": {
                "qvec": list(primary_image.qvec),
                "tvec": list(primary_image.tvec),
            },
            "secondary_pose": {
                "qvec": list(secondary_image.qvec),
                "tvec": list(secondary_image.tvec),
            },
        },
    )
