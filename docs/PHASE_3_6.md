# Phase 3.6 — SAM / Mask Refinement

**Status:** ✅ v0.35.0 (GrabCut + threshold bootstrap; optional MobileSAM ONNX path)

## Goal

Tighten window/door bounding boxes after YOLO / row / contour detection using **mask-based refinement** before Overlay review and IR mapping.

```text
Base detect (auto / yolo / row / contour)
      ↓
Mask refine (GrabCut + Otsu inside each prompt box)
      ↓
Tighter bbox_norm + optional green mask tint on overlay
```

## Workspace usage

1. Rectify facade
2. Detection → **SAM refine (Auto + mask)**
3. Overlay view shows refined boxes + light green mask tint
4. Review → Rationalize → Generate

## API

`POST /detect` with `method=sam_v1`

Response `method` is `sam_v1`. Debug fields:

| Field | Meaning |
|-------|---------|
| `base_method` | Detector used before refine (`yolo_v1`, `facade_row_v1`, …) |
| `refine_backend` | `grabcut_v1`, `threshold_v1`, or `prompt_only` |
| `refined_count` | Boxes changed vs prompt |

`GET /detect/capabilities` includes `sam_available: true`.

## Backends

| Backend | Requires model | Notes |
|---------|----------------|-------|
| `grabcut_v1` | No | Default; works on CPU |
| `threshold_v1` | No | Otsu inside ROI for dark windows / doors |
| `mobile_sam_v1.onnx` | Optional | Place in `backend/models/` or set `GEOMORA_SAM_MODEL` (future ONNX hook) |

Config: `backend/models/sam_config.json`

## CLI test

```powershell
cd F:\development\Geomora\backend
.\.venv\Scripts\python -m pytest ..\tests\backend\test_mask_refiner.py -q
```

## Files

| Path | Role |
|------|------|
| `geomora_detect/mask_refiner.py` | GrabCut + threshold refine |
| `geomora_detect/pipeline.py` | `sam_v1` method |
| `models/sam_config.json` | Refine parameters |

## Gate

- [x] `sam_v1` returns elements on synthetic rectified facade
- [x] Overlay includes mask tint
- [x] Workspace detection dropdown includes SAM refine
- [ ] Optional MobileSAM ONNX wired (model download separate)
