from __future__ import annotations

from geomora_reconstruct.understanding import understand_openings
from geomora_reconstruct.topology_inference import infer_topology_from_openings


def test_infer_two_storey_facade_rows():
    openings = [
        {"id": "w21", "type": "window", "bbox": [0.10, 0.12, 0.30, 0.36]},
        {"id": "w22", "type": "window", "bbox": [0.60, 0.12, 0.80, 0.36]},
        {"id": "d11", "type": "door", "bbox": [0.39, 0.58, 0.51, 0.98]},
        {"id": "w11", "type": "window", "bbox": [0.10, 0.58, 0.30, 0.82]},
        {"id": "w12", "type": "window", "bbox": [0.60, 0.58, 0.80, 0.82]},
    ]
    topology, enriched = infer_topology_from_openings(openings)

    assert topology["storey_count"] == 2
    assert topology["bay_count"] == 2
    assert topology["method"] == "understanding_v0.1"
    by_id = {item["id"]: item for item in enriched}
    assert by_id["w11"]["storey"] == 1
    assert by_id["w21"]["storey"] == 2
    assert by_id["w11"]["bay"] == 1
    assert by_id["w22"]["bay"] == 2
    assert by_id["d11"]["storey"] == 1


def test_infer_single_row_windows():
    openings = [
        {"id": "w1", "type": "window", "bbox": [0.10, 0.20, 0.20, 0.40]},
        {"id": "w2", "type": "window", "bbox": [0.30, 0.21, 0.40, 0.41]},
        {"id": "w3", "type": "window", "bbox": [0.50, 0.19, 0.60, 0.39]},
    ]
    topology, enriched = infer_topology_from_openings(openings)

    assert topology["storey_count"] == 1
    assert topology["bay_count"] == 3
    assert all(item["storey"] == 1 for item in enriched)


def test_filters_giant_false_window_before_storey_clustering():
    openings = [
        {"id": "w_top_1", "type": "window", "bbox": [0.12, 0.10, 0.28, 0.30]},
        {"id": "w_top_2", "type": "window", "bbox": [0.38, 0.10, 0.54, 0.30]},
        {"id": "w_top_3", "type": "window", "bbox": [0.64, 0.10, 0.80, 0.30]},
        {"id": "w_bot_1", "type": "window", "bbox": [0.12, 0.58, 0.28, 0.78]},
        {"id": "w_bot_2", "type": "window", "bbox": [0.38, 0.58, 0.54, 0.78]},
        {"id": "w_bot_3", "type": "window", "bbox": [0.64, 0.58, 0.80, 0.78]},
        {"id": "false_full", "type": "window", "bbox": [0.05, 0.05, 0.95, 0.95]},
    ]
    result, enriched = understand_openings(openings)
    topology = {
        "storey_count": result.debug["storey_count"],
        "bay_count": result.debug["bay_count"],
    }

    assert topology["storey_count"] == 2
    assert topology["bay_count"] == 3
    assert "filtered_outliers:1" in result.uncertainties
    by_id = {item["id"]: item for item in enriched}
    assert by_id["false_full"]["understanding_status"] == "low_confidence"


def test_semantic_floor_boundary_can_form_storey_hypotheses_without_windows():
    openings = [{"id": "d1", "type": "door", "bbox": [0.4, 0.62, 0.55, 0.95], "confidence": 0.9}]
    result, enriched = understand_openings(
        openings,
        facade_bounds=[0.05, 0.05, 0.95, 0.95],
        storey_cues=[{
            "id": "slab_1", "type": "horizontal_line", "role": "floor_slab",
            "y": 0.52, "confidence": 0.9, "source": "structural_detector",
        }],
    )
    assert result.debug["storey_count"] == 2
    assert [band.status for band in result.storeys] == ["hypothesized", "hypothesized"]
    assert enriched[0]["storey"] == 1
    assert set(result.debug["storey_hypothesis"]["used_cue_ids"]) == {"door_baseline:d1", "slab_1"}


def test_generic_horizontal_line_does_not_invent_a_storey():
    openings = [{"id": "w1", "type": "window", "bbox": [0.2, 0.3, 0.4, 0.5]}]
    result, _ = understand_openings(
        openings,
        storey_cues=[{
            "id": "cornice_unknown", "type": "horizontal_line", "role": "horizontal_structure",
            "y": 0.7, "confidence": 0.98,
        }],
    )
    assert result.debug["storey_count"] == 1
    assert result.debug["storey_hypothesis"]["unused_cue_ids"] == ["cornice_unknown"]


def test_structural_line_support_is_traced_on_window_row_hypothesis():
    openings = [
        {"id": "w1", "type": "window", "bbox": [0.1, 0.2, 0.25, 0.4]},
        {"id": "w2", "type": "window", "bbox": [0.5, 0.2, 0.65, 0.4]},
    ]
    result, _ = understand_openings(
        openings,
        storey_cues=[{"id": "belt_1", "role": "cornice", "y": 0.405, "confidence": 0.8}],
    )
    evidence_types = {item["type"] for item in result.storeys[0].evidence}
    assert evidence_types == {"window_row", "cornice"}


def test_door_ground_floor_is_hypothesis_with_observed_facade_evidence():
    openings = [
        {"id": "w1", "type": "window", "bbox": [0.1, 0.2, 0.25, 0.4]},
        {"id": "w2", "type": "window", "bbox": [0.5, 0.2, 0.65, 0.4]},
        {"id": "d1", "type": "door", "bbox": [0.35, 0.42, 0.48, 0.68], "confidence": 0.9},
    ]
    result, enriched = understand_openings(openings, facade_bounds=[0.05, 0.05, 0.95, 0.7])
    door = next(item for item in enriched if item["id"] == "d1")
    assert door["storey"] == 1
    assert door["understanding_status"] == "hypothesized"
    assert door["storey_hypothesis"]["hypothesis"] == "ground_floor_door"
    assert "near_observed_facade_bottom" in door["storey_hypothesis"]["evidence"]
    assert "legacy_low_image_position" not in door["storey_hypothesis"]["evidence"]
    assert result.door_hypotheses[0]["door_id"] == "d1"


def test_door_away_from_ground_uses_nearest_storey_band_not_absolute_threshold():
    openings = [
        {"id": "w21", "type": "window", "bbox": [0.1, 0.18, 0.25, 0.38]},
        {"id": "w22", "type": "window", "bbox": [0.5, 0.18, 0.65, 0.38]},
        {"id": "w11", "type": "window", "bbox": [0.1, 0.65, 0.25, 0.85]},
        {"id": "w12", "type": "window", "bbox": [0.5, 0.65, 0.65, 0.85]},
        {"id": "d2", "type": "door", "bbox": [0.72, 0.16, 0.84, 0.5], "confidence": 0.8},
    ]
    _result, enriched = understand_openings(openings, facade_bounds=[0.05, 0.05, 0.95, 1.0])
    door = next(item for item in enriched if item["id"] == "d2")
    assert door["storey"] == 2
    assert "nearest_storey_band" in door["storey_hypothesis"]["evidence"]
    assert door["storey_hypothesis"]["status"] == "hypothesized"
