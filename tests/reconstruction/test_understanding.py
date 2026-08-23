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
