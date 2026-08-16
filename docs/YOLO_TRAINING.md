# Geomora Facade YOLO Training

Train the local `yolo_v1` detector used by **Detect Elements** in the Workspace.

## Prerequisites

```powershell
cd F:\development\Geomora\backend
.\.venv\Scripts\pip install -r requirements.txt
.\.venv\Scripts\pip install -r requirements-dev.txt
```

## Quick train (synthetic + canonical fixture)

```powershell
cd F:\development\Geomora\backend
.\.venv\Scripts\python scripts\train_yolo_facade.py
```

This builds:

- 240 random synthetic rectified facades (train)
- 80 augmented copies of the canonical 4-window + door scene (train)
- 40 + 20 validation images

Outputs:

- `backend/models/facade_yolo_v1.onnx`
- `backend/models/detection_config.json` (confidence threshold 0.30)

## Add real building photos

Prepare YOLO labels for **rectified** facade images (after Workspace Rectify):

```text
backend/data/facade_yolo_custom/
  train/images/photo_001.jpg
  train/labels/photo_001.txt
  val/images/photo_002.jpg
  val/labels/photo_002.txt
```

Label format (per line): `class cx cy w h` (normalized 0–1)

| Class ID | Type |
|----------|------|
| 0 | window |
| 1 | door |

Train with custom data merged:

```powershell
.\.venv\Scripts\python scripts\train_yolo_facade.py --custom-dataset data\facade_yolo_custom --epochs 80
```

If `data/facade_yolo_custom` exists, it is merged automatically.

## Validate exported model

```powershell
.\.venv\Scripts\python scripts\validate_yolo_facade.py
```

Expect ≥3 windows and ≥1 door on the canonical rectified synthetic scene.

## SketchUp usage

1. Restart backend: `start_server.bat`
2. Rebuild plugin if needed: `build_rbz.ps1`
3. Workspace → Detection: **YOLO** or **Auto**

## Tips for real photos

1. Always **Rectify Facade** before Detect
2. Label only the opening rectangles (glass/door panel), not frames
3. Start with 10–20 rectified photos; retrain iteratively
4. Use Overlay in Workspace to fix false boxes — export corrections as new labels for the next train round

## CLI options

```text
--epochs 60
--synthetic-train 240
--fixture-train 80
--custom-dataset path
--model yolov8n.pt
--skip-train          # only build dataset
--export-pt path.pt   # export ONNX without retraining
```
