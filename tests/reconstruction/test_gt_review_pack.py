from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND = REPO_ROOT / "backend"
PACK_DIR = REPO_ROOT / "tests" / "reconstruction" / "review_pack"
EXPORT_SCRIPT = BACKEND / "scripts" / "export_gt_review_pack.py"
IMPORT_SCRIPT = BACKEND / "scripts" / "import_gt_review_pack.py"


def _python() -> str:
    venv = BACKEND / ".venv" / "Scripts" / "python.exe"
    return str(venv if venv.exists() else sys.executable)


def test_export_gt_review_pack_generates_index_and_images():
    subprocess.run([_python(), str(EXPORT_SCRIPT)], check=True, cwd=BACKEND)
    index = PACK_DIR / "index.html"
    assert index.exists()
    html = index.read_text(encoding="utf-8")
    assert "window.PACK_DATA" in html
    assert "photo_01" in html
    assert (PACK_DIR / "images" / "photo_01.jpg").exists()


def test_import_gt_review_pack_dry_run(tmp_path):
    sample = {
        "schema_version": "reconstruction-metrics-v1",
        "photo_id": "photo_01",
        "annotation_status": "reviewed_v1",
        "review_rounds": 1,
        "facade_bbox": [0.1, 0.04, 0.9, 0.98],
        "facade": {"width": 1.0, "height": 1.0},
        "topology": {"storey_count": 2, "bay_count": 2},
        "openings": [
            {"id": "w11", "type": "window", "bbox": [0.1, 0.2, 0.2, 0.4], "storey": 1, "bay": 1}
        ],
        "pattern_groups": [],
        "metric_anchors": [],
    }
    exports = tmp_path / "exports"
    exports.mkdir()
    (exports / "photo_01.json").write_text(json.dumps(sample), encoding="utf-8")

    result = subprocess.run(
        [_python(), str(IMPORT_SCRIPT), "--exports", str(exports), "--dry-run"],
        cwd=BACKEND,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "DRY-RUN" in result.stdout
