from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from geomora_reconstruct.metric_anchors import anchor_axis, apply_metric_anchors_to_gt, derive_metric_from_anchors

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND = REPO_ROOT / "backend"
IMPORT_ANCHORS = BACKEND / "scripts" / "import_metric_anchors.py"


def _python() -> str:
    venv = BACKEND / ".venv" / "Scripts" / "python.exe"
    return str(venv if venv.exists() else sys.executable)


def test_derive_metric_from_horizontal_anchor():
    anchors = [
        {
            "id": "anchor_facade_width",
            "type": "user_distance",
            "start": [0.05, 0.9],
            "end": [0.95, 0.9],
            "distance_mm": 12400,
        }
    ]
    metric = derive_metric_from_anchors(anchors, topology={"storey_count": 2})
    assert metric == {"facade_width_mm": 12400.0}


def test_anchor_axis_does_not_infer_semantics_from_id():
    anchor = {"id": "misleading_height_name", "type": "segment_distance", "property": "width", "start": [0.1, 0.2], "end": [0.3, 0.2]}
    assert anchor_axis(anchor) == "horizontal"


def test_segment_anchor_derives_scale_then_facade_dimension():
    anchors = [{
        "id": "anchor_001", "type": "segment_distance", "target": "window_03",
        "property": "width", "start": [0.2, 0.3], "end": [0.3, 0.3],
        "distance_mm": 1500, "priority": "hard",
    }]
    metric = derive_metric_from_anchors(
        anchors,
        topology={"storey_count": 2},
        facade_bbox=[0.1, 0.1, 0.9, 0.8],
    )
    assert metric["facade_width_mm"] == 12000.0
    assert "facade_height_mm" not in metric


def test_storey_height_anchor_derives_vertical_scale_and_direct_storey_height():
    anchors = [{
        "id": "storey", "type": "storey_height", "target": "storey_1",
        "property": "storey_height", "start": [0.2, 0.5], "end": [0.2, 0.7],
        "distance_mm": 3200, "priority": "hard",
    }]
    metric = derive_metric_from_anchors(anchors, topology={"storey_count": 2}, facade_bbox=[0.1, 0.3, 0.9, 0.7])
    assert metric == {"facade_height_mm": 6400.0, "storey_height_mm": 3200.0}


def test_apply_metric_anchors_to_gt_writes_metric_block():
    gt = {
        "photo_id": "photo_11",
        "topology": {"storey_count": 2, "bay_count": 7},
        "metric_anchors": [
            {
                "id": "anchor_facade_width",
                "type": "user_distance",
                "status": "pending_survey",
                "start": [0.05, 0.9],
                "end": [0.95, 0.9],
                "distance_mm": 12600,
            }
        ],
    }
    merged = apply_metric_anchors_to_gt(gt)
    assert merged["metric"]["facade_width_mm"] == 12600.0
    assert merged["metric_anchors"][0]["status"] == "surveyed"


def test_merge_anchor_updates_into_existing_gt(tmp_path):
    gt_dir = tmp_path / "ground_truth"
    gt_dir.mkdir()
    gt = {
        "schema_version": "reconstruction-metrics-v1",
        "photo_id": "photo_19",
        "topology": {"storey_count": 2, "bay_count": 9},
        "metric_anchors": [
            {
                "id": "anchor_facade_width",
                "type": "user_distance",
                "status": "pending_survey",
                "start": [0.06, 0.94],
                "end": [0.94, 0.94],
                "distance_mm": None,
            }
        ],
    }
    (gt_dir / "photo_19.json").write_text(json.dumps(gt), encoding="utf-8")

    anchor_file = tmp_path / "photo_19.json"
    anchor_file.write_text(
        json.dumps({"photo_id": "photo_19", "anchor_id": "anchor_facade_width", "distance_mm": 9800}),
        encoding="utf-8",
    )

    result = subprocess.run(
        [_python(), str(IMPORT_ANCHORS), str(anchor_file), "--ground-truth-dir", str(gt_dir)],
        cwd=BACKEND,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr

    merged = json.loads((gt_dir / "photo_19.json").read_text(encoding="utf-8"))
    assert merged["metric"]["facade_width_mm"] == 9800.0
    assert merged["metric_anchors"][0]["status"] == "surveyed"


def test_import_gt_review_pack_applies_metric_block(tmp_path):
    exports = tmp_path / "exports"
    gt_dir = tmp_path / "ground_truth"
    exports.mkdir()
    gt_dir.mkdir()
    payload = {
        "schema_version": "reconstruction-metrics-v1",
        "photo_id": "photo_11",
        "annotation_status": "reviewed_v1",
        "review_rounds": 1,
        "facade_bbox": [0.0, 0.0, 1.0, 1.0],
        "facade": {"width": 1.0, "height": 1.0},
        "topology": {"storey_count": 2, "bay_count": 7},
        "openings": [
            {"id": "w11", "type": "window", "bbox": [0.1, 0.2, 0.2, 0.4], "storey": 1, "bay": 1}
        ],
        "pattern_groups": [],
        "metric_anchors": [
            {
                "id": "anchor_facade_width",
                "type": "user_distance",
                "status": "surveyed",
                "start": [0.05, 0.9],
                "end": [0.95, 0.9],
                "distance_mm": 12000,
            }
        ],
    }
    (exports / "photo_11.json").write_text(json.dumps(payload), encoding="utf-8")

    import_script = BACKEND / "scripts" / "import_gt_review_pack.py"
    result = subprocess.run(
        [_python(), str(import_script), "--exports", str(exports), "--ground-truth-dir", str(gt_dir)],
        cwd=BACKEND,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    merged = json.loads((gt_dir / "photo_11.json").read_text(encoding="utf-8"))
    assert merged["metric"]["facade_width_mm"] == 12000.0
