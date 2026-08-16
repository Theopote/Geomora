"""A1 Real Photo Benchmark runner — detection baseline + E2E scorecard template.

Does NOT fix failures. Records automated signals and produces a SketchUp review checklist.

Example:
  cd backend
  .venv\\Scripts\\python scripts/run_real_photo_benchmark.py
  .venv\\Scripts\\python scripts/run_real_photo_benchmark.py --split holdout
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
sys.path.insert(0, str(BACKEND_ROOT))

from geomora_detect.pipeline import detect_facade  # noqa: E402

MANIFEST_DEFAULT = REPO_ROOT / "examples" / "real_photos" / "benchmark" / "manifest.json"

FAILURE_CLASSES = (
    "missed_window",
    "false_window",
    "missed_door",
    "false_door",
    "bad_rectify",
    "wrong_scale",
    "wrong_pattern",
    "invalid_geometry",
    "generate_failed",
    "none",
)

RQS_DIMENSIONS = (
    ("perspective_rectification", 15),
    ("opening_detection", 20),
    ("opening_placement", 15),
    ("scale", 10),
    ("pattern_rationalization", 10),
    ("geometry_validity", 15),
    ("sketchup_editability", 10),
    ("human_correction_cost", 5),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run A1 real-photo benchmark baseline")
    parser.add_argument("--manifest", type=Path, default=MANIFEST_DEFAULT)
    parser.add_argument("--split", choices=("train", "val", "holdout", "all"), default="all")
    parser.add_argument("--method", default="auto")
    parser.add_argument("--rectify-log", type=Path, default=BACKEND_ROOT / "cache" / "real_photo_rectify_log.json")
    parser.add_argument("--out", type=Path, default=None, help="Output JSON (default: cache/benchmark_a1_e2e.json or _{split}.json)")
    return parser.parse_args()


def load_manifest(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"Manifest not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def load_rectify_map(log_path: Path) -> dict[str, dict]:
    if not log_path.exists():
        return {}
    items = json.loads(log_path.read_text(encoding="utf-8"))
    return {item["file"]: item for item in items}


def resolve_image_path(manifest: dict, file_name: str) -> Path:
    root = manifest.get("image_root", "backend/cache/real_photo_desktop_rectified")
    candidate = (REPO_ROOT / root / file_name).resolve()
    if candidate.exists():
        return candidate
    fallback = (BACKEND_ROOT / "cache" / "real_photo_desktop_rectified" / file_name).resolve()
    if fallback.exists():
        return fallback
    raise FileNotFoundError(f"Image not found: {file_name}")


def infer_failure_hints(
    *,
    detect_passed: bool,
    window_count: int,
    door_count: int,
    confidence: float,
    rectify: dict | None,
) -> list[str]:
    hints: list[str] = []
    if window_count == 0:
        hints.append("missed_window")
    if window_count >= 8:
        hints.append("false_window")
    if door_count >= 1 and window_count == 0:
        hints.append("false_door")
    if confidence < 0.5:
        hints.append("opening_detection")
    if rectify and rectify.get("method") == "auto_full_frame":
        hints.append("bad_rectify")
    if not detect_passed and not hints:
        hints.append("opening_detection")
    return hints or ["none"]


def empty_rqs() -> dict[str, int | None]:
    return {name: None for name, _ in RQS_DIMENSIONS}


def run_entry(
    entry: dict,
    manifest: dict,
    rectify_map: dict[str, dict],
    method: str,
) -> dict:
    image_path = resolve_image_path(manifest, entry["file"])
    rectify = rectify_map.get(entry["file"])
    result = detect_facade(str(image_path), method=method, return_overlay=False)
    windows = [e for e in result.elements if e.type == "window"]
    doors = [e for e in result.elements if e.type == "door"]
    detect_passed = len(windows) >= 1

    return {
        "id": entry["id"],
        "file": entry["file"],
        "split": entry["split"],
        "category": entry.get("category", ""),
        "image_path": str(image_path),
        "detection": {
            "method": result.method,
            "confidence": round(result.confidence, 4),
            "window_count": len(windows),
            "door_count": len(doors),
            "passed_smoke": detect_passed,
            "scale_hint": result.scale_hint,
        },
        "rectify": {
            "ok": rectify.get("rectify_ok") if rectify else None,
            "method": rectify.get("method") if rectify else None,
            "confidence": rectify.get("confidence") if rectify else None,
        },
        "automated_failure_hints": infer_failure_hints(
            detect_passed=detect_passed,
            window_count=len(windows),
            door_count=len(doors),
            confidence=result.confidence,
            rectify=rectify,
        ),
        "e2e": {
            "sketchup_reviewed": False,
            "failure_classes": [],
            "overlay_correction": None,
            "generate_ok": None,
            "correction_time_sec": None,
            "rqs": empty_rqs(),
            "rqs_total": None,
            "notes": "",
        },
    }


def summarize(results: list[dict]) -> dict:
    by_split: dict[str, dict] = {}
    for row in results:
        split = row["split"]
        bucket = by_split.setdefault(split, {"total": 0, "detect_pass": 0, "hints": {}})
        bucket["total"] += 1
        if row["detection"]["passed_smoke"]:
            bucket["detect_pass"] += 1
        for hint in row["automated_failure_hints"]:
            if hint != "none":
                bucket["hints"][hint] = bucket["hints"].get(hint, 0) + 1

    return {
        "images": len(results),
        "detect_pass": sum(1 for r in results if r["detection"]["passed_smoke"]),
        "by_split": by_split,
    }


def main() -> None:
    args = parse_args()
    manifest = load_manifest(args.manifest.resolve())
    rectify_map = load_rectify_map(args.rectify_log.resolve())

    entries = manifest["images"]
    if args.split != "all":
        entries = [e for e in entries if e["split"] == args.split]

    results = [run_entry(e, manifest, rectify_map, args.method) for e in entries]
    summary = summarize(results)

    out_path = args.out
    if out_path is None:
        out_path = BACKEND_ROOT / "cache" / (
            "benchmark_a1_e2e.json" if args.split == "all" else f"benchmark_a1_e2e_{args.split}.json"
        )

    payload = {
        "benchmark": "a1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "method": args.method,
        "manifest": str(args.manifest.resolve()),
        "summary": summary,
        "rqs_rubric": {name: max_pts for name, max_pts in RQS_DIMENSIONS},
        "failure_classes": list(FAILURE_CLASSES),
        "results": results,
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    print(f"A1 benchmark: {summary['detect_pass']}/{summary['images']} detection smoke pass")
    for split, stats in summary["by_split"].items():
        print(f"  {split}: {stats['detect_pass']}/{stats['total']}")
        if stats["hints"]:
            print(f"    hints: {stats['hints']}")
    print(f"E2E scorecard: {out_path.resolve()}")
    print("Next: SketchUp manual pass — fill e2e.rqs and e2e.failure_classes per image")


if __name__ == "__main__":
    main()
