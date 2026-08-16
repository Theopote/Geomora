from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np

from geomora_detect.overlays import draw_overlay, encode_overlay_jpeg
from geomora_detect.pipeline import detect_facade

from .colmap_common import colmap_available
from .colmap_dense import register_views_colmap_dense
from .colmap_sparse import register_views_colmap
from .depth import DEPTH_METHODS, compute_depth_map, depth_capabilities
from .feature_match import (
    detect_and_match,
    estimate_planar_homography,
    homography_confidence,
    load_gray,
)
from .fusion import fuse_elements, transform_element
from .models import FusionResult, MultiviewResult, ViewRegistration
from .onnx_providers import onnx_device_info

REGISTER_METHODS = (
    "auto",
    "feature_homography_v1",
    "colmap_sparse_v1",
    "colmap_dense_v1",
)


def resolve_register_method(method: str) -> str:
    normalized = (method or "auto").strip().lower()
    if normalized == "auto":
        return "colmap_sparse_v1" if colmap_available() else "feature_homography_v1"
    if normalized not in REGISTER_METHODS:
        raise ValueError(f"Unsupported registration method: {method}")
    if normalized in {"colmap_sparse_v1", "colmap_dense_v1"} and not colmap_available():
        raise ValueError("COLMAP executable not found on PATH")
    return normalized


def register_views_orb(primary_path: str, secondary_path: str) -> MultiviewResult:
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
            "registration_backend": "orb",
            "detector": "ORB",
            "matcher": "BF_HAMMING_CROSSCHECK",
            "ransac_threshold": 5.0,
        },
    )


def register_views(primary_path: str, secondary_path: str, *, method: str = "auto") -> MultiviewResult:
    resolved = resolve_register_method(method)
    if resolved == "colmap_dense_v1":
        return register_views_colmap_dense(primary_path, secondary_path)
    if resolved == "colmap_sparse_v1":
        return register_views_colmap(primary_path, secondary_path)
    return register_views_orb(primary_path, secondary_path)


def parse_homography(raw: str | list | None) -> np.ndarray | None:
    if raw is None:
        return None
    if isinstance(raw, list):
        data = raw
    else:
        text = raw.strip()
        if not text:
            return None
        data = json.loads(text)
    matrix = np.array(data, dtype=np.float64)
    if matrix.shape != (3, 3):
        raise ValueError("homography must be a 3x3 matrix")
    return matrix


def fuse_openings(
    primary_path: str,
    secondary_path: str,
    *,
    homography: list[list[float]] | str | None = None,
    detect_method: str = "auto",
    depth_method: str = "auto",
    register_method: str = "auto",
    return_overlay: bool = True,
) -> FusionResult:
    primary = Path(primary_path)
    secondary = Path(secondary_path)
    if not primary.exists():
        raise ValueError(f"Primary image not found: {primary_path}")
    if not secondary.exists():
        raise ValueError(f"Secondary image not found: {secondary_path}")

    registration = None
    homography_matrix = parse_homography(homography)
    if homography_matrix is None:
        registration = register_views(str(primary), str(secondary), method=register_method)
        if registration.homography is None:
            raise ValueError("Unable to estimate homography between views")
        homography_matrix = np.array(registration.homography, dtype=np.float64)

    primary_bgr = cv2.imread(str(primary))
    secondary_bgr = cv2.imread(str(secondary))
    if primary_bgr is None or secondary_bgr is None:
        raise ValueError("Unable to read one or both images")

    primary_h, primary_w = primary_bgr.shape[:2]
    secondary_h, secondary_w = secondary_bgr.shape[:2]
    colmap_depth_path = None
    if registration and registration.debug:
        colmap_depth_path = registration.debug.get("depth_map_path")

    depth_map, resolved_depth_method = compute_depth_map(
        primary_bgr,
        method=depth_method,
        colmap_depth_path=colmap_depth_path,
    )

    primary_detection = detect_facade(str(primary), method=detect_method, return_overlay=False)
    secondary_detection = detect_facade(str(secondary), method=detect_method, return_overlay=False)

    transformed_secondary = [
        transform_element(
            element,
            homography_matrix,
            secondary_w,
            secondary_h,
            primary_w,
            primary_h,
        )
        for element in secondary_detection.elements
    ]

    combined = list(primary_detection.elements) + transformed_secondary
    fused_elements = fuse_elements(combined, depth_map, primary_w, primary_h)

    confidence = (
        sum(element.confidence for element in fused_elements) / len(fused_elements)
        if fused_elements
        else 0.35
    )

    overlay_base64 = None
    if return_overlay:
        overlay = draw_overlay(primary_bgr, fused_elements)
        overlay_base64 = encode_overlay_jpeg(overlay)

    return FusionResult(
        method="multiview_fusion_v1",
        confidence=confidence,
        image_width=primary_w,
        image_height=primary_h,
        elements=fused_elements,
        overlay_base64=overlay_base64,
        registration=registration.to_dict() if registration else None,
        homography=homography_matrix.astype(float).tolist(),
        debug={
            "detect_method": detect_method,
            "depth_method": resolved_depth_method,
            "register_method": registration.method if registration else "provided_homography",
            "primary_elements": len(primary_detection.elements),
            "secondary_elements": len(secondary_detection.elements),
            "fused_elements": len(fused_elements),
            "colmap_dense_vertices": registration.debug.get("dense_vertices") if registration else None,
            "colmap_dense_status": registration.debug.get("dense_status") if registration else None,
        },
    )


def multiview_capabilities() -> dict[str, object]:
    depth_info = depth_capabilities()
    return {
        "colmap_available": colmap_available(),
        "depth_models": depth_info["depth_models"],
        "depth_auto": depth_info["depth_auto"],
        "onnx_device": depth_info.get("onnx_device", onnx_device_info()),
        "register_methods": list(REGISTER_METHODS),
        "depth_methods": list(DEPTH_METHODS),
        "midas_available": depth_info["depth_models"].get("midas_v21_v1", False),
        "depth_anything_available": depth_info["depth_models"].get("depth_anything_v2_small_v1", False),
        "depth_anything_q4_available": depth_info["depth_models"].get("depth_anything_v2_small_q4_v1", False),
        "marigold_available": depth_info["depth_models"].get("marigold_v1_1_v1", False),
    }
