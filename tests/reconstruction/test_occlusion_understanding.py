from __future__ import annotations

from geomora_reconstruct.topology_inference import infer_topology_from_openings
from geomora_reconstruct.vlm_evidence import parse_architectural_evidence


def _evidence(*, confidence=0.9, likely=True):
    return parse_architectural_evidence(
        {
            "building_type": {"value": "historic_masonry", "confidence": 0.8},
            "facade": {
                "bbox": [0.05, 0.05, 0.95, 0.9],
                "visible_storeys": {"value": 1, "confidence": 0.75},
                "bay_count": {"value": 4, "confidence": 0.7},
                "repetition": {"value": "strong", "confidence": 0.9},
            },
            "opening_groups": [],
            "occlusions": [{
                "region": [0.52, 0.18, 0.68, 0.48], "likely_hidden_opening": likely,
                "confidence": confidence, "reason": "tree canopy",
            }],
            "uncertainties": [],
        },
        photo_id="occluded", provider="openai", model="fixture",
    )


def _regular_with_gap():
    return [
        {"id": "w1", "type": "window", "bbox": [0.15, 0.2, 0.25, 0.4]},
        {"id": "w2", "type": "window", "bbox": [0.35, 0.2, 0.45, 0.4]},
        {"id": "w4", "type": "window", "bbox": [0.75, 0.2, 0.85, 0.4]},
    ]


def test_occluded_gap_becomes_review_only_hidden_opening_hypothesis():
    topology, observed = infer_topology_from_openings(
        _regular_with_gap(), architectural_evidence=_evidence(),
    )
    hidden = topology["hidden_opening_hypotheses"]
    assert len(hidden) == 1
    assert abs((hidden[0]["bbox"][0] + hidden[0]["bbox"][2]) / 2 - 0.6) < 0.01
    assert hidden[0]["status"] == "hidden_hypothesis"
    assert hidden[0]["requires_confirmation"] is True
    assert hidden[0]["evidence"]["pattern_members"] == ["w1", "w2", "w4"]
    assert len(observed) == 3
    assert all(item["id"] != hidden[0]["id"] for item in observed)
    assert topology["occlusion_awareness"]["geometry_policy"] == "review_only_not_exported"


def test_low_confidence_or_non_hidden_occlusion_does_not_fill_gap():
    for evidence in (_evidence(confidence=0.4), _evidence(likely=False)):
        topology, _ = infer_topology_from_openings(_regular_with_gap(), architectural_evidence=evidence)
        assert topology["hidden_opening_hypotheses"] == []


def test_irregular_spacing_is_not_completed_behind_occlusion():
    irregular = [
        {"id": "w1", "type": "window", "bbox": [0.15, 0.2, 0.25, 0.4]},
        {"id": "w2", "type": "window", "bbox": [0.38, 0.2, 0.48, 0.4]},
        {"id": "w3", "type": "window", "bbox": [0.75, 0.2, 0.85, 0.4]},
    ]
    topology, _ = infer_topology_from_openings(irregular, architectural_evidence=_evidence())
    assert topology["hidden_opening_hypotheses"] == []
