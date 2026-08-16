# Geomora Phase 6 — Multi-view Reconstruction

**Status:** Phase 6 **COMPLETE** (v0.9.0) · 6.5 **COMPLETE** (v0.10.0) · 6.5+ **COMPLETE** (v0.11.0) · 6.5++ **COMPLETE** (v0.12.0) · 6.5+++ **COMPLETE** (v0.13.0)

| Step | Status |
|---|---|
| 6.1 Planning + API contract | ✅ |
| 6.2 Feature matching + planar homography (`feature_homography_v1`) | ✅ |
| 6.3 `POST /multiview/register` + Ruby client | ✅ |
| 6.4 Workspace secondary image + Register Views | ✅ |
| 6.5 Depth proxy + opening fusion (`multiview_fusion_v1`) | ✅ |

---

## 1. Goal

Register **two facade photographs** of the same building plane and store camera-relative alignment metadata in IR `sources[]`.

```text
Primary image + Secondary image
      ↓
ORB feature match + RANSAC homography
      ↓
Multiview metadata (transform view_002 → view_001)
      ↓
IR sources[] (primary + secondary)
      ↓
Continue single-facade pipeline (Rectify → Detect → Rationalize → Generate)
```

Phase 6 bootstrap aligns views in **image space**. Depth estimation and full 3D fusion are deferred.

---

## 2. Backend (`feature_homography_v1`)

| Step | Tool |
|---|---|
| Feature detection | OpenCV ORB (5000 keypoints) |
| Matching | BFMatcher Hamming, cross-check |
| Pose / plane | `cv2.findHomography` (RANSAC, 5 px) |
| Output | 3×3 homography mapping secondary → primary pixels |

### `POST /multiview/register`

```http
POST /multiview/register
Content-Type: multipart/form-data

primary: <file>
secondary: <file>
```

**Response:**

```json
{
  "method": "feature_homography_v1",
  "confidence": 0.82,
  "match_count": 156,
  "inlier_count": 98,
  "homography": [[...], [...], [...]],
  "views": [
    { "id": "view_001", "role": "primary", "image_width": 800, "image_height": 600 },
    { "id": "view_002", "role": "secondary", "image_width": 800, "image_height": 600,
      "transform_to_primary": [[...]] }
  ]
}
```

---

## 3. Workspace workflow

1. **Load Primary Image** — main facade photo (existing flow)
2. **Load Secondary Image** — another angle of same facade
3. **Register Views** — calls `/multiview/register`, shows match/inlier counts
4. Continue: Rectify → Detect → Rationalize → Apply Pattern → Generate

Multi-view metadata is stored in IR `sources[]` on Generate.

---

## 4. Files

```text
backend/geomora_multiview/
├── feature_match.py
├── models.py
└── pipeline.py
plugin/geomora/perception/
├── multiview_client.rb
└── multiview_result.rb
tests/backend/
├── test_multiview_pipeline.py
└── test_multiview_endpoint.py
```

---

## 5. Future (Phase 7+)

- Cross-session multi-photo opening graph fusion
- COLMAP mesh export to SketchUp
- TensorRT / CoreML ONNX providers

---

## 6. Gate to Phase 7

Phase 6 links multiple **photos** to one facade session. See **Phase 6.5** below and [PHASE_6.md](PHASE_6.md) for fusion.

---

## Phase 6.5+ — Neural Depth + COLMAP (v0.11.0)

| Step | Status |
|---|---|
| 6.5.6 MiDaS ONNX depth (`midas_v21_v1`) with auto fallback | ✅ |
| 6.5.7 COLMAP sparse registration (`colmap_sparse_v1`) | ✅ |
| 6.5.8 `GET /multiview/capabilities` + Workspace method selectors | ✅ |
| 6.5.9 Depth Anything / Marigold upgrade | ✅ (see Phase 6.5++ below); COLMAP dense deferred |

### Depth methods (v0.11 baseline)

| Method | Description |
|---|---|
| `auto` | Best available neural model, else gradient (see 6.5++ for priority) |
| `gradient_laplacian_v1` | Fast Laplacian + radial proxy (default without model) |
| `midas_v21_v1` | MiDaS v2.1 small ONNX |

Download MiDaS:

```bat
cd backend
.venv\Scripts\python.exe scripts\download_depth_models.py --model midas
```

Or set `GEOMORA_MIDAS_MODEL` to a custom ONNX path.

### Registration methods

| Method | Description |
|---|---|
| `auto` | COLMAP if `colmap` is on PATH, else ORB homography |
| `feature_homography_v1` | ORB + RANSAC homography (Phase 6) |
| `colmap_sparse_v1` | COLMAP SIFT sparse reconstruction + shared 3D observations |

Install [COLMAP](https://colmap.github.io/) and ensure `colmap` is available in your shell PATH.

### API

```http
GET /multiview/capabilities

POST /multiview/register
method: auto | feature_homography_v1 | colmap_sparse_v1

POST /multiview/fuse
method: auto | yolo_v1 | contour_v1
depth_method: auto | depth_anything_v2_small_v1 | marigold_v1_1_v1 | midas_v21_v1 | gradient_laplacian_v1
register_method: auto | feature_homography_v1 | colmap_sparse_v1
homography: optional JSON 3x3 matrix
```

---

## Phase 6.5++ — Depth Model Upgrade (v0.12.0)

| Step | Status |
|---|---|
| 6.5.10 Depth Anything V2 Small ONNX (`depth_anything_v2_small_v1`) | ✅ |
| 6.5.11 Marigold v1-1 optional diffusers backend (`marigold_v1_1_v1`) | ✅ |
| 6.5.12 Depth model registry + DPT preprocessing | ✅ |
| 6.5.13 Unified downloader `download_depth_models.py` | ✅ |

### Auto depth priority

```text
auto → depth_anything_v2_small_v1 → marigold_v1_1_v1 → midas_v21_v1 → gradient_laplacian_v1
```

### Depth methods (v0.12.0)

| Method | Description |
|---|---|
| `auto` | Best available neural model, else gradient |
| `depth_anything_v2_small_v1` | Depth Anything V2 Small (ONNX, ~99 MB + weights) |
| `marigold_v1_1_v1` | Marigold v1-1 via diffusers (optional torch stack) |
| `midas_v21_v1` | MiDaS v2.1 small ONNX (legacy fallback) |
| `gradient_laplacian_v1` | Fast Laplacian + radial proxy |

Download ONNX models:

```bat
cd backend
.venv\Scripts\python.exe scripts\download_depth_models.py --model all
```

Marigold (optional, downloads weights on first use):

```bat
pip install -r requirements-depth.txt
```

`GET /multiview/capabilities` returns `depth_models`, `depth_auto`, and per-model availability flags.

---

## Phase 6.5+++ — COLMAP Dense + Quantized DA2 + GPU ONNX (v0.13.0)

| Step | Status |
|---|---|
| 6.5.14 COLMAP dense registration (`colmap_dense_v1`) | ✅ |
| 6.5.15 COLMAP dense depth map for fusion (`colmap_dense_v1`) | ✅ |
| 6.5.16 Depth Anything V2 Q4 ONNX (`depth_anything_v2_small_q4_v1`) | ✅ |
| 6.5.17 GPU ONNX Runtime providers (CUDA / DirectML) | ✅ |

### Registration

| Method | Description |
|---|---|
| `colmap_dense_v1` | Sparse COLMAP + undistort + patch-match stereo + fusion; falls back to sparse depth if dense fails |

### Depth

| Method | Description |
|---|---|
| `colmap_dense_v1` | Use COLMAP fused/sparse depth from dense registration workspace |
| `depth_anything_v2_small_q4_v1` | Quantized DA2 (~27 MB weights, faster on CPU) |

### Auto depth priority

```text
GPU:  DA2 full → DA2 Q4 → Marigold → MiDaS → gradient
CPU:  DA2 Q4 → DA2 full → Marigold → MiDaS → gradient
```

When `register_method=colmap_dense_v1`, fusion auto-prefers COLMAP dense depth if available.

### GPU ONNX

Set execution provider via environment variable:

```bat
set GEOMORA_ONNX_DEVICE=auto    :: CUDA → DirectML → CPU
set GEOMORA_ONNX_DEVICE=cuda    :: NVIDIA GPU (requires onnxruntime-gpu)
set GEOMORA_ONNX_DEVICE=dml     :: Windows DirectML
set GEOMORA_ONNX_DEVICE=cpu
```

Download quantized DA2:

```bat
.venv\Scripts\python.exe scripts\download_depth_models.py --model da2-q4
```

---

## Phase 6.5 — Opening Fusion + Depth (v0.10.0)

| Step | Status |
|---|---|
| 6.5.1 Gradient depth proxy (`gradient_laplacian_v1`) | ✅ |
| 6.5.2 Transform secondary detections via homography | ✅ |
| 6.5.3 IoU fusion + depth-weighted confidence | ✅ |
| 6.5.4 `POST /multiview/fuse` + Workspace **Fuse Openings** | ✅ |
| 6.5.5 MiDaS / COLMAP depth | ✅ (see Phase 6.5+ below) |

### Workflow

```text
Load Primary + Secondary → Register Views (optional)
      ↓
Rectify primary (recommended)
      ↓
Fuse Openings  ← detects both views, merges into primary frame
      ↓
Rationalize → Apply Pattern → Generate
```

### API

```http
POST /multiview/fuse
primary: <file>
secondary: <file>
homography: optional JSON 3x3 matrix
method: auto | yolo_v1 | contour_v1
```
