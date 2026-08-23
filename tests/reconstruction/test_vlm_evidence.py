from __future__ import annotations

import json

import pytest

from geomora_reconstruct.observations.models import ObservationKind
from geomora_reconstruct.observations.vlm_adapter import vlm_evidence_to_observations
from geomora_reconstruct.observations import ObservationGraphBuilder, yolo_to_observations
from geomora_reconstruct.vlm_evidence import (
    parse_architectural_evidence,
    read_evidence_cache,
    write_evidence_cache,
)


SAMPLE = {
    "building_type": {"value": "historic_masonry", "confidence": 0.82},
    "facade": {
        "bbox": [0.05, 0.04, 0.94, 0.91],
        "visible_storeys": {"value": 3, "confidence": 0.88},
        "bay_count": {"value": 5, "confidence": 0.76},
        "repetition": {"value": "strong", "confidence": 0.84},
    },
    "opening_groups": [{"type": "window", "rows": 3, "columns": 5, "region": [0.1, 0.15, 0.9, 0.8], "confidence": 0.8}],
    "occlusions": [{"region": [0.0, 0.55, 0.2, 1.0], "likely_hidden_opening": True, "confidence": 0.61, "reason": "tree"}],
    "uncertainties": ["roof partly cropped"],
}


def test_parse_vlm_architectural_evidence_and_cache(tmp_path):
    evidence = parse_architectural_evidence(f"```json\n{json.dumps(SAMPLE)}\n```", photo_id="photo_x", provider="openai", model="test-model")
    assert evidence.visible_storeys.value == 3
    assert evidence.bay_count.value == 5
    assert evidence.opening_groups[0].columns == 5

    cache = tmp_path / "evidence.json"
    write_evidence_cache(cache, evidence)
    restored = read_evidence_cache(cache)
    assert restored.to_dict() == evidence.to_dict()


def test_vlm_evidence_becomes_observations_not_final_ir():
    evidence = parse_architectural_evidence(SAMPLE, photo_id="photo_x", provider="gemini", model="test-model")
    graph = vlm_evidence_to_observations(evidence, image_width=1000, image_height=800)
    kinds = [item.kind for item in graph.observations]
    assert ObservationKind.ARCHITECTURAL_EVIDENCE in kinds
    assert ObservationKind.FACADE_CANDIDATE in kinds
    assert ObservationKind.REPETITION_EVIDENCE in kinds
    assert ObservationKind.OCCLUSION_REGION in kinds
    assert all("width_mm" not in item.geometry for item in graph.observations)
    assert graph.debug["adapter"] == "vlm_architecture"


def test_vlm_schema_rejects_unbounded_confidence():
    invalid = json.loads(json.dumps(SAMPLE))
    invalid["facade"]["bay_count"]["confidence"] = 1.2
    with pytest.raises(ValueError, match="confidence"):
        parse_architectural_evidence(invalid, photo_id="bad", provider="openai", model="test")


def test_observation_package_keeps_existing_public_api():
    assert ObservationGraphBuilder is not None
    assert yolo_to_observations is not None
