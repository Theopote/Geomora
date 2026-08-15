from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class ColmapCamera:
    camera_id: int
    model: str
    width: int
    height: int
    params: list[float]


@dataclass
class ColmapImage:
    image_id: int
    qvec: tuple[float, float, float, float]
    tvec: tuple[float, float, float]
    camera_id: int
    name: str
    points2d: list[tuple[float, float, int]]


@dataclass
class ColmapPoint3D:
    point_id: int
    xyz: tuple[float, float, float]
    track: list[tuple[int, int]]


def _read_non_comment_lines(path: Path) -> list[str]:
    lines: list[str] = []
    with path.open(encoding="utf-8") as handle:
        for raw in handle:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            lines.append(line)
    return lines


def read_cameras_text(path: Path) -> dict[int, ColmapCamera]:
    cameras: dict[int, ColmapCamera] = {}
    for line in _read_non_comment_lines(path):
        parts = line.split()
        camera_id = int(parts[0])
        model = parts[1]
        width = int(parts[2])
        height = int(parts[3])
        params = [float(value) for value in parts[4:]]
        cameras[camera_id] = ColmapCamera(camera_id, model, width, height, params)
    return cameras


def read_images_text(path: Path) -> dict[int, ColmapImage]:
    lines = _read_non_comment_lines(path)
    images: dict[int, ColmapImage] = {}
    index = 0
    while index < len(lines):
        header = lines[index].split()
        index += 1
        image_id = int(header[0])
        qvec = tuple(float(value) for value in header[1:5])
        tvec = tuple(float(value) for value in header[5:8])
        camera_id = int(header[8])
        name = header[9]
        points2d: list[tuple[float, float, int]] = []
        if index < len(lines):
            observation_parts = lines[index].split()
            index += 1
            for offset in range(0, len(observation_parts), 3):
                x = float(observation_parts[offset])
                y = float(observation_parts[offset + 1])
                point3d_id = int(observation_parts[offset + 2])
                points2d.append((x, y, point3d_id))
        images[image_id] = ColmapImage(image_id, qvec, tvec, camera_id, name, points2d)
    return images


def read_points3d_text(path: Path) -> dict[int, ColmapPoint3D]:
    points: dict[int, ColmapPoint3D] = {}
    for line in _read_non_comment_lines(path):
        parts = line.split()
        point_id = int(parts[0])
        xyz = (float(parts[1]), float(parts[2]), float(parts[3]))
        track_parts = parts[8:]
        track: list[tuple[int, int]] = []
        for offset in range(0, len(track_parts), 2):
            track.append((int(track_parts[offset]), int(track_parts[offset + 1])))
        points[point_id] = ColmapPoint3D(point_id, xyz, track)
    return points
