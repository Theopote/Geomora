"""Batch-evaluate Reconstruction Metrics v1 over the minimal 5-photo set."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
sys.path.insert(0, str(BACKEND_ROOT))

from geomora_reconstruct.metrics import evaluate_reconstruction  # noqa: E402
from geomora_reconstruct.metrics.a3_gate import evaluate_a3_gate  # noqa: E402

MINIMAL_SET = REPO_ROOT / "tests" / "reconstruction" / "minimal_set.json"
GT_DIR = REPO_ROOT / "tests" / "reconstruction" / "ground_truth"
DEFAULT_PRED_DIR = REPO_ROOT / "tests" / "reconstruction" / "baselines" / "current"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--minimal-set", type=Path, default=MINIMAL_SET)
    parser.add_argument("--ground-truth-dir", type=Path, default=GT_DIR)
    parser.add_argument(
        "--prediction-dir",
        type=Path,
        default=DEFAULT_PRED_DIR,
        help="Directory with per-photo prediction.json or flat {photo_id}.json files",
    )
    parser.add_argument("--output", type=Path, default=None)
    return parser.parse_args()


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_prediction(prediction_dir: Path, photo_id: str) -> Path | None:
    candidates = [
        prediction_dir / photo_id / "prediction.json",
        prediction_dir / f"{photo_id}.json",
        REPO_ROOT / "tests" / "reconstruction" / "predictions" / f"{photo_id}.json",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def aggregate(results: list[dict], *, minimal_set: dict | None = None, truths: dict[str, dict] | None = None) -> dict:
    evaluated = [row for row in results if row.get("metrics")]
    coverages = [row["metrics"]["coverage"] for row in evaluated if row["metrics"].get("coverage") is not None]
    rqss = [row["metrics"]["rqs"] for row in evaluated if row["metrics"].get("rqs") is not None]
    full_coverage = [row for row in evaluated if row["metrics"].get("coverage") == 1.0]

    detection_rows = [row["metrics"]["detection"] for row in evaluated if row["metrics"].get("detection")]
    window_recalls = [row["window"]["recall"] for row in detection_rows if row.get("window")]
    window_precisions = [row["window"]["precision"] for row in detection_rows if row.get("window")]

    gate_report = None
    if minimal_set is not None:
        gate_report = evaluate_a3_gate(minimal_set, results, truths=truths, phase="r0_objective").to_dict()

    return {
        "photos": len(results),
        "evaluated": len(evaluated),
        "full_coverage_count": len(full_coverage),
        "mean_coverage": round(sum(coverages) / len(coverages), 4) if coverages else None,
        "mean_rqs": round(sum(rqss) / len(rqss), 1) if rqss else None,
        "mean_window_recall": round(sum(window_recalls) / len(window_recalls), 4) if window_recalls else None,
        "mean_window_precision": round(sum(window_precisions) / len(window_precisions), 4) if window_precisions else None,
        "gate_ready": len(full_coverage) == len(results) and len(results) > 0,
        "a3_gate_r0": gate_report,
    }


def main() -> int:
    args = parse_args()
    minimal = load_json(args.minimal_set)
    photo_ids = [item["id"] for item in minimal["photos"]]

    rows = []
    truths: dict[str, dict] = {}
    for photo_id in photo_ids:
        truth_path = args.ground_truth_dir / f"{photo_id}.json"
        pred_path = resolve_prediction(args.prediction_dir, photo_id)
        row = {"photo_id": photo_id, "ground_truth": str(truth_path), "prediction": None, "metrics": None}
        if not truth_path.exists():
            row["error"] = "missing_ground_truth"
            rows.append(row)
            continue
        if pred_path is None:
            row["error"] = "missing_prediction"
            rows.append(row)
            continue
        truth = load_json(truth_path)
        truths[photo_id] = truth
        prediction = load_json(pred_path)
        row["prediction"] = str(pred_path)
        row["metrics"] = evaluate_reconstruction(truth, prediction)
        rows.append(row)

    payload = {
        "minimal_set": str(args.minimal_set),
        "aggregate": aggregate(rows, minimal_set=minimal, truths=truths),
        "results": rows,
    }

    out_path = args.output or (args.prediction_dir / "metrics_aggregate.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    aggregate_summary = payload["aggregate"]
    gate = aggregate_summary.get("a3_gate_r0") or {}
    print(f"Metrics aggregate -> {out_path.resolve()}")
    print(
        f"  evaluated={aggregate_summary['evaluated']}/{aggregate_summary['photos']} "
        f"mean_rqs={aggregate_summary['mean_rqs']} "
        f"mean_window_recall={aggregate_summary['mean_window_recall']} "
        f"mean_coverage={aggregate_summary['mean_coverage']} "
        f"gate_ready={aggregate_summary['gate_ready']} "
        f"a3_gate_r0_passed={gate.get('passed')}"
    )
    for row in rows:
        metrics = row.get("metrics") or {}
        print(
            f"  {row['photo_id']}: rqs={metrics.get('rqs')} "
            f"coverage={metrics.get('coverage')} not_evaluated={metrics.get('not_evaluated')}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
