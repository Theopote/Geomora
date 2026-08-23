from __future__ import annotations

from geomora_detect.models import DetectedElement, DetectionResult
from geomora_reconstruct.constraints import ConstraintPriority, infer_constraint_suggestions
from geomora_reconstruct.export import detection_to_prediction
from geomora_reconstruct.ir_export import prediction_to_ir
from geomora_reconstruct.vlm_evidence import parse_architectural_evidence
from geomora_reconstruct.understanding.patterns import infer_pattern_groups


OPENINGS = [
    {"id": "w1", "type": "window", "bbox": [0.1, 0.2, 0.2, 0.4]},
    {"id": "w2", "type": "window", "bbox": [0.3, 0.2, 0.4, 0.4]},
    {"id": "w3", "type": "window", "bbox": [0.5, 0.2, 0.6, 0.4]},
]
TOPOLOGY = {
    "storey_count": 1,
    "bay_count": 3,
    "pattern_groups": [
        {
            "id": "row_a",
            "members": ["w1", "w2", "w3"],
            "constraints": ["equal_width", "equal_height", "equal_sill", "equal_spacing"],
            "confidence": 0.75,
        }
    ],
}


def vlm_evidence():
    return parse_architectural_evidence(
        {
            "building_type": {"value": "historic_masonry", "confidence": 0.8},
            "facade": {
                "bbox": [0, 0, 1, 1],
                "visible_storeys": {"value": 1, "confidence": 0.8},
                "bay_count": {"value": 3, "confidence": 0.8},
                "repetition": {"value": "strong", "confidence": 0.9},
            },
            "opening_groups": [
                {"type": "window", "rows": 1, "columns": 3, "region": [0.05, 0.1, 0.7, 0.5], "confidence": 0.85}
            ],
            "occlusions": [],
            "uncertainties": [],
        },
        photo_id="constraints",
        provider="openai",
        model="fixture",
    )


def test_pattern_groups_become_soft_ir_compatible_constraints():
    constraints = infer_constraint_suggestions(OPENINGS, TOPOLOGY)
    by_type = {item.type: item for item in constraints}
    assert set(by_type) == {"equal_width", "equal_height", "align", "equal_spacing"}
    assert by_type["align"].priority == ConstraintPriority.SOFT
    assert by_type["equal_width"].targets == ["w1", "w2", "w3"]
    assert by_type["equal_width"].source == "cv_pattern"
    assert all(0 < item.weight <= 1 for item in constraints)


def test_vlm_can_increase_confidence_but_not_create_targets():
    plain = infer_constraint_suggestions(OPENINGS, TOPOLOGY)
    fused = infer_constraint_suggestions(OPENINGS, TOPOLOGY, architectural_evidence=vlm_evidence())
    assert {tuple(item.targets) for item in fused} == {("w1", "w2", "w3")}
    assert fused[0].confidence > plain[0].confidence
    assert fused[0].source == "cv_pattern+vlm"


def test_unknown_or_invalid_members_do_not_reach_constraints():
    topology = {
        "pattern_groups": [
            {"id": "bad", "members": ["missing", "w1"], "constraints": ["equal_width"], "confidence": 1.0}
        ]
    }
    assert infer_constraint_suggestions(OPENINGS, topology) == []


def test_prediction_constraints_are_preserved_in_ir():
    detection = DetectionResult(
        method="fixture",
        confidence=0.8,
        image_width=1000,
        image_height=800,
        elements=[
            DetectedElement(type="window", bbox_norm=[0.1, 0.2, 0.2, 0.4], confidence=0.8),
            DetectedElement(type="window", bbox_norm=[0.3, 0.2, 0.4, 0.4], confidence=0.8),
            DetectedElement(type="window", bbox_norm=[0.5, 0.2, 0.6, 0.4], confidence=0.8),
        ],
        scale_hint={"wall_length_mm": 10000, "wall_height_mm": 3000},
    )
    topology = {
        **TOPOLOGY,
        "pattern_groups": [{**TOPOLOGY["pattern_groups"][0], "members": ["pred_001", "pred_002", "pred_003"]}],
    }
    prediction = detection_to_prediction("constraints", detection, topology=topology)
    ir = prediction_to_ir(prediction)
    assert ir is not None
    assert ir["constraints"]
    assert ir["constraints"][0]["priority"] == "soft"
    assert set(ir["constraints"][0]["targets"]) <= {item["id"] for item in ir["openings"]}


def test_pattern_inference_uses_measured_repetition_relationships():
    openings = [
        {"id": "w21", "type": "window", "bbox": [0.1, 0.1, 0.2, 0.3], "storey": 2, "bay": 1},
        {"id": "w22", "type": "window", "bbox": [0.3, 0.1, 0.4, 0.3], "storey": 2, "bay": 2},
        {"id": "w23", "type": "window", "bbox": [0.5, 0.1, 0.6, 0.3], "storey": 2, "bay": 3},
        {"id": "w11", "type": "window", "bbox": [0.1, 0.6, 0.2, 0.8], "storey": 1, "bay": 1},
    ]
    groups = infer_pattern_groups(openings)
    row = next(item for item in groups if item["id"] == "storey_2_row_pattern")
    column = next(item for item in groups if item["id"] == "bay_1_column_pattern")
    assert {"equal_width", "equal_height", "equal_sill", "equal_spacing"} <= set(row["constraints"])
    assert "vertical_alignment" in column["constraints"]
    assert row["evidence"]["width_spread"] == 0.0
