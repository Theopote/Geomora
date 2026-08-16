# Geomora Example Fixtures

Test assets for manual acceptance and backend CLI checks.

## Files

| File | Purpose |
|---|---|
| `facade_phase0.json` | Phase 0 IR fixture — Load Phase 0 Template in workspace |
| `facade_perspective_synthetic.jpg` | Synthetic oblique facade for rectification tests |
| `generate_rectified_fixture.py` | Generates `facade_rectified_synthetic.jpg` for detection tests |
| `real_photos/` | Local real building photos — see `docs/REAL_PHOTO_ACCEPTANCE.md` |

## Regenerate synthetic images

```powershell
cd F:\development\Geomora\backend
.\.venv\Scripts\activate
python ..\examples\generate_perspective_fixture.py
python ..\examples\generate_rectified_fixture.py
```

## Suggested workflow (Stage A acceptance)

1. Start backend: `backend\start_server.bat`
2. Install latest `dist\geomora.rbz` in SketchUp
3. Open Workspace → **Load Reference Image** → choose `facade_perspective_synthetic.jpg`
4. On **Original** view, drag the four corner handles to frame the facade
5. **Rectify Facade** → switch to **Rectified** and confirm fronto-parallel result
6. **Detect Elements** (optional) → **Overlay** to delete false boxes or draw missing windows
7. Set door width to `0` if no door → **Validate** → **Generate**

For real building photos, see **`docs/REAL_PHOTO_ACCEPTANCE.md`**.

## CLI batch acceptance (optional)

```powershell
cd F:\development\Geomora\backend
.\.venv\Scripts\python scripts\validate_yolo_facade.py
.\.venv\Scripts\python scripts\accept_real_photos.py --images ..\examples\real_photos\rectified --method auto
.\.venv\Scripts\python scripts\accept_real_photos.py --dataset data\facade_yolo_custom --split val --report cache\real_photo_acceptance.json
```
