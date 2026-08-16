"""Download MobileSAM ONNX encoder + decoder into backend/models/.

Source: https://huggingface.co/Heliosoph/sam-onnx (Apache-2.0)

Usage:
  cd backend
  .venv\\Scripts\\pip install httpx
  .venv\\Scripts\\python scripts\\download_mobile_sam_onnx.py
"""

from __future__ import annotations

import argparse
import sys
import time
import urllib.request
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
MODELS_DIR = BACKEND_ROOT / "models"

HF_BASE = "https://huggingface.co/Heliosoph/sam-onnx/resolve/main"

DEFAULT_FILES = {
    "mobile_sam_image_encoder.onnx": f"{HF_BASE}/mobile_sam_image_encoder.onnx",
    "sam_mask_decoder_single.onnx": f"{HF_BASE}/sam_mask_decoder_single.onnx",
}


def download_file_httpx(url: str, destination: Path) -> bool:
    try:
        import httpx
    except ImportError:
        return False

    print(f"Downloading {destination.name} (httpx) ...")
    with httpx.stream("GET", url, follow_redirects=True, timeout=600.0) as response:
        response.raise_for_status()
        total = int(response.headers.get("content-length", 0))
        downloaded = 0
        with destination.open("wb") as handle:
            for chunk in response.iter_bytes(chunk_size=1024 * 1024):
                handle.write(chunk)
                downloaded += len(chunk)
                if total:
                    pct = downloaded * 100 // total
                    print(f"  {pct}% ({downloaded // (1024 * 1024)} MB)", end="\r")
    print(f"  -> {destination}")
    return True


def download_file_urlopen(url: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    print(f"Downloading {destination.name} (urllib) ...")
    with urllib.request.urlopen(url, timeout=600) as response:
        total = int(response.headers.get("Content-Length", 0))
        chunk_size = 1024 * 1024
        downloaded = 0
        with destination.open("wb") as handle:
            while True:
                chunk = response.read(chunk_size)
                if not chunk:
                    break
                handle.write(chunk)
                downloaded += len(chunk)
                if total:
                    pct = downloaded * 100 // total
                    print(f"  {pct}% ({downloaded // (1024 * 1024)} MB)", end="\r")
    print(f"  -> {destination}")


def download_file(url: str, destination: Path, retries: int = 3) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    for attempt in range(1, retries + 1):
        try:
            if download_file_httpx(url, destination):
                return
            download_file_urlopen(url, destination)
            return
        except Exception as error:  # pragma: no cover - network flake
            if attempt == retries:
                raise
            print(f"  retry {attempt}/{retries - 1}: {error}")
            time.sleep(2 * attempt)


def main() -> None:
    parser = argparse.ArgumentParser(description="Download MobileSAM ONNX models")
    parser.add_argument("--force", action="store_true", help="Re-download existing files")
    args = parser.parse_args()

    for filename, url in DEFAULT_FILES.items():
        destination = MODELS_DIR / filename
        if destination.exists() and not args.force:
            print(f"Skip existing: {destination}")
            continue
        download_file(url, destination)

    print("Done. Verify with:")
    print("  .venv\\Scripts\\python -c \"from geomora_detect.sam_onnx import mobile_sam_available; print(mobile_sam_available())\"")


if __name__ == "__main__":
    sys.path.insert(0, str(BACKEND_ROOT))
    main()
