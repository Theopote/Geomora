# Phase 3.6 — SAM / Mask Refinement

**Status:** ✅ v0.35.1 (MobileSAM ONNX + GrabCut fallback)

## Goal

Tighten window/door bounding boxes after detection using mask segmentation.

## Backends (priority)

| Backend | Model required | Notes |
|---------|----------------|-------|
| `mobile_sam_v1` | Encoder + decoder ONNX | Best quality; ~43 MB download |
| `grabcut_v1` | No | CPU fallback |
| `threshold_v1` | No | Otsu inside ROI |

## Download MobileSAM ONNX

```powershell
cd F:\development\Geomora\backend
.\.venv\Scripts\python scripts\download_mobile_sam_onnx.py
```

Files land in `backend/models/`:

| File | Role |
|------|------|
| `mobile_sam_image_encoder.onnx` | ViT-T encoder (~27 MB) |
| `sam_mask_decoder_single.onnx` | Mask decoder (~16 MB) |

Source: [Heliosoph/sam-onnx](https://huggingface.co/Heliosoph/sam-onnx) (Apache-2.0)

Config: `backend/models/sam_config.json`

## Workspace

Detection → **SAM refine (Auto + mask)**

## API

`POST /detect` with `method=sam_v1`

`GET /detect/capabilities` → `sam_onnx_available: true` when both ONNX files exist.

Debug fields: `base_method`, `refine_backend`, `mobile_sam_onnx`, `refined_count`.

## Verify

```powershell
.\.venv\Scripts\python -c "from geomora_detect.sam_onnx import mobile_sam_available; print(mobile_sam_available())"
.\.venv\Scripts\python -m pytest ..\tests\backend\test_sam_onnx.py -q
.\.venv\Scripts\python scripts\validate_yolo_facade.py
```

## Architecture

```text
Base detect (auto)
    ↓
Encode image once (MobileSAM encoder)
    ↓
Per box: box prompt → decoder → mask → tight bbox
    ↓
Fallback: GrabCut / threshold if ONNX missing or score low
```
