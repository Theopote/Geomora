from __future__ import annotations

import json
from pathlib import Path

from geomora_reconstruct.metrics.gt_validator import validate_ground_truth


GT_DIR = Path(__file__).parent / "ground_truth"


def test_photo_19_detects_three_way_annotation_contradiction():
    truth = json.loads((GT_DIR / "photo_19.json").read_text(encoding="utf-8"))
    w291 = next(item for item in truth["openings"] if item["id"] == "w291")
    w291.update(storey=1, bay=1)
    truth["pattern_groups"][0]["members"].remove("w291")
    report = validate_ground_truth(truth)
    codes = {issue.code for issue in report.warnings}
    assert "spatial_storey_mismatch" in codes
    assert "probable_pattern_omission" in codes
    assert "annotation_count_mismatch" in codes
    mismatch = next(issue for issue in report.warnings if issue.code == "spatial_storey_mismatch")
    assert mismatch.details["suggested_storey"] == 2
    assert "w291" in mismatch.message
    assert report.valid is True
    assert report.gate_ready is False


def test_other_minimal_ground_truth_is_gate_ready():
    for photo_id in ("photo_01", "photo_11", "photo_16", "photo_18"):
        truth = json.loads((GT_DIR / f"{photo_id}.json").read_text(encoding="utf-8"))
        assert validate_ground_truth(truth).gate_ready, photo_id


def test_structural_errors_cover_ids_bbox_topology_and_anchors():
    truth = {
        "photo_id": "broken",
        "topology": {"storey_count": 1, "bay_count": 1},
        "openings": [
            {"id": "same", "type": "window", "bbox": [0.1, 0.1, 0.3, 0.3], "storey": 2, "bay": 1},
            {"id": "same", "type": "window", "bbox": [0.1, 0.1, 0.3, 0.3], "storey": 1, "bay": 1},
        ],
        "pattern_groups": [{"id": "p", "members": ["missing"]}],
        "metric_anchors": [{"id": "width", "status": "surveyed", "start": [0.2, 0.2], "end": [0.2, 0.2], "distance_mm": None}],
    }
    report = validate_ground_truth(truth)
    codes = {issue.code for issue in report.errors}
    assert {"invalid_storey_id", "duplicate_element_id", "duplicate_bbox", "unknown_pattern_member", "zero_length_anchor", "surveyed_anchor_missing_distance"} <= codes
    assert report.valid is False
