"""Summarize solver/review audit records without exposing holdout details."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
sys.path.insert(0, str(BACKEND_ROOT))

from geomora_reconstruct.reconstruction_audit import extract_audit_event, summarize_audit  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="IR JSON file or directory")
    parser.add_argument("--minimal-set", type=Path, default=REPO_ROOT / "tests/reconstruction/minimal_set.json")
    parser.add_argument("--output", type=Path, default=BACKEND_ROOT / "runs/reconstruction_audit.json")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    minimal = json.loads(args.minimal_set.read_text(encoding="utf-8")) if args.minimal_set.exists() else {"photos": []}
    split_by_id = {item["id"]: item.get("split", "unknown") for item in minimal.get("photos", [])}
    paths = [args.input] if args.input.is_file() else sorted(args.input.rglob("*.json"))
    events = []
    for path in paths:
        document = json.loads(path.read_text(encoding="utf-8"))
        artifact_id = document.get("project", {}).get("name") or path.stem
        event = extract_audit_event(document, artifact_id=artifact_id, split=split_by_id.get(artifact_id, "unknown"))
        if event is not None:
            events.append(event)
    payload = {
        "schema_version": "reconstruction-audit-v0.1",
        "summary": summarize_audit(events),
        "events": [event for event in events if event["split"] != "holdout"],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Reconstruction audit -> {args.output.resolve()}")
    print(json.dumps(payload["summary"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
