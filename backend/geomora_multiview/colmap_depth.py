from __future__ import annotations

from pathlib import Path

import numpy as np

from .depth_preprocess import normalize_depth_map


def load_colmap_depth_map(path: str | Path) -> np.ndarray:
    depth_path = Path(path)
    if not depth_path.exists():
        raise FileNotFoundError(f"COLMAP depth map not found: {depth_path}")

    depth = np.load(depth_path)
    return normalize_depth_map(depth.astype(np.float32))
