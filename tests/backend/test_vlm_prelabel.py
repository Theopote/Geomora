from __future__ import annotations

import pytest

from geomora_detect.vlm_prelabel import (
    bbox_norm_to_yolo_line,
    clamp_bbox_norm,
    extract_json_payload,
    parse_elements,
    sanitize_error_message,
)


def test_extract_json_payload_from_codeblock():
    payload = extract_json_payload('```json\n{"elements": []}\n```')
    assert payload == {"elements": []}


def test_parse_elements_filters_invalid_boxes():
    payload = {
        "elements": [
            {"type": "window", "bbox_norm": [0.1, 0.2, 0.3, 0.5], "confidence": 0.9},
            {"type": "door", "bbox_norm": [0.0, 0.0, 0.005, 0.5], "confidence": 0.8},
            {"type": "sign", "bbox_norm": [0.1, 0.2, 0.3, 0.5]},
        ]
    }
    elements = parse_elements(payload)
    assert len(elements) == 1
    assert elements[0].type == "window"


def test_bbox_norm_to_yolo_line():
    line = bbox_norm_to_yolo_line("window", [0.1, 0.2, 0.3, 0.5])
    assert line == "0 0.200000 0.350000 0.200000 0.300000"


def test_clamp_bbox_norm_rejects_tiny_box():
    assert clamp_bbox_norm([0.1, 0.2, 0.105, 0.5]) is None


def test_sanitize_error_message_redacts_key():
    message = "404 for url https://example.com?key=SECRET123"
    assert "SECRET123" not in sanitize_error_message(message, "SECRET123")
