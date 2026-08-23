from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np
import pytest

from geomora_detect.facade_row_detector import detect_facade_row_elements
from geomora_detect.models import DetectedElement, DetectionResult
from geomora_reconstruct.observations.adapters import (
    detection_result_to_observations,
    facade_row_to_observations,
    yolo_to_observations,
)
from geomora_reconstruct.observations.fusion import fuse_observation_graphs
from geomora_reconstruct.observations.models import ObservationKind


def _synthetic_image() -> np.ndarray:
    image = np.zeros((600, 800, 3), dtype=np.uint8)
    image[:] = (210, 210, 210)
    for x1, y1, x2, y2 in [(80, 140, 200, 320), (240, 140, 360, 320), (400, 140, 520, 320)]:
        cv2.rectangle(image, (x1, y1), (x2, y2), (35, 35, 120), -1)
    return image


def test_yolo_adapter_emits_opening_candidates():
    result = DetectionResult(
        method="yolo_v1",
        confidence=0.8,
        image_width=800,
        image_height=600,
        elements=[
            DetectedElement(type="window", bbox_norm=[0.1, 0.2, 0.2, 0.4], confidence=0.76)
        ],
    )
    graph = yolo_to_observations(result, photo_id="photo_test")
    assert graph.observations[0].kind == ObservationKind.OPENING_CANDIDATE
    assert "window" in graph.observations[0].semantic_candidates
    assert graph.observations[0].sources[0].type == "yolo"


def test_facade_row_adapter_includes_facade_candidate():
    image = _synthetic_image()
    result = detect_facade_row_elements(image, return_overlay=False)
    graph = facade_row_to_observations(result, photo_id="photo_test")
    kinds = {observation.kind for observation in graph.observations}
    assert ObservationKind.FACADE_CANDIDATE in kinds
    assert ObservationKind.OPENING_CANDIDATE in kinds


def test_fusion_preserves_sources_and_reduces_duplicates():
    image = _synthetic_image()
    row_result = detect_facade_row_elements(image, return_overlay=False)
    yolo_result = DetectionResult(
        method="yolo_v1",
        confidence=0.8,
        image_width=800,
        image_height=600,
        elements=row_result.elements[:1],
    )
    fused = fuse_observation_graphs(
        facade_row_to_observations(row_result, photo_id="photo_test"),
        yolo_to_observations(yolo_result, photo_id="photo_test"),
    )
    assert fused.debug["fused_count"] <= len(row_result.elements) + 1
    merged = [observation for observation in fused.observations if observation.kind == ObservationKind.OPENING_CANDIDATE]
    assert any(len(observation.sources) >= 2 for observation in merged)


def test_observation_graph_serializes_without_architectural_facts():
    image = _synthetic_image()
    result = detect_facade_row_elements(image, return_overlay=False)
    graph = detection_result_to_observations(result, photo_id="photo_test")
    payload = graph.to_dict()
    serialized = json.dumps(payload)
    restored = json.loads(serialized)
    assert restored["schema_version"] == "observation-graph-v0.1"
    for observation in restored["observations"]:
        assert "width_mm" not in observation
        assert observation["kind"] == "opening_candidate" or observation["kind"] == "facade_candidate"


@pytest.mark.parametrize("photo_id", ["photo_01", "photo_11", "photo_16", "photo_18", "photo_19"])
def test_minimal_set_ground_truth_loads(photo_id: str):
    path = Path(__file__).resolve().parent / "ground_truth" / f"{photo_id}.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["photo_id"] == photo_id
    assert payload["topology"]["storey_count"] >= 1
    assert len(payload["openings"]) >= 1
