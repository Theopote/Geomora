# Geomora Perception Service (Phase 2 + 3)

Local Python service for facade rectification and element detection.

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
```

Response includes `elements[]`, `confidence`, `overlay_base64`.

## Tests

From repository root:

```powershell
py -m pytest tests/backend -q
```

## Notes

- Phase 2: auto rectify uses line detection + vanishing points + estimated facade quad.
- Phase 3: `contour_v1` detects dark rectangular openings on rectified images.
- For best results, **rectify first**, then detect. Use manual 4 corners when auto rectify fails.
- v0.4.0 uses OpenCV only; YOLO/SAM planned for Phase 3.5+.
