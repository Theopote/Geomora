"""Import reviewed ground truth JSON from the GT review pack exports folder.

Example:
  cd backend
  .venv\\Scripts\\python scripts/import_gt_review_pack.py
  .venv\\Scripts\\python scripts/import_gt_review_pack.py --exports ..\\tests\\reconstruction\\review_pack\\exports
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent

DEFAULT_EXPORTS = REPO_ROOT / "tests" / "reconstruction" / "review_pack" / "exports"
DEFAULT_GT_DIR = REPO_ROOT / "tests" / "reconstruction" / "ground_truth"
MINIMAL_SET = REPO_ROOT / "tests" / "reconstruction" / "minimal_set.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exports", type=Path, default=DEFAULT_EXPORTS)
    parser.add_argument("--ground-truth-dir", type=Path, default=DEFAULT_GT_DIR)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_gt(payload: dict) -> list[str]:
    errors: list[str] = []
    if payload.get("schema_version") != "reconstruction-metrics-v1":
        errors.append("schema_version must be reconstruction-metrics-v1")
    if not payload.get("photo_id"):
        errors.append("photo_id is required")
    topology = payload.get("topology") or {}
    if not topology.get("storey_count"):
        errors.append("topology.storey_count is required")
    if not topology.get("bay_count"):
        errors.append("topology.bay_count is required")
    openings = payload.get("openings") or []
    if not openings:
        errors.append("at least one opening is required")
    for opening in openings:
        if not opening.get("id"):
            errors.append("opening missing id")
        bbox = opening.get("bbox") or []
        if len(bbox) != 4:
            errors.append(f"{opening.get('id')}: bbox must have 4 values")
            continue
        if bbox[2] <= bbox[0] or bbox[3] <= bbox[1]:
            errors.append(f"{opening.get('id')}: invalid bbox ordering")
    facade_bbox = payload.get("facade_bbox") or []
    if len(facade_bbox) == 4 and (facade_bbox[2] <= facade_bbox[0] or facade_bbox[3] <= facade_bbox[1]):
        errors.append("invalid facade_bbox")
    for anchor in payload.get("metric_anchors") or []:
        if anchor.get("distance_mm") in (None, ""):
            continue
        if float(anchor["distance_mm"]) <= 0:
            errors.append(f"{anchor.get('id')}: distance_mm must be positive")
    return errors


def normalize_gt(payload: dict) -> dict:
    payload = json.loads(json.dumps(payload))
    payload["annotation_status"] = payload.get("annotation_status") or "reviewed_v1"
    if payload["annotation_status"] == "draft_v1":
        payload["annotation_status"] = "reviewed_v1"
    payload["review_rounds"] = int(payload.get("review_rounds") or 1) + 1
    for opening in payload.get("openings", []):
        opening["bbox"] = [round(float(v), 4) for v in opening["bbox"]]
    if payload.get("facade_bbox"):
        payload["facade_bbox"] = [round(float(v), 4) for v in payload["facade_bbox"]]
    return payload


def main() -> int:
    args = parse_args()
    if not args.exports.exists():
        raise SystemExit(f"Exports folder not found: {args.exports}")

    files = sorted(args.exports.glob("photo_*.json"))
    if not files:
        raise SystemExit(f"No photo_*.json files in {args.exports}")

    merged = 0
    for path in files:
        payload = load_json(path)
        errors = validate_gt(payload)
        if errors:
            print(f"SKIP {path.name}:")
            for error in errors:
                print(f"  - {error}")
            continue

        normalized = normalize_gt(payload)
        out_path = args.ground_truth_dir / f"{normalized['photo_id']}.json"
        if args.dry_run:
            print(f"DRY-RUN would write {out_path.name} (review_rounds={normalized['review_rounds']})")
        else:
            out_path.write_text(json.dumps(normalized, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(f"Merged {path.name} -> {out_path}")
        merged += 1

    if merged == 0:
        return 1

    if not args.dry_run and MINIMAL_SET.exists():
        minimal = load_json(MINIMAL_SET)
        required = set(minimal.get("metric_anchor_required", []))
        for photo_id in required:
            gt_path = args.ground_truth_dir / f"{photo_id}.json"
            if not gt_path.exists():
                continue
            gt = load_json(gt_path)
            anchors = gt.get("metric_anchors") or []
            surveyed = [a for a in anchors if a.get("distance_mm") not in (None, "")]
            if not surveyed:
                print(f"WARN {photo_id}: metric anchor still pending survey")

    print(f"Done: {merged}/{len(files)} files imported")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
