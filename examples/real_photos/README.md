# Real building photos (local acceptance)

Place your **local** test photos here. These paths are for manual / CLI acceptance — do not commit private photos unless your team policy allows it.

```text
perspective/    # Original photos → load in SketchUp Workspace
rectified/      # Optional pre-rectified images → CLI batch detect
```

## SketchUp workflow

See **`docs/REAL_PHOTO_ACCEPTANCE.md`** §3.

## CLI smoke test (rectified folder)

```powershell
cd F:\development\Geomora\backend
.\.venv\Scripts\python scripts\accept_real_photos.py --images ..\examples\real_photos\rectified --method auto
```

## CLI with labels

Export labels from Workspace into `backend/data/facade_yolo_custom/`, then:

```powershell
.\.venv\Scripts\python scripts\accept_real_photos.py --dataset data\facade_yolo_custom --split val --report cache\real_photo_acceptance.json
```
