from __future__ import annotations

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
