#!/usr/bin/env python3
"""Download optional ONNX depth models for Geomora Phase 6.5++."""

from __future__ import annotations

import argparse
import sys
import urllib.request
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
MODELS_DIR = BACKEND_ROOT / "models"

MODEL_SPECS = {
    "da2": {
        "label": "Depth Anything V2 Small",
        "files": [
            {
                "url": "https://huggingface.co/onnx-community/depth-anything-v2-small-ONNX/resolve/main/onnx/model.onnx",
                "target": "depth_anything_v2_small.onnx",
            },
            {
                "url": "https://huggingface.co/onnx-community/depth-anything-v2-small-ONNX/resolve/main/onnx/model.onnx_data",
                "target": "depth_anything_v2_small.onnx_data",
            },
        ],
    },
    "da2-q4": {
        "label": "Depth Anything V2 Small (Q4)",
        "files": [
            {
                "url": "https://huggingface.co/onnx-community/depth-anything-v2-small-ONNX/resolve/main/onnx/model_q4.onnx",
                "target": "depth_anything_v2_small_q4.onnx",
            },
            {
                "url": "https://huggingface.co/onnx-community/depth-anything-v2-small-ONNX/resolve/main/onnx/model_q4.onnx_data",
                "target": "depth_anything_v2_small_q4.onnx_data",
            },
        ],
    },
    "midas": {
        "label": "MiDaS v2.1 Small",
        "files": [
            {
                "url": "https://huggingface.co/onnx-community/midas-vision-small/resolve/main/onnx/model.onnx",
                "target": "midas_v21_small.onnx",
            },
        ],
    },
}


def download(url: str, destination: Path) -> None:
    print(f"Downloading {url}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(url, destination)


def download_model(key: str) -> int:
    spec = MODEL_SPECS[key]
    print(f"=== {spec['label']} ===")
    for item in spec["files"]:
        target = MODELS_DIR / item["target"]
        if target.exists():
            print(f"Already exists: {target}")
            continue
        try:
            download(item["url"], target)
            print(f"Saved: {target}")
        except Exception as error:  # pragma: no cover - network fallback
            print(f"Failed: {error}")
            return 1
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Download Geomora depth ONNX models")
    parser.add_argument(
        "--model",
        choices=["all", "da2", "da2-q4", "midas"],
        default="all",
        help="Which model bundle to download (default: all)",
    )
    args = parser.parse_args()

    keys = list(MODEL_SPECS.keys()) if args.model == "all" else [args.model]
    exit_code = 0
    for key in keys:
        if download_model(key) != 0:
            exit_code = 1
    if exit_code != 0:
        print("Some downloads failed. You can also place ONNX files manually in backend/models/.")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
