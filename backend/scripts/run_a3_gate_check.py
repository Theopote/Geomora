"""Evaluate tiered Reconstruction Core gates against minimal-set metrics."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
sys.path.insert(0, str(BACKEND_ROOT))

from geomora_reconstruct.metrics.a3_gate import evaluate_reconstruction_gate  # noqa: E402
from geomora_reconstruct.metrics import evaluate_reconstruction  # noqa: E402
from geomora_reconstruct.prediction_enrichment import enrich_prediction  # noqa: E402

MINIMAL_SET = REPO_ROOT / "tests" / "reconstruction" / "minimal_set.json"
GT_DIR = REPO_ROOT / "tests" / "reconstruction" / "ground_truth"
DEFAULT_PRED_DIR = REPO_ROOT / "tests" / "reconstruction" / "baselines" / "current"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--minimal-set", type=Path, default=MINIMAL_SET)
    parser.add_argument("--ground-truth-dir", type=Path, default=GT_DIR)
    parser.add_argument("--prediction-dir", type=Path, default=DEFAULT_PRED_DIR)
    parser.add_argument(
        "--phase",
        choices=("prototype_bootstrap", "reconstruction_alpha", "product_beta", "r0_objective", "stage_a_core", "stage_a_full"),
        default="prototype_bootstrap",
        help="Gate phase to evaluate",
    )
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--refresh", action="store_true", help="Re-enrich predictions before evaluation")
    return parser.parse_args()


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_prediction(prediction_dir: Path, photo_id: str) -> Path | None:
    candidates = [
        prediction_dir / photo_id / "prediction.json",
        prediction_dir / f"{photo_id}.json",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def build_results(minimal_set: dict, args: argparse.Namespace) -> tuple[list[dict], dict[str, dict]]:
    truths: dict[str, dict] = {}
    rows: list[dict] = []
    for item in minimal_set["photos"]:
        photo_id = item["id"]
        truth_path = args.ground_truth_dir / f"{photo_id}.json"
        pred_path = resolve_prediction(args.prediction_dir, photo_id)
        row = {"photo_id": photo_id, "split": item.get("split"), "metrics": None}
        if not truth_path.exists():
            row["error"] = "missing_ground_truth"
            rows.append(row)
            continue
        truth = load_json(truth_path)
        truths[photo_id] = truth
        if pred_path is None:
            row["error"] = "missing_prediction"
            rows.append(row)
            continue
        prediction = load_json(pred_path)
        if args.refresh:
            enrich_prediction(prediction)
        row["metrics"] = evaluate_reconstruction(truth, prediction)
        row["prediction"] = str(pred_path)
        rows.append(row)
    return rows, truths


def print_report(report) -> None:
    print(f"{report.gate} maturity={report.maturity_claim} phase={report.phase} passed={report.passed}")
    for check in report.checks:
        status = "PASS" if check.passed else "FAIL"
        print(f"  [{status}] {check.id}: actual={check.actual} threshold={check.threshold}")
    if report.blockers:
        print("  Blockers:")
        for blocker in report.blockers:
            print(f"    - {blocker}")
    summary = report.summary
    print(
        "  Summary: "
        f"mean_rqs={summary.get('mean_rqs')} "
        f"mean_coverage={summary.get('mean_coverage')} "
        f"val_recall={summary.get('val_window_recall')} "
        f"holdout_generate_stable={summary.get('holdout_generate_stable')}"
    )


def main() -> int:
    args = parse_args()
    minimal_set = load_json(args.minimal_set)
    results, truths = build_results(minimal_set, args)
    report = evaluate_reconstruction_gate(minimal_set, results, truths=truths, phase=args.phase)

    payload = {
        "minimal_set": str(args.minimal_set),
        "prediction_dir": str(args.prediction_dir),
        "gate": report.to_dict(),
        "results": results,
    }
    out_path = args.output or (args.prediction_dir / f"reconstruction_gate_{args.phase}.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print_report(report)
    print(f"Gate report -> {out_path.resolve()}")
    return 0 if report.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
