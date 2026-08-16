"""Train Geomora facade YOLO detector and export ONNX for SketchUp plugin.

Usage:
  cd backend
  .venv\\Scripts\\pip install -r requirements-dev.txt
  .venv\\Scripts\\python scripts/train_yolo_facade.py

Custom annotated photos (YOLO format):
  backend/data/facade_yolo_custom/
    train/images/*.jpg
    train/labels/*.txt
    val/images/*.jpg
    val/labels/*.txt

  .venv\\Scripts\\python scripts/train_yolo_facade.py --custom-dataset data/facade_yolo_custom
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))
MODELS_DIR = BACKEND_ROOT / "models"
DATASET_ROOT = BACKEND_ROOT / "data" / "facade_yolo"
ONNX_OUTPUT = MODELS_DIR / "facade_yolo_v1.onnx"
CONFIG_OUTPUT = MODELS_DIR / "detection_config.json"
DEFAULT_CUSTOM = BACKEND_ROOT / "data" / "facade_yolo_custom"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train Geomora facade YOLO and export ONNX")
    parser.add_argument("--epochs", type=int, default=60, help="Training epochs")
    parser.add_argument("--batch", type=int, default=16, help="Batch size")
    parser.add_argument("--imgsz", type=int, default=640, help="Training image size")
    parser.add_argument("--synthetic-train", type=int, default=240, help="Random synthetic train images")
    parser.add_argument("--synthetic-val", type=int, default=40, help="Random synthetic val images")
    parser.add_argument("--fixture-train", type=int, default=80, help="Augmented canonical fixture train images")
    parser.add_argument("--fixture-val", type=int, default=20, help="Augmented canonical fixture val images")
    parser.add_argument("--custom-dataset", type=Path, default=None, help="Optional YOLO dataset root to merge")
    parser.add_argument("--model", default="yolov8n.pt", help="Ultralytics base weights")
    parser.add_argument("--dataset-dir", type=Path, default=DATASET_ROOT, help="Generated dataset output dir")
    parser.add_argument("--run-name", default="facade_yolo_v1", help="Ultralytics run name")
    parser.add_argument("--skip-train", action="store_true", help="Only build dataset")
    parser.add_argument("--export-pt", type=Path, default=None, help="Export existing .pt to ONNX without training")
    return parser.parse_args()


def write_detection_config(onnx_path: Path, metrics: dict | None = None) -> None:
    config = {
        "model_file": onnx_path.name,
        "input_size": 640,
        "class_names": ["window", "door"],
        "confidence_threshold": 0.30,
        "iou_threshold": 0.45,
    }
    if metrics:
        config["training_metrics"] = metrics
    CONFIG_OUTPUT.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")


def export_onnx(weights_path: Path, imgsz: int) -> Path:
    from ultralytics import YOLO

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    export_model = YOLO(str(weights_path))
    export_model.export(format="onnx", imgsz=imgsz, simplify=True, opset=12)

    exported = weights_path.with_suffix(".onnx")
    if not exported.exists():
        raise FileNotFoundError(f"ONNX export missing: {exported}")

    shutil.copy2(exported, ONNX_OUTPUT)
    print(f"Exported ONNX model -> {ONNX_OUTPUT}")
    return ONNX_OUTPUT


def train_and_export(args: argparse.Namespace) -> Path:
    from geomora_detect.dataset_builder import build_dataset

    custom_root = args.custom_dataset

    def _has_custom_images(root: Path) -> bool:
        for split in ("train", "val"):
            images = root / split / "images"
            if images.exists() and any(images.iterdir()):
                return True
        return False

    if custom_root is None and DEFAULT_CUSTOM.exists() and _has_custom_images(DEFAULT_CUSTOM):
        custom_root = DEFAULT_CUSTOM
        print(f"Merging custom dataset: {custom_root}")

    yaml_path = build_dataset(
        args.dataset_dir,
        synthetic_train=args.synthetic_train,
        synthetic_val=args.synthetic_val,
        fixture_train=args.fixture_train,
        fixture_val=args.fixture_val,
        custom_root=custom_root,
        clean=True,
    )
    print(f"Dataset written: {yaml_path}")

    if args.skip_train:
        return ONNX_OUTPUT

    from ultralytics import YOLO

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    model = YOLO(args.model)
    results = model.train(
        data=str(yaml_path),
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        patience=15,
        project=str(BACKEND_ROOT / "runs"),
        name=args.run_name,
        exist_ok=True,
        verbose=True,
    )

    best_weights = Path(results.save_dir) / "weights" / "best.pt"
    if not best_weights.exists():
        raise FileNotFoundError(f"Training did not produce weights: {best_weights}")

    metrics = {}
    if hasattr(results, "results_dict") and results.results_dict:
        metrics = {key: float(value) for key, value in results.results_dict.items() if isinstance(value, (int, float))}

    onnx_path = export_onnx(best_weights, args.imgsz)
    write_detection_config(onnx_path, metrics)
    print(f"Updated detection config -> {CONFIG_OUTPUT}")
    return onnx_path


def main() -> None:
    args = parse_args()

    if args.export_pt:
        onnx_path = export_onnx(args.export_pt, args.imgsz)
        write_detection_config(onnx_path)
        print(f"Done. Model ready at {onnx_path}")
        return

    path = train_and_export(args)
    print(f"Done. Model ready at {path}")


if __name__ == "__main__":
    main()
