# Geomora Perception Service (Phase 2–6)

Local Python service for facade rectification, detection, and multi-view registration.

## Setup

```powershell
cd F:\development\Geomora\backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Run server

```powershell
uvicorn geomora_rectify.server:app --host 127.0.0.1 --port 8765
```

Health check: http://127.0.0.1:8765/health

## CLI (no server)

```powershell
python run_rectify.py path\to\facade.jpg -o rectified.jpg
python run_rectify.py path\to\facade.jpg --corners "[[80,420],[560,380],[520,80],[120,120]]"
```

## API

```http
POST /rectify
Content-Type: multipart/form-data

image: <file>
corners: optional JSON string [[x,y],...]  (4 points)
```

Response includes `rectified_image_base64`, `homography`, `vanishing_points`, `confidence`.

```http
POST /detect
Content-Type: multipart/form-data

image: <file>
method: auto | yolo_v1 | contour_v1   # optional
```

Response includes `elements[]`, `confidence`, `overlay_base64`, `method`.

## YOLO model (Phase 3.5)

```powershell
pip install -r requirements-dev.txt
python scripts/train_yolo_facade.py
```

See `models/README.md`. Without `facade_yolo_v1.onnx`, `method=auto` uses `contour_v1`.

```http
POST /multiview/register
Content-Type: multipart/form-data

primary: <file>
secondary: <file>
```

Returns homography mapping secondary → primary pixels, match/inlier counts, and view metadata.

```http
POST /multiview/fuse
Content-Type: multipart/form-data

primary: <file>
secondary: <file>
homography: optional JSON 3x3 matrix
method: auto | yolo_v1 | contour_v1
```

Detects openings on both views, warps secondary boxes to primary, fuses with depth-weighted NMS (`multiview_fusion_v1`).

```http
GET /multiview/capabilities

POST /multiview/register
method: auto | feature_homography_v1 | colmap_sparse_v1

POST /multiview/fuse
depth_method: auto | gradient_laplacian_v1 | midas_v21_v1
register_method: auto | feature_homography_v1 | colmap_sparse_v1
```

Optional MiDaS model:

```bat
.venv\Scripts\python.exe scripts\download_midas_model.py
```

COLMAP: install the CLI and ensure `colmap` is on PATH for `colmap_sparse_v1`.

## Tests

From repository root:

```powershell
py -m pytest tests/backend -q
```

## Notes

- Phase 2: auto rectify uses line detection + vanishing points + estimated facade quad.
- Phase 3: `contour_v1` (OpenCV) or `yolo_v1` (ONNX) — `method=auto` prefers YOLO when model exists.
- For best results, **rectify first**, then detect. Use manual 4 corners when auto rectify fails.
