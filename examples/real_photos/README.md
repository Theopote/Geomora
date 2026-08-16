# Real building photos (Stage A benchmark)

**Milestone:** A1 — see `docs/ROADMAP.md` and `docs/REAL_PHOTO_ACCEPTANCE.md`.

## Layout

```text
benchmark/manifest.json   # 20 photos, splits, categories (in git)
perspective/              # Original photos (gitignored)
rectified/                # Local rectified copies (gitignored)
```

## A1 workflow

1. Place originals in `perspective/` (or use existing `backend/cache/real_photo_desktop_src/`)
2. Rectify in SketchUp Workspace → save to `backend/cache/real_photo_desktop_rectified/`
3. Run detection baseline:

```powershell
cd F:\development\Geomora\backend
.\.venv\Scripts\python scripts\run_real_photo_benchmark.py
.\.venv\Scripts\python scripts\accept_real_photos.py --images cache\real_photo_desktop_rectified --method auto --report cache\benchmark_a1_detection.json
```

4. Open `cache/real_photo_review/index.html` for P0-first visual review
5. SketchUp E2E pass on all 20 manifest images — fill RQS in `cache/benchmark_a1_e2e.json`

## Splits

| Split | Count | Rule |
|-------|-------|------|
| train | 10 | Export YOLO labels, retrain OK |
| val | 5 | Metrics only |
| hold-out | 5 | **Never train** — final gate |

Hold-out IDs: `photo_16` … `photo_20` in `benchmark/manifest.json`.
