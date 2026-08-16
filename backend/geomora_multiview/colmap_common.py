from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

import cv2

from .colmap_model import ColmapImage, read_images_text, read_points3d_text


def colmap_available() -> bool:
    return shutil.which("colmap") is not None


def run_colmap(args: list[str], *, cwd: Path) -> None:
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


@dataclass
class ColmapWorkspace:
    root: Path
    image_dir: Path
    database_path: Path
    sparse_dir: Path
    dense_dir: Path


def prepare_workspace(parent_dir: Path) -> ColmapWorkspace:
    workspace = parent_dir / "colmap_workspace"
    if workspace.exists():
        shutil.rmtree(workspace)

    image_dir = workspace / "images"
    sparse_dir = workspace / "sparse"
    dense_dir = workspace / "dense"
    image_dir.mkdir(parents=True)
    sparse_dir.mkdir(parents=True)
    dense_dir.mkdir(parents=True)

    return ColmapWorkspace(
        root=workspace,
        image_dir=image_dir,
        database_path=workspace / "database.db",
        sparse_dir=sparse_dir,
        dense_dir=dense_dir,
    )


def copy_view_images(workspace: ColmapWorkspace, primary: Path, secondary: Path) -> None:
    shutil.copy2(primary, workspace.image_dir / "primary.jpg")
    shutil.copy2(secondary, workspace.image_dir / "secondary.jpg")


def run_sparse_reconstruction(workspace: ColmapWorkspace) -> Path:
    run_colmap(
        [
            "feature_extractor",
            "--database_path",
            str(workspace.database_path),
            "--image_path",
            str(workspace.image_dir),
            "--ImageReader.single_camera_per_image",
            "1",
            "--SiftExtraction.max_num_features",
            "4096",
        ],
        cwd=workspace.root,
    )
    run_colmap(
        [
            "exhaustive_matcher",
            "--database_path",
            str(workspace.database_path),
        ],
        cwd=workspace.root,
    )
    run_colmap(
        [
            "mapper",
            "--database_path",
            str(workspace.database_path),
            "--image_path",
            str(workspace.image_dir),
            "--output_path",
            str(workspace.sparse_dir),
        ],
        cwd=workspace.root,
    )

    model_dir = workspace.sparse_dir / "0"
    if not (model_dir / "images.txt").exists() or not (model_dir / "points3D.txt").exists():
        raise RuntimeError("COLMAP mapper did not produce a sparse reconstruction")
    return model_dir


def load_primary_secondary_images(model_dir: Path) -> tuple[dict, dict, ColmapImage, ColmapImage]:
    images = read_images_text(model_dir / "images.txt")
    points3d = read_points3d_text(model_dir / "points3D.txt")
    primary_image = next((image for image in images.values() if image.name.endswith("primary.jpg")), None)
    secondary_image = next((image for image in images.values() if image.name.endswith("secondary.jpg")), None)
    if primary_image is None or secondary_image is None:
        raise RuntimeError("COLMAP reconstruction missing one or both input images")
    return images, points3d, primary_image, secondary_image


def read_image_shape(path: Path) -> tuple[int, int]:
    image = cv2.imread(str(path))
    if image is None:
        raise ValueError(f"Unable to read image: {path}")
    height, width = image.shape[:2]
    return height, width
