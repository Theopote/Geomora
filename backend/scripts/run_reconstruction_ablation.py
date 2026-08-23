"""Run deterministic A-E Reconstruction Core ablation on the minimal GT set."""
from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
sys.path.insert(0, str(BACKEND_ROOT))

from geomora_detect.pipeline import detect_facade  # noqa: E402
from geomora_reconstruct.ablation import (  # noqa: E402
    STAGES, build_stage_predictions, build_vlm_pair_predictions,
    evaluate_stages, summarize_stage, summarize_vlm_pair,
)
from geomora_reconstruct.vlm_evidence import read_evidence_cache  # noqa: E402

DEFAULT_SET = REPO_ROOT / "tests" / "reconstruction" / "minimal_set.json"
DEFAULT_OUT = BACKEND_ROOT / "runs" / "reconstruction_ablation"


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vlm-cache-dir", type=Path, required=True,
                        help="Required frozen <photo_id>.json VLM evidence cache; live cloud calls are forbidden")
    parser.add_argument("--minimal-set", type=Path, default=DEFAULT_SET)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--method", default="auto")
    parser.add_argument("--photo-id", action="append", dest="photo_ids")
    parser.add_argument("--expose-holdout-details", action="store_true",
                        help="Write per-photo holdout metrics/predictions (off by default to avoid tuning leakage)")
    return parser.parse_args()


def _metric_anchors(truth: dict) -> list[dict]:
    return [dict(item) for item in truth.get("metric_anchors") or [] if item.get("distance_mm") not in (None, "")]


def _fmt(value) -> str:
    return "—" if value is None else f"{value:.3f}" if isinstance(value, float) else str(value)


def _markdown(stages: list[dict], *, generated_at: str, vlm_pair: dict | None = None) -> str:
    lines = ["# Reconstruction Ablation", "", f"Generated: {generated_at}", "",
             "> Compare RQS only when coverage is comparable. Component columns are the primary ablation evidence.", "",
             "| Pipeline | RQS | Coverage | Storey | Bay | Geometry | Scale | Solver |",
             "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for row in stages:
        lines.append("| " + " | ".join([
            row["label"], _fmt(row["mean_rqs"]), _fmt(row["mean_coverage"]),
            _fmt(row["storey_accuracy"]), _fmt(row["bay_accuracy"]),
            _fmt(row["geometry_score"]), _fmt(row["scale_score"]), _fmt(row["solver_pass_rate"]),
        ]) + " |")
    lines.extend(["", "## Interpretation guardrails", "",
                  "- B measures raw cached VLM topology, not successful architectural fusion.",
                  "- C−B measures the value of the Understanding coordinator.",
                  "- D only affects photos with surveyed metric anchors.",
                  "- Holdout per-photo details are sealed unless explicitly requested.", ""])
    if vlm_pair:
        lines.extend(["## Paired VLM effect", "", "| Arm | RQS | Coverage | Storey | Bay | Geometry |",
                      "|---|---:|---:|---:|---:|---:|"])
        for arm in ("without_vlm", "with_vlm"):
            row = vlm_pair[arm]
            lines.append("| " + " | ".join([arm.replace("_", " "), _fmt(row["mean_rqs"]),
                         _fmt(row["mean_coverage"]), _fmt(row["storey_accuracy"]),
                         _fmt(row["bay_accuracy"]), _fmt(row["geometry_score"])]) + " |")
        delta = vlm_pair["delta_with_minus_without"]
        lines.append("| delta | " + " | ".join([_fmt(delta["mean_rqs"]), _fmt(delta["mean_coverage"]),
                     _fmt(delta["storey_accuracy"]), _fmt(delta["bay_accuracy"]), _fmt(delta["geometry_score"])]) + " |")
        lines.append("")
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    minimal = _json(args.minimal_set)
    manifest = _json(REPO_ROOT / minimal["manifest"])
    entries = {item["id"]: item for item in manifest["images"]}
    selected = args.photo_ids or [item["id"] for item in minimal["photos"]]
    args.out.mkdir(parents=True, exist_ok=True)
    stage_rows = {stage_id: [] for stage_id, _label in STAGES}
    vlm_pair_rows = {"without_vlm": [], "with_vlm": []}

    for photo_id in selected:
        entry = entries[photo_id]
        truth = _json(REPO_ROOT / minimal["ground_truth_dir"] / f"{photo_id}.json")
        evidence_path = args.vlm_cache_dir / f"{photo_id}.json"
        if not evidence_path.exists():
            raise FileNotFoundError(f"Frozen VLM evidence missing for {photo_id}: {evidence_path}")
        evidence = read_evidence_cache(evidence_path)
        if evidence.photo_id != photo_id:
            raise ValueError(f"VLM evidence photo_id mismatch: {evidence_path}")
        image_path = REPO_ROOT / manifest["image_root"] / entry["file"]
        detection = detect_facade(str(image_path), method=args.method, return_overlay=False)
        predictions = build_stage_predictions(
            photo_id, detection, evidence=evidence, metric_anchors=_metric_anchors(truth),
        )
        metrics = evaluate_stages(truth, predictions)
        pair_predictions = build_vlm_pair_predictions(photo_id, detection, evidence=evidence)
        pair_metrics = evaluate_stages(truth, pair_predictions)
        expose = entry["split"] != "holdout" or args.expose_holdout_details
        for stage_id, _label in STAGES:
            stage_rows[stage_id].append({"photo_id": photo_id, "split": entry["split"], "metrics": metrics[stage_id]})
            if expose:
                stage_dir = args.out / "predictions" / stage_id
                stage_dir.mkdir(parents=True, exist_ok=True)
                (stage_dir / f"{photo_id}.json").write_text(
                    json.dumps(predictions[stage_id], ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
                )
        for arm in vlm_pair_rows:
            vlm_pair_rows[arm].append({"photo_id": photo_id, "split": entry["split"], "metrics": pair_metrics[arm]})

    summaries = [summarize_stage(stage_id, stage_rows[stage_id]) for stage_id, _ in STAGES]
    if not args.expose_holdout_details:
        for summary in summaries:
            summary["results"] = [
                row if row["split"] != "holdout" else {"photo_id": row["photo_id"], "split": "holdout", "metrics": "sealed"}
                for row in summary["results"]
            ]
    generated_at = datetime.now(UTC).isoformat()
    vlm_pair = summarize_vlm_pair(vlm_pair_rows)
    report = {
        "schema_version": "reconstruction-ablation-v1", "generated_at": generated_at,
        "method": args.method, "vlm_mode": "frozen_cache_only", "photo_count": len(selected),
        "holdout_details_exposed": args.expose_holdout_details, "stages": summaries,
        "paired_vlm_effect": vlm_pair,
    }
    (args.out / "ablation_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (args.out / "ablation_report.md").write_text(_markdown(summaries, generated_at=generated_at, vlm_pair=vlm_pair), encoding="utf-8")
    with (args.out / "ablation_summary.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        fields = ["stage", "label", "mean_rqs", "mean_coverage", "storey_accuracy", "bay_accuracy", "geometry_score", "scale_score", "solver_pass_rate"]
        writer = csv.DictWriter(handle, fieldnames=fields); writer.writeheader()
        for row in summaries:
            writer.writerow({key: row.get(key) for key in fields})
    print(_markdown(summaries, generated_at=generated_at, vlm_pair=vlm_pair))
    print(f"\nReports saved to {args.out.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
