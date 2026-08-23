from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft7Validator


ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = ROOT / "schemas/geomora-ir-v0.1.schema.json"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_ir_schema_is_a_valid_draft7_schema():
    Draft7Validator.check_schema(load(SCHEMA_PATH))


def test_phase0_example_matches_ir_schema():
    Draft7Validator(load(SCHEMA_PATH)).validate(load(ROOT / "examples/facade_phase0.json"))


def test_current_reconstruction_ir_artifacts_match_schema():
    validator = Draft7Validator(load(SCHEMA_PATH))
    artifacts = sorted((ROOT / "tests/reconstruction/baselines/current").glob("photo_*/architectural_ir.json"))
    assert len(artifacts) == 5
    for path in artifacts:
        errors = sorted(validator.iter_errors(load(path)), key=lambda item: list(item.path))
        assert not errors, f"{path}: " + "; ".join(error.message for error in errors)
