from __future__ import annotations

from geomora_reconstruct.observations.balconies import (
    balcony_observations_to_storey_cues,
    infer_balcony_slab_observations,
)
from geomora_reconstruct.observations.models import Observation, ObservationKind


def _line(x_range=(0.2, 0.7)):
    return Observation("line_1", ObservationKind.HORIZONTAL_LINE, {"y": 0.5, "x_range": list(x_range)},
                       {"horizontal_structure": 0.88}, 0.88)


def _depth(*, reliable=True):
    role = "depth_discontinuity" if reliable else "depth_edge_proxy"
    return Observation("depth_1", ObservationKind.DEPTH_DISCONTINUITY,
                       {"y": 0.505, "x_range": [0.0, 1.0]}, {role: 0.86}, 0.86)


def _windows():
    return [{"id": "w1", "type": "window", "bbox": [0.3, 0.25, 0.48, 0.44]}]


def test_cross_modal_consensus_creates_balcony_slab_evidence():
    result = infer_balcony_slab_observations([_line()], [_depth()], openings=_windows())
    assert len(result) == 1
    balcony = result[0]
    assert balcony.kind == ObservationKind.BALCONY_CANDIDATE
    assert "balcony_slab" in balcony.semantic_candidates
    assert {source.metadata["observation_id"] for source in balcony.sources} == {"line_1", "depth_1"}
    assert balcony.geometry["supported_opening_ids"] == ["w1"]
    assert balcony_observations_to_storey_cues(result)[0]["role"] == "balcony_slab"


def test_gradient_depth_proxy_cannot_create_balcony():
    assert infer_balcony_slab_observations([_line()], [_depth(reliable=False)], openings=_windows()) == []


def test_full_facade_line_is_not_guessed_as_local_balcony():
    assert infer_balcony_slab_observations([_line((0.02, 0.98))], [_depth()], openings=_windows()) == []


def test_balcony_requires_opening_support_above_slab():
    unsupported = [{"id": "w1", "type": "window", "bbox": [0.75, 0.25, 0.9, 0.44]}]
    assert infer_balcony_slab_observations([_line()], [_depth()], openings=unsupported) == []
