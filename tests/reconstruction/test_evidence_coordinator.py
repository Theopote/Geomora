from __future__ import annotations

from geomora_reconstruct.topology_inference import infer_topology_from_openings
from geomora_reconstruct.export import detection_to_prediction
from geomora_reconstruct.understanding.coordinator import reconcile_count
from geomora_reconstruct.vlm_evidence import parse_architectural_evidence
from geomora_detect.models import DetectionResult


def evidence(*, storeys: int, storey_confidence: float, bays: int, bay_confidence: float):
    return parse_architectural_evidence(
        {
            "building_type": {"value": "historic_masonry", "confidence": 0.8},
            "facade": {
                "bbox": [0.05, 0.05, 0.95, 0.95],
                "visible_storeys": {"value": storeys, "confidence": storey_confidence},
                "bay_count": {"value": bays, "confidence": bay_confidence},
                "repetition": {"value": "strong", "confidence": 0.8},
            },
            "opening_groups": [],
            "occlusions": [],
            "uncertainties": [],
        },
        photo_id="test",
        provider="openai",
        model="fixture",
    )


def test_agreement_combines_confidence():
    decision = reconcile_count("storey_count", cv_value=3, cv_confidence=0.7, vlm_value=3, vlm_confidence=0.8)
    assert decision.value == 3
    assert decision.source == "cv+vlm_agreement"
    assert decision.confidence > 0.9
    assert decision.conflict is False


def test_vlm_only_overrides_weak_geometry_when_high_confidence():
    decision = reconcile_count("storey_count", cv_value=1, cv_confidence=0.4, vlm_value=3, vlm_confidence=0.9)
    assert decision.value == 3
    assert decision.source == "vlm_high_confidence"


def test_ambiguous_conflict_preserves_geometric_count():
    decision = reconcile_count("bay_count", cv_value=4, cv_confidence=0.72, vlm_value=6, vlm_confidence=0.82)
    assert decision.value == 4
    assert decision.source == "cv_geometry"
    assert decision.conflict is True


def test_sparse_openings_use_high_confidence_vlm_but_keep_uncertainty():
    openings = [
        {"id": "w1", "type": "window", "bbox": [0.2, 0.5, 0.35, 0.75]},
    ]
    topology, enriched = infer_topology_from_openings(
        openings,
        architectural_evidence=evidence(storeys=3, storey_confidence=0.93, bays=4, bay_confidence=0.91),
    )
    assert topology["storey_count"] == 3
    assert topology["bay_count"] == 4
    assert topology["method"] == "understanding_v0.2_evidence"
    assert any("unobserved_structure" in item for item in topology["uncertainties"])
    assert enriched[0]["storey"] == 1


def test_strong_cv_conflict_is_reported_without_vlm_override():
    openings = [
        {"id": "w21", "type": "window", "bbox": [0.1, 0.1, 0.25, 0.3]},
        {"id": "w22", "type": "window", "bbox": [0.6, 0.1, 0.75, 0.3]},
        {"id": "w11", "type": "window", "bbox": [0.1, 0.6, 0.25, 0.8]},
        {"id": "w12", "type": "window", "bbox": [0.6, 0.6, 0.75, 0.8]},
    ]
    topology, _ = infer_topology_from_openings(
        openings,
        architectural_evidence=evidence(storeys=4, storey_confidence=0.8, bays=5, bay_confidence=0.8),
    )
    assert topology["storey_count"] == 2
    assert topology["bay_count"] == 2
    assert any("storey_count_conflict" in item for item in topology["uncertainties"])
    coordination = topology.get("evidence_coordination")
    assert coordination is not None


def test_zero_cv_detections_still_produce_uncertain_vlm_topology():
    detection = DetectionResult(
        method="empty",
        confidence=0.1,
        image_width=1000,
        image_height=800,
        elements=[],
    )
    payload = detection_to_prediction(
        "test",
        detection,
        architectural_evidence=evidence(
            storeys=3,
            storey_confidence=0.94,
            bays=5,
            bay_confidence=0.92,
        ),
    )
    assert payload["topology"]["storey_count"] == 3
    assert payload["topology"]["bay_count"] == 5
    assert "no_openings" in payload["topology"]["uncertainties"]
    assert payload["openings"] == []
