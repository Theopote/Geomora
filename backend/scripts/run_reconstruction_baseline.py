"""Run current pipeline on the minimal 5-photo set and save stage artifacts."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
sys.path.insert(0, str(BACKEND_ROOT))

from geomora_detect.image_io import imread_bgr, imwrite_bgr  # noqa: E402
from geomora_detect.overlays import draw_overlay  # noqa: E402
from geomora_detect.pipeline import detect_facade  # noqa: E402
from geomora_detect.facade_row_detector import detect_facade_row_elements  # noqa: E402
from geomora_detect.yolo_detector import detect_yolo_elements, model_available  # noqa: E402
from geomora_reconstruct.export import detection_to_prediction  # noqa: E402
from geomora_reconstruct.metrics import evaluate_reconstruction  # noqa: E402
from geomora_reconstruct.prediction_enrichment import enrich_prediction  # noqa: E402
from geomora_reconstruct.observations.adapters import (  # noqa: E402
    detection_result_to_observations,
    facade_row_to_observations,
    yolo_to_observations,
)
from geomora_reconstruct.observations.fusion import fuse_observation_graphs  # noqa: E402
from geomora_reconstruct.observations.vlm_adapter import vlm_evidence_to_observations  # noqa: E402
from geomora_reconstruct.vlm_evidence import read_evidence_cache  # noqa: E402

MINIMAL_SET = REPO_ROOT / "tests" / "reconstruction" / "minimal_set.json"
DEFAULT_BASELINE = REPO_ROOT / "tests" / "reconstruction" / "baselines" / "current"
GT_DIR = REPO_ROOT / "tests" / "reconstruction" / "ground_truth"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--minimal-set", type=Path, default=MINIMAL_SET)
    parser.add_argument("--out", type=Path, default=DEFAULT_BASELINE)
    parser.add_argument("--method", default="auto")
    parser.add_argument("--photo-id", action="append", dest="photo_ids")
    parser.add_argument(
        "--vlm-cache-dir",
        type=Path,
        help="Optional directory containing <photo_id>.json architectural evidence",
    )
    return parser.parse_args()


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_text(*args: str) -> str | None:
    try:
        return subprocess.run(
            ["git", *args], cwd=REPO_ROOT, check=True, capture_output=True, text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def source_changes(out_dir: Path) -> list[str]:
    """Return dirty source inputs while excluding generated benchmark artifacts/caches."""
    rows = (git_text("status", "--porcelain") or "").splitlines()
    try:
        out_prefix = out_dir.resolve().relative_to(REPO_ROOT).as_posix().rstrip("/") + "/"
    except ValueError:
        out_prefix = ""
    kept = []
    for row in rows:
        path = row[3:].replace("\\", "/") if len(row) > 3 else row
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        if (out_prefix and path.startswith(out_prefix)) or "/__pycache__/" in f"/{path}/":
            continue
        if path.startswith("tests/reconstruction/baselines/archive/"):
            continue
        kept.append(row)
    return kept


def resolve_image_path(manifest: dict, file_name: str) -> Path:
    return REPO_ROOT / manifest["image_root"] / file_name


def entry_by_id(manifest: dict, photo_id: str) -> dict:
    for entry in manifest["images"]:
        if entry["id"] == photo_id:
            return entry
    raise KeyError(f"photo_id not found in manifest: {photo_id}")


def write_overlay(image_path: Path, detection, out_path: Path) -> None:
    image = imread_bgr(image_path)
    overlay = draw_overlay(image, detection.elements)
    imwrite_bgr(out_path, overlay)


def load_vlm_evidence(photo_id: str, vlm_cache_dir: Path | None):
    if vlm_cache_dir is None:
        return None
    evidence_path = vlm_cache_dir / f"{photo_id}.json"
    if not evidence_path.exists():
        return None
    evidence = read_evidence_cache(evidence_path)
    if evidence.photo_id != photo_id:
        raise ValueError(f"VLM evidence photo_id mismatch: {evidence_path}")
    return evidence


def build_observation_graph(photo_id: str, image, *, architectural_evidence=None) -> dict:
    graphs = []
    row_result = detect_facade_row_elements(image, return_overlay=False)
    graphs.append(facade_row_to_observations(row_result, photo_id=photo_id))
    if model_available():
        yolo_result = detect_yolo_elements(image, return_overlay=False)
        graphs.append(yolo_to_observations(yolo_result, photo_id=photo_id))
    if architectural_evidence is not None:
        graphs.append(
            vlm_evidence_to_observations(
                architectural_evidence,
                image_width=int(image.shape[1]),
                image_height=int(image.shape[0]),
            )
        )
    if len(graphs) == 1:
        return detection_result_to_observations(row_result, photo_id=photo_id).to_dict()
    return fuse_observation_graphs(*graphs).to_dict()


def run_photo(
    photo_id: str,
    manifest: dict,
    *,
    method: str,
    out_root: Path,
    vlm_cache_dir: Path | None = None,
) -> dict:
    entry = entry_by_id(manifest, photo_id)
    image_path = resolve_image_path(manifest, entry["file"])
    photo_dir = out_root / photo_id
    photo_dir.mkdir(parents=True, exist_ok=True)

    gt_path = GT_DIR / f"{photo_id}.json"
    truth = load_json(gt_path) if gt_path.exists() else None
    # Surveyed user anchors are reconstruction input, not hidden evaluation
    # labels. Other GT fields remain isolated from the prediction pipeline.
    metric_anchors = [
        dict(anchor)
        for anchor in ((truth or {}).get("metric_anchors") or [])
        if anchor.get("distance_mm") not in (None, "")
    ]

    detection = detect_facade(str(image_path), method=method, return_overlay=False)
    image = imread_bgr(image_path)
    architectural_evidence = load_vlm_evidence(photo_id, vlm_cache_dir)
    observation_graph = build_observation_graph(
        photo_id,
        image,
        architectural_evidence=architectural_evidence,
    )

    rectification = {
        "photo_id": photo_id,
        "image_path": str(image_path),
        "method": "existing_rectified_cache",
        "notes": "Rectification artifact not re-run in baseline exporter v0.1",
    }
    detections = detection.to_dict()
    prediction = detection_to_prediction(
        photo_id,
        detection,
        metric_anchors=metric_anchors,
        architectural_evidence=architectural_evidence,
    )
    enrich_prediction(prediction, detection, export_ir=True)
    architectural_ir = prediction.get("architectural_ir") or {
        "photo_id": photo_id,
        "status": "not_run",
        "notes": "IR export requires scale_hint from detection",
    }
    rationalized = {
        "photo_id": photo_id,
        "status": "topology_geometry_inferred",
        "topology": prediction.get("topology"),
        "geometry": prediction.get("geometry"),
        "openings": prediction.get("openings"),
        "rationalization_before": prediction.get("rationalization_before"),
        "rationalization_after": prediction.get("rationalization_after"),
        "sketchup": prediction.get("sketchup"),
        "notes": "Understanding v0.1 + heuristic rationalization/sketchup checks",
    }

    metrics_result = None
    if truth is not None:
        metrics_result = evaluate_reconstruction(truth, prediction)

    preview_path = photo_dir / "preview.png"
    write_overlay(image_path, detection, preview_path)

    (photo_dir / "rectification.json").write_text(
        json.dumps(rectification, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (photo_dir / "detections.json").write_text(
        json.dumps(detections, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (photo_dir / "observation_graph.json").write_text(
        json.dumps(observation_graph, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (photo_dir / "rationalized.json").write_text(
        json.dumps(rationalized, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (photo_dir / "architectural_ir.json").write_text(
        json.dumps(architectural_ir, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (photo_dir / "prediction.json").write_text(
        json.dumps(prediction, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    if metrics_result is not None:
        (photo_dir / "reconstruction_metrics.json").write_text(
            json.dumps(metrics_result, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    return {
        "photo_id": photo_id,
        "split": entry["split"],
        "category": entry.get("category", ""),
        "detection_method": detection.method,
        "window_count": len([element for element in detection.elements if element.type == "window"]),
        "door_count": len([element for element in detection.elements if element.type == "door"]),
        "metrics": metrics_result,
        "preview": str(preview_path),
    }


def main() -> int:
    args = parse_args()
    minimal = load_json(args.minimal_set)
    manifest = load_json(REPO_ROOT / minimal["manifest"])
    photo_ids = args.photo_ids or [item["id"] for item in minimal["photos"]]

    args.out.mkdir(parents=True, exist_ok=True)
    results = []
    for photo_id in photo_ids:
        results.append(
            run_photo(
                photo_id,
                manifest,
                method=args.method,
                out_root=args.out,
                vlm_cache_dir=args.vlm_cache_dir,
            )
        )

    generated_at = datetime.now(UTC).isoformat()
    summary = {
        "generated_at": generated_at,
        "method": args.method,
        "photos": len(results),
        "results": results,
    }
    (args.out / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    gt_hashes = {
        photo_id: sha256(GT_DIR / f"{photo_id}.json")
        for photo_id in photo_ids
    }
    dirty_paths = source_changes(args.out)
    freeze_manifest = {
        "schema_version": "reconstruction-baseline-freeze-v1",
        "generated_at": generated_at,
        "source_commit": git_text("rev-parse", "HEAD"),
        "source_worktree_clean": not dirty_paths,
        "source_worktree_changes": dirty_paths,
        "generated_artifact_changes_omitted": True,
        "method": args.method,
        "minimal_set": str(args.minimal_set.relative_to(REPO_ROOT)),
        "minimal_set_sha256": sha256(args.minimal_set),
        "photo_ids": photo_ids,
        "ground_truth_sha256": gt_hashes,
        "vlm_cache": str(args.vlm_cache_dir) if args.vlm_cache_dir else None,
    }
    (args.out / "freeze_manifest.json").write_text(
        json.dumps(freeze_manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(f"Baseline saved to {args.out.resolve()}")
    for row in results:
        metrics = row.get("metrics") or {}
        coverage = metrics.get("coverage")
        rqs = metrics.get("rqs")
        not_eval = metrics.get("not_evaluated", [])
        print(
            f"  {row['photo_id']}: w={row['window_count']} d={row['door_count']} "
            f"rqs={rqs} coverage={coverage} not_evaluated={not_eval}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
