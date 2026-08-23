from __future__ import annotations

import cv2
import numpy as np

from geomora_reconstruct.observations.models import ObservationKind
from geomora_reconstruct.observations.structural_lines import (
    detect_horizontal_structure_observations,
    horizontal_observations_to_storey_cues,
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
