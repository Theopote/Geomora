from __future__ import annotations

import struct
from pathlib import Path

import numpy as np

from .colmap_model import ColmapCamera, ColmapImage, ColmapPoint3D


def qvec_to_rotation_matrix(qvec: tuple[float, float, float, float]) -> np.ndarray:
    qw, qx, qy, qz = qvec
    return np.array(
        [
            [1 - 2 * qy * qy - 2 * qz * qz, 2 * qx * qy - 2 * qz * qw, 2 * qx * qz + 2 * qy * qw],
            [2 * qx * qy + 2 * qz * qw, 1 - 2 * qx * qx - 2 * qz * qz, 2 * qy * qz - 2 * qx * qw],
            [2 * qx * qz - 2 * qy * qw, 2 * qy * qz + 2 * qx * qw, 1 - 2 * qx * qx - 2 * qy * qy],
        ],
        dtype=np.float64,
    )


def project_points(
    points_xyz: np.ndarray,
    image: ColmapImage,
    camera: ColmapCamera,
) -> tuple[np.ndarray, np.ndarray]:
    rotation = qvec_to_rotation_matrix(image.qvec)
    translation = np.array(image.tvec, dtype=np.float64)
    camera_points = (rotation @ points_xyz.T).T + translation
    depths = camera_points[:, 2]
    valid = depths > 1e-6
    if camera.model != "PINHOLE" or len(camera.params) < 4:
        raise ValueError(f"Unsupported COLMAP camera model: {camera.model}")

    fx, fy, cx, cy = camera.params[:4]
    u = fx * camera_points[:, 0] / depths + cx
    v = fy * camera_points[:, 1] / depths + cy
    pixels = np.stack([u, v], axis=1)
    return pixels, depths


def rasterize_depth_from_points(
    points3d: dict[int, ColmapPoint3D],
    image: ColmapImage,
    camera: ColmapCamera,
    image_height: int,
    image_width: int,
) -> np.ndarray:
    if not points3d:
        return np.zeros((image_height, image_width), dtype=np.float32)

    xyz = np.array([point.xyz for point in points3d.values()], dtype=np.float64)
    pixels, depths = project_points(xyz, image, camera)

    depth_map = np.zeros((image_height, image_width), dtype=np.float32)
    z_buffer = np.full((image_height, image_width), np.inf, dtype=np.float32)

    for (u, v), depth in zip(pixels, depths):
        if depth <= 0:
            continue
        x = int(round(u))
        y = int(round(v))
        if x < 0 or y < 0 or x >= image_width or y >= image_height:
            continue
        if depth < z_buffer[y, x]:
            z_buffer[y, x] = depth
            depth_map[y, x] = depth

    if not np.isfinite(z_buffer).any():
        return depth_map

    observed = depth_map > 0
    if not observed.any():
        return depth_map

    min_depth = depth_map[observed].min()
    max_depth = depth_map[observed].max()
    normalized = np.zeros_like(depth_map)
    normalized[observed] = 1.0 - ((depth_map[observed] - min_depth) / (max_depth - min_depth + 1e-6))
    return np.clip(normalized, 0.0, 1.0)


def read_ply_vertex_count(path: Path) -> int:
    if not path.exists():
        return 0

    with path.open("rb") as handle:
        header_lines: list[str] = []
        while True:
            line = handle.readline()
            if not line:
                break
            decoded = line.decode("ascii", errors="ignore").strip()
            header_lines.append(decoded)
            if decoded == "end_header":
                break

        vertex_count = 0
        binary = False
        for line in header_lines:
            if line.startswith("element vertex"):
                vertex_count = int(line.split()[-1])
            if "format binary" in line:
                binary = True

        if vertex_count == 0:
            return 0
        if not binary:
            return vertex_count

        # Skip vertex records after header for a rough sanity read.
        position = handle.tell()
        record_size = 12  # xyz float32
        handle.seek(0, 2)
        payload_bytes = handle.tell() - position
        if payload_bytes <= 0:
            return vertex_count
        return min(vertex_count, payload_bytes // record_size)


def read_ply_vertices(path: Path, max_vertices: int = 250_000) -> np.ndarray:
    if not path.exists():
        return np.empty((0, 3), dtype=np.float64)

    with path.open("rb") as handle:
        header_lines: list[str] = []
        while True:
            line = handle.readline()
            if not line:
                break
            decoded = line.decode("ascii", errors="ignore").strip()
            header_lines.append(decoded)
            if decoded == "end_header":
                break

        vertex_count = 0
        binary = False
        for line in header_lines:
            if line.startswith("element vertex"):
                vertex_count = int(line.split()[-1])
            if "format binary_little_endian" in line:
                binary = True

        if vertex_count == 0:
            return np.empty((0, 3), dtype=np.float64)

        if not binary:
            vertices: list[list[float]] = []
            for _ in range(min(vertex_count, max_vertices)):
                parts = handle.readline().decode("ascii", errors="ignore").split()
                if len(parts) < 3:
                    break
                vertices.append([float(parts[0]), float(parts[1]), float(parts[2])])
            return np.array(vertices, dtype=np.float64)

        count = min(vertex_count, max_vertices)
        raw = handle.read(count * 12)
        if len(raw) < 12:
            return np.empty((0, 3), dtype=np.float64)
        vertices = struct.unpack("<" + "f" * (len(raw) // 4), raw)
        return np.array(vertices, dtype=np.float64).reshape(-1, 3)
