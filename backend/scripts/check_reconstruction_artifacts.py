"""Check that a minimal-set reconstruction produced complete, schema-valid artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from jsonschema import Draft7Validator


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifact_dir", type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    manifest = json.loads((root / "tests/reconstruction/minimal_set.json").read_text(encoding="utf-8"))
    validator = Draft7Validator(json.loads((root / "schemas/geomora-ir-v0.1.schema.json").read_text(encoding="utf-8")))
    for item in manifest["photos"]:
        photo_dir = args.artifact_dir / item["id"]
        required = ("prediction.json", "reconstruction_metrics.json", "architectural_ir.json", "observation_graph.json")
        missing = [name for name in required if not (photo_dir / name).exists()]
        if missing:
            raise SystemExit(f"{item['id']}: missing artifacts: {', '.join(missing)}")
        prediction = json.loads((photo_dir / "prediction.json").read_text(encoding="utf-8"))
        metrics = json.loads((photo_dir / "reconstruction_metrics.json").read_text(encoding="utf-8"))
        ir = json.loads((photo_dir / "architectural_ir.json").read_text(encoding="utf-8"))
        if prediction.get("photo_id") != item["id"] or metrics.get("photo_id") != item["id"]:
            raise SystemExit(f"{item['id']}: artifact photo_id mismatch")
        errors = sorted(validator.iter_errors(ir), key=lambda error: list(error.path))
        if errors:
            raise SystemExit(f"{item['id']}: IR schema failure: {errors[0].message}")
        if metrics.get("rqs") is None or metrics.get("coverage") is None:
            raise SystemExit(f"{item['id']}: incomplete Reconstruction Metrics")
        print(f"[PASS] {item['id']}: rqs={metrics['rqs']} coverage={metrics['coverage']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
