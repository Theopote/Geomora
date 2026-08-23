from __future__ import annotations

import cv2
import numpy as np

from geomora_reconstruct.observations.models import ObservationKind
from geomora_reconstruct.observations.structural_lines import (
    classify_horizontal_structure_roles,
    detect_horizontal_structure_observations,
    horizontal_observations_to_storey_cues,
)
from geomora_reconstruct.observations.models import Observation, ObservationSource


def _line(line_id, y, x1=0.05, x2=0.95, confidence=0.9):
    return Observation(
        id=line_id, kind=ObservationKind.HORIZONTAL_LINE,
        geometry={"y": y, "x_range": [x1, x2]},
        semantic_candidates={"horizontal_structure": confidence}, confidence=confidence,
        sources=[ObservationSource("fixture", confidence)],
        uncertainties=["architectural_role_unclassified"],
    )


def test_detects_and_clusters_long_horizontal_structure(tmp_path):
    image = np.full((600, 800, 3), 185, dtype=np.uint8)
    cv2.line(image, (80, 210), (720, 210), (30, 30, 30), 5)
    cv2.line(image, (80, 410), (720, 410), (30, 30, 30), 5)
    path = tmp_path / "facade.jpg"
    cv2.imwrite(str(path), image)

    graph = detect_horizontal_structure_observations(
        path, photo_id="synthetic", facade_bbox=[0.05, 0.05, 0.95, 0.95],
    )

    assert graph.debug["adapter"] == "horizontal_structure_v0.1"
    assert len(graph.observations) == 2
    assert all(item.kind == ObservationKind.HORIZONTAL_LINE for item in graph.observations)
    ys = [item.geometry["y"] for item in graph.observations]
    assert abs(ys[0] - 210 / 600) < 0.02
    assert abs(ys[1] - 410 / 600) < 0.02
    assert all("architectural_role_unclassified" in item.uncertainties for item in graph.observations)


def test_line_observations_become_non_semantic_storey_cues(tmp_path):
    image = np.full((300, 500, 3), 180, dtype=np.uint8)
    cv2.line(image, (20, 150), (480, 150), (20, 20, 20), 4)
    path = tmp_path / "line.jpg"
    cv2.imwrite(str(path), image)
    graph = detect_horizontal_structure_observations(path, photo_id="line")

    cues = horizontal_observations_to_storey_cues(graph.observations)

    assert cues
    assert all(cue["role"] == "horizontal_structure" for cue in cues)
    assert all(cue["role"] != "floor_slab" for cue in cues)


def test_line_between_two_stable_window_rows_is_floor_slab_candidate():
    lines = [_line("between_rows", 0.49)]
    openings = [
        {"type": "window", "bbox": [0.1, 0.12, 0.25, 0.32]},
        {"type": "window", "bbox": [0.55, 0.12, 0.7, 0.32]},
        {"type": "window", "bbox": [0.1, 0.62, 0.25, 0.82]},
        {"type": "window", "bbox": [0.55, 0.62, 0.7, 0.82]},
    ]

    counts = classify_horizontal_structure_roles(lines, openings=openings)

    assert counts == {"floor_slab": 1}
    assert max(lines[0].semantic_candidates, key=lines[0].semantic_candidates.get) == "floor_slab"
    assert "architectural_role_inferred_from_opening_context" in lines[0].uncertainties


def test_lone_row_cannot_promote_unrelated_line_to_floor_slab():
    lines = [_line("unrelated", 0.65)]
    openings = [
        {"type": "window", "bbox": [0.1, 0.2, 0.25, 0.4]},
        {"type": "window", "bbox": [0.55, 0.2, 0.7, 0.4]},
    ]

    classify_horizontal_structure_roles(lines, openings=openings)

    assert "floor_slab" not in lines[0].semantic_candidates


def test_repeated_window_edge_is_opening_alignment_not_slab():
    lines = [_line("lintel", 0.2)]
    openings = [
        {"type": "window", "bbox": [0.1, 0.2, 0.25, 0.4]},
        {"type": "window", "bbox": [0.55, 0.2, 0.7, 0.4]},
    ]

    classify_horizontal_structure_roles(lines, openings=openings)

    assert max(lines[0].semantic_candidates, key=lines[0].semantic_candidates.get) == "opening_alignment"
