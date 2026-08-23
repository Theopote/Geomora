from __future__ import annotations

import numpy as np

from geomora_reconstruct.observations.depth_discontinuities import (
    depth_discontinuity_observations,
    depth_observations_to_storey_cues,
)
from geomora_reconstruct.observations.models import ObservationKind


def _stepped_depth():
    depth = np.full((200, 300), 0.2, dtype=np.float32)
    depth[100:, :] = 0.8
    return depth


def test_neural_depth_step_becomes_structural_boundary_candidate():
    graph = depth_discontinuity_observations(
        _stepped_depth(), photo_id="depth", method="depth_anything_v2_small_v1",
    )
    assert graph.observations
    strongest = max(graph.observations, key=lambda item: item.confidence)
    assert strongest.kind == ObservationKind.DEPTH_DISCONTINUITY
    assert abs(strongest.geometry["y"] - 0.5) < 0.03
    assert "depth_discontinuity" in strongest.semantic_candidates
    assert graph.debug["metric_depth_evidence"] is True
    cues = depth_observations_to_storey_cues(graph.observations)
    assert any(cue["role"] == "depth_discontinuity" for cue in cues)


def test_gradient_proxy_cannot_become_storey_boundary():
    graph = depth_discontinuity_observations(
        _stepped_depth(), photo_id="proxy", method="gradient_laplacian_v1",
    )
    assert graph.observations
    assert graph.debug["metric_depth_evidence"] is False
    assert all("depth_discontinuity" not in item.semantic_candidates for item in graph.observations)
    assert all("non_metric_depth_proxy_not_a_storey_boundary" in item.uncertainties for item in graph.observations)


def test_uniform_depth_emits_no_false_discontinuity():
    graph = depth_discontinuity_observations(
        np.full((120, 160), 0.5, dtype=np.float32),
        photo_id="flat", method="midas_v21_v1",
    )
    assert graph.observations == []
