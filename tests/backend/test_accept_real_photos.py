from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np
import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[2] / "backend"
SCRIPT = BACKEND_ROOT / "scripts" / "accept_real_photos.py"


def _write_rectified_fixture(path: Path) -> None:
    image = np.full((600, 800, 3), (210, 210, 210), dtype=np.uint8)
    cv2.rectangle(image, (20, 40), (780, 560), (175, 168, 158), -1)
    for x1, y1, x2, y2 in (
        (80, 140, 200, 320),
        (240, 140, 360, 320),
        (400, 140, 520, 320),
        (560, 140, 680, 320),
    ):
        cv2.rectangle(image, (x1, y1), (x2, y2), (35, 35, 120), -1)
    cv2.rectangle(image, (10, 330), (70, 560), (25, 25, 90), -1)
    cv2.imwrite(str(path), image)


@pytest.mark.skipif(not SCRIPT.exists(), reason="accept_real_photos.py missing")
def test_accept_real_photos_cli_passes_on_synthetic(tmp_path):
    images_dir = tmp_path / "rectified"
    images_dir.mkdir()
    _write_rectified_fixture(images_dir / "sample.jpg")

    report = tmp_path / "report.json"
    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--images",
            str(images_dir),
            "--method",
            "auto",
            "--min-windows",
            "3",
            "--report",
            str(report),
        ],
        cwd=BACKEND_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert report.exists()
    assert "PASS" in completed.stdout
