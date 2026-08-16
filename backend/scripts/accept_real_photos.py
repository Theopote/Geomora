"""Batch acceptance runner for rectified facade detection on real photos.

Examples:
  cd backend
  .venv\\Scripts\\python scripts/accept_real_photos.py --images ..\\examples\\real_photos\\rectified
  .venv\\Scripts\\python scripts/accept_real_photos.py --dataset data\\facade_yolo_custom --split val
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from geomora_detect.acceptance_metrics import (  # noqa: E402
    ImageEvaluation,
    discover_dataset_images,
    discover_images,
    evaluate_elements,
    parse_yolo_label_file,
    resolve_label_path,
)
from geomora_detect.pipeline import detect_facade  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate facade detection on real rectified photos")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--images", type=Path, help="Folder of rectified images")
    source.add_argument("--dataset", type=Path, help="YOLO dataset root with train/val splits")
    parser.add_argument("--split", choices=("train", "val"), default=None, help="Dataset split to evaluate")
    parser.add_argument("--method", default="auto", help="Detection method (auto, yolo_v1, facade_row_v1, contour_v1)")
    parser.add_argument("--iou", type=float, default=0.5, help="IoU threshold for labeled metrics")
    parser.add_argument("--window-recall-min", type=float, default=0.7)
    parser.add_argument("--window-precision-min", type=float, default=0.6)
    parser.add_argument("--door-recall-min", type=float, default=0.5)
    parser.add_argument("--door-precision-min", type=float, default=0.5)
    parser.add_argument("--min-windows", type=int, default=1, help="Smoke threshold when labels are absent")
    parser.add_argument("--report", type=Path, default=None, help="Write JSON report to this path")
    parser.add_argument("--fail-fast", action="store_true", help="Exit 1 on first failed image")
    return parser.parse_args()


def evaluate_image(
    image_path: Path,
    *,
    label_path: Path | None,
    method: str,
    args: argparse.Namespace,
) -> ImageEvaluation:
    result = detect_facade(str(image_path), method=method, return_overlay=False)
    windows = [element for element in result.elements if element.type == "window"]
    doors = [element for element in result.elements if element.type == "door"]

    evaluation = ImageEvaluation(
        image_path=str(image_path.resolve()),
        label_path=str(label_path.resolve()) if label_path else None,
        method=result.method,
        confidence=result.confidence,
        window_count=len(windows),
        door_count=len(doors),
        scale_hint=result.scale_hint,
    )

    if label_path and label_path.exists():
        ground_truth = parse_yolo_label_file(label_path)
        metrics, passed, notes = evaluate_elements(
            result.elements,
            ground_truth,
            iou_threshold=args.iou,
            window_recall_min=args.window_recall_min,
            window_precision_min=args.window_precision_min,
            door_recall_min=args.door_recall_min,
            door_precision_min=args.door_precision_min,
        )
        evaluation.metrics = metrics
        evaluation.passed = passed
        evaluation.notes = notes
        return evaluation

    notes: list[str] = []
    passed = len(windows) >= args.min_windows
    if not passed:
        notes.append(f"expected at least {args.min_windows} windows, found {len(windows)}")
    evaluation.passed = passed
    evaluation.notes = notes
    return evaluation


def collect_targets(args: argparse.Namespace) -> list[tuple[Path, Path | None]]:
    if args.images:
        root = args.images.resolve()
        if not root.exists():
            raise FileNotFoundError(f"Image folder not found: {root}")
        return [(path, resolve_label_path(path)) for path in discover_images(root)]

    dataset_root = args.dataset.resolve()
    if not dataset_root.exists():
        raise FileNotFoundError(f"Dataset root not found: {dataset_root}")
    return discover_dataset_images(dataset_root, args.split)


def print_summary(results: list[ImageEvaluation]) -> None:
    passed = sum(1 for result in results if result.passed)
    labeled = [result for result in results if result.metrics]
    print(f"Images: {len(results)} | Passed: {passed}/{len(results)}")

    for result in results:
        status = "PASS" if result.passed else "FAIL"
        line = (
            f"[{status}] {Path(result.image_path).name} "
            f"method={result.method} windows={result.window_count} doors={result.door_count} "
            f"conf={result.confidence:.3f}"
        )
        if result.notes:
            line += " | " + "; ".join(result.notes)
        print(line)

    if labeled:
        window_tp = sum(result.metrics["window"].true_positives for result in labeled if result.metrics)
        window_fp = sum(result.metrics["window"].false_positives for result in labeled if result.metrics)
        window_fn = sum(result.metrics["window"].false_negatives for result in labeled if result.metrics)
        door_tp = sum(result.metrics["door"].true_positives for result in labeled if result.metrics)
        door_fp = sum(result.metrics["door"].false_positives for result in labeled if result.metrics)
        door_fn = sum(result.metrics["door"].false_negatives for result in labeled if result.metrics)

        def aggregate(tp: int, fp: int, fn: int) -> tuple[float, float]:
            precision = tp / (tp + fp) if (tp + fp) else 1.0
            recall = tp / (tp + fn) if (tp + fn) else 1.0
            return precision, recall

        window_p, window_r = aggregate(window_tp, window_fp, window_fn)
        door_p, door_r = aggregate(door_tp, door_fp, door_fn)
        print(
            f"Labeled aggregate | window P/R={window_p:.3f}/{window_r:.3f} "
            f"| door P/R={door_p:.3f}/{door_r:.3f} ({len(labeled)} images)"
        )


def main() -> None:
    args = parse_args()
    targets = collect_targets(args)
    if not targets:
        raise SystemExit("No images found.")

    results: list[ImageEvaluation] = []
    for image_path, label_path in targets:
        evaluation = evaluate_image(image_path, label_path=label_path, method=args.method, args=args)
        results.append(evaluation)
        if args.fail_fast and not evaluation.passed:
            print_summary(results)
            raise SystemExit(1)

    print_summary(results)

    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "method_requested": args.method,
            "results": [result.to_dict() for result in results],
            "passed": sum(1 for result in results if result.passed),
            "total": len(results),
        }
        args.report.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        print(f"Report written: {args.report.resolve()}")

    if any(not result.passed for result in results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
