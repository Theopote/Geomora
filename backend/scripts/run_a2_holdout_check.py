"""A2 hold-out smoke diagnostic after failure-driven detection fixes.

This command is intentionally not a release gate. A non-empty detection proves
only that the pipeline ran; use Reconstruction Metrics v1 for A2/A3 decisions.

Example:
  cd backend
  .venv\\Scripts\\python scripts/run_a2_holdout_check.py
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
sys.path.insert(0, str(BACKEND_ROOT))

from geomora_detect.pipeline import detect_facade  # noqa: E402

MANIFEST_DEFAULT = REPO_ROOT / "examples" / "real_photos" / "benchmark" / "manifest.json"
E2E_DEFAULT = BACKEND_ROOT / "cache" / "benchmark_a1_e2e.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="A2 hold-out detection smoke diagnostic (not a gate)")
    parser.add_argument("--manifest", type=Path, default=MANIFEST_DEFAULT)
    parser.add_argument("--baseline", type=Path, default=E2E_DEFAULT)
    parser.add_argument("--method", default="auto")
    parser.add_argument("--split", default="holdout")
    return parser.parse_args()


def resolve_image_path(manifest: dict, file_name: str) -> Path:
    image_root = REPO_ROOT / manifest.get("image_root", "")
    return image_root / file_name


def infer_hints(window_count: int, door_count: int, confidence: float) -> list[str]:
    hints: list[str] = []
    if window_count == 0:
        hints.append("missed_window")
    if door_count > 0 and window_count == 0:
        hints.append("false_door")
    if confidence < 0.5:
        hints.append("opening_detection")
    return hints


def main() -> int:
    args = parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    baseline = json.loads(args.baseline.read_text(encoding="utf-8")) if args.baseline.exists() else {}

    entries = [entry for entry in manifest["images"] if entry["split"] == args.split]
    baseline_by_id = {row["id"]: row for row in baseline.get("results", [])}

    print(f"A2 hold-out check — method={args.method} — {len(entries)} images")
    print("-" * 72)

    pass_count = 0
    for entry in entries:
        image_path = resolve_image_path(manifest, entry["file"])
        result = detect_facade(str(image_path), method=args.method, return_overlay=False)
        windows = [element for element in result.elements if element.type == "window"]
        doors = [element for element in result.elements if element.type == "door"]
        passed = len(windows) >= 1  # Pipeline liveness only; never reconstruction quality.
        hints = infer_hints(len(windows), len(doors), result.confidence)
        if passed:
            pass_count += 1

        baseline_row = baseline_by_id.get(entry["id"], {})
        old_detect = baseline_row.get("detection", {})
        old_pass = old_detect.get("passed_smoke")
        delta = ""
        if old_pass is not None:
            delta = " (A1: PASS)" if old_pass else " (A1: FAIL)"

        status = "PASS" if passed else "FAIL"
        print(
            f"{entry['id']:10} {status:4}  w={len(windows)} d={len(doors)} "
            f"conf={result.confidence:.2f} method={result.method}{delta} hints={hints or ['none']}"
        )

    print("-" * 72)
    print(f"Smoke pass: {pass_count}/{len(entries)}")
    print("Diagnostic only: this result MUST NOT be used to pass A2 or A3.")
    print("Run Reconstruction Metrics v1 with reviewed ground truth for gate decisions.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
