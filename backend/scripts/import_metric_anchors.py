"""Import surveyed metric anchors into ground truth JSON.

Supports:
  - single-photo JSON: {"photo_id": "photo_11", "distance_mm": 12400}
  - batch JSON: {"version": "metric-anchors-v1", "anchors": [...]}
  - CSV: photo_id,anchor_id,distance_mm,notes

Examples:
  cd backend
  .venv\\Scripts\\python scripts/import_metric_anchors.py --status
  .venv\\Scripts\\python scripts/import_metric_anchors.py anchors/photo_11.json
  .venv\\Scripts\\python scripts/import_metric_anchors.py anchors/survey_batch.csv
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
sys.path.insert(0, str(BACKEND_ROOT))

from geomora_reconstruct.metric_anchors import (  # noqa: E402
    anchor_status_report,
    merge_anchor_updates,
    validate_anchor,
)

DEFAULT_GT_DIR = REPO_ROOT / "tests" / "reconstruction" / "ground_truth"
MINIMAL_SET = REPO_ROOT / "tests" / "reconstruction" / "minimal_set.json"
DEFAULT_TEMPLATES = REPO_ROOT / "tests" / "reconstruction" / "review_pack" / "anchors"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", nargs="*", type=Path, help="Anchor JSON/CSV files")
    parser.add_argument("--ground-truth-dir", type=Path, default=DEFAULT_GT_DIR)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--status", action="store_true", help="Print anchor status for minimal set")
    parser.add_argument("--export-templates", type=Path, nargs="?", const=DEFAULT_TEMPLATES)
    return parser.parse_args()


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_updates(path: Path) -> list[dict]:
    if path.suffix.lower() == ".csv":
        return load_csv_updates(path)
    payload = load_json(path)
    if "anchors" in payload:
        return list(payload["anchors"])
    if "photo_id" in payload:
        return [payload]
    raise ValueError(f"Unrecognized anchor file format: {path}")


def load_csv_updates(path: Path) -> list[dict]:
    rows: list[dict] = []
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            if not row.get("photo_id"):
                continue
            item = {
                "photo_id": row["photo_id"].strip(),
                "anchor_id": (row.get("anchor_id") or "anchor_facade_width").strip(),
            }
            if row.get("distance_mm") not in (None, ""):
                item["distance_mm"] = float(row["distance_mm"])
            if row.get("notes"):
                item["notes"] = row["notes"].strip()
            rows.append(item)
    return rows


def group_updates(updates: list[dict]) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = {}
    for update in updates:
        photo_id = update.get("photo_id")
        if not photo_id:
            continue
        grouped.setdefault(photo_id, []).append(update)
    return grouped


def export_templates(out_dir: Path, required_photo_ids: list[str], gt_dir: Path) -> int:
    out_dir.mkdir(parents=True, exist_ok=True)
    count = 0
    for photo_id in required_photo_ids:
        gt_path = gt_dir / f"{photo_id}.json"
        if not gt_path.exists():
            continue
        gt = load_json(gt_path)
        anchors = gt.get("metric_anchors") or []
        template = {
            "version": "metric-anchors-v1",
            "photo_id": photo_id,
            "anchor_id": anchors[0]["id"] if anchors else "anchor_facade_width",
            "distance_mm": None,
            "notes": "Replace distance_mm with on-site tape/survey measurement.",
            "anchors": anchors,
        }
        out_path = out_dir / f"{photo_id}.json"
        out_path.write_text(json.dumps(template, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        count += 1

    csv_path = out_dir / "survey_batch.template.csv"
    csv_path.write_text(
        "photo_id,anchor_id,distance_mm,notes\n"
        + "\n".join(
            f"{photo_id},anchor_facade_width,,on-site measurement required"
            for photo_id in required_photo_ids
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"Templates -> {out_dir.resolve()} ({count} JSON + survey_batch.template.csv)")
    return count


def print_status(gt_dir: Path, required_photo_ids: list[str]) -> int:
    pending = 0
    for photo_id in required_photo_ids:
        gt_path = gt_dir / f"{photo_id}.json"
        if not gt_path.exists():
            print(f"{photo_id}: missing ground truth")
            pending += 1
            continue
        report = anchor_status_report(load_json(gt_path))
        status = "READY" if report["surveyed_count"] and report["has_metric"] else "PENDING"
        print(
            f"{photo_id}: {status} surveyed={report['surveyed_count']}/{report['anchor_count']} "
            f"metric={report['has_metric']} pending={report['pending_ids']}"
        )
        if status != "READY":
            pending += 1
    return 0 if pending == 0 else 1


def import_updates(grouped: dict[str, list[dict]], gt_dir: Path, *, dry_run: bool) -> int:
    merged = 0
    for photo_id, updates in sorted(grouped.items()):
        gt_path = gt_dir / f"{photo_id}.json"
        if not gt_path.exists():
            print(f"SKIP {photo_id}: ground truth not found")
            continue
        gt = load_json(gt_path)
        merged_gt, warnings = merge_anchor_updates(gt, updates)
        for warning in warnings:
            print(f"WARN {photo_id}: {warning}")

        metric = merged_gt.get("metric")
        if dry_run:
            print(
                f"DRY-RUN {photo_id}: metric={metric} "
                f"anchors={[a.get('id') for a in merged_gt.get('metric_anchors', [])]}"
            )
        else:
            gt_path.write_text(json.dumps(merged_gt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(f"Merged {photo_id} -> {gt_path.name} metric={metric}")
        merged += 1
    return merged


def main() -> int:
    args = parse_args()
    required = []
    if MINIMAL_SET.exists():
        required = load_json(MINIMAL_SET).get("metric_anchor_required", [])

    if args.export_templates is not None:
        export_templates(args.export_templates, required, args.ground_truth_dir)
        return 0

    if args.status:
        return print_status(args.ground_truth_dir, required)

    if not args.inputs:
        print_status(args.ground_truth_dir, required)
        print("")
        print("Import examples:")
        print("  .venv\\Scripts\\python scripts/import_metric_anchors.py --export-templates")
        print("  .venv\\Scripts\\python scripts/import_metric_anchors.py ..\\tests\\reconstruction\\review_pack\\anchors\\photo_11.json")
        return 1

    updates: list[dict] = []
    for path in args.inputs:
        if not path.exists():
            print(f"SKIP missing file: {path}")
            continue
        updates.extend(load_updates(path))

    if not updates:
        print("No anchor updates found.")
        return 1

    grouped = group_updates(updates)
    merged = import_updates(grouped, args.ground_truth_dir, dry_run=args.dry_run)
    if merged == 0:
        return 1

    if not args.dry_run and required:
        existing_required = [
            photo_id for photo_id in required if (args.ground_truth_dir / f"{photo_id}.json").exists()
        ]
        if existing_required:
            return print_status(args.ground_truth_dir, existing_required)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
