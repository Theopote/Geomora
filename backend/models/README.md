# Geomora Detection Models

## Files

| File | Description |
|---|---|
| `detection_config.json` | Class names, thresholds, input size |
| `facade_yolo_v1.onnx` | YOLOv8n facade detector (window + door) — build via `docs/YOLO_TRAINING.md` |

## Build YOLO model

See **`docs/YOLO_TRAINING.md`** for training commands and **`docs/YOLO_LABELING.md`** for real-photo annotation.

```powershell
cd F:\development\Geomora\backend
.\.venv\Scripts\pip install -r requirements-dev.txt
.\.venv\Scripts\python scripts\train_yolo_facade.py
.\.venv\Scripts\python scripts\validate_yolo_facade.py
```

## Override model path

Set environment variable before starting the server:

```powershell
$env:GEOMORA_YOLO_MODEL = "D:\models\custom_facade.onnx"
```

Optional config override:

```powershell
$env:GEOMORA_DETECTION_CONFIG = "D:\models\custom_detection_config.json"
```

## Runtime

- **Production inference:** `onnxruntime` only (see `requirements.txt`)
- **Training:** `ultralytics` (see `requirements-dev.txt`)

When the ONNX file is missing, `method=auto` falls back to `contour_v1`.
