# Geomora Acceptance Checklist (Stage A)

Use this checklist after installing `dist/geomora.rbz` and starting `backend/start_server.bat`.

## Prerequisites

- [ ] Python backend responds at `http://127.0.0.1:8765/health`
- [ ] SketchUp extension **Geomora** enabled (v0.14.0+)
- [ ] Fixture available: `examples/facade_perspective_synthetic.jpg`

## Phase 2 — Rectification

| # | Step | Expected |
|---|---|---|
| 2.1 | Open Workspace | HtmlDialog loads without error |
| 2.2 | Load Reference Image | Original view shows photo; four corner handles visible |
| 2.3 | Drag corners | Quad outline follows handles; labels TL/TR/BR/BL |
| 2.4 | Reset Corners | Handles return to ~8% inset default |
| 2.5 | Rectify Facade | Status success; Rectified view shows fronto-parallel facade |
| 2.6 | Rectify meta | Method `manual_corners` when corners were sent |

## Phase 3 — Detection + overlay editing

| # | Step | Expected |
|---|---|---|
| 3.1 | Detect Elements (after rectify) | Form populated; method shows `yolo_v1` or `contour_v1` |
| 3.2 | Overlay view | Click box selects window; Delete removes it |
| 3.3 | Draw window | Drag creates new window box on rectified image |
| 3.4 | Resize / move | Corner handles resize; drag moves box |
| 3.5 | >8 windows | Generate blocked with review message |

## IR + Generate

| # | Step | Expected |
|---|---|---|
| 4.0 | **Rationalize** (≥1 window) | Equal widths/heights/sills; even spacing; overlay boxes update |
| 4.1 | **Apply Pattern** (≥2 windows, after Rationalize) | Element tree shows `translation_grid`; shared `window_bay_WxH` |
| 4.2 | Door width = 0 | No door in element tree / IR when no door on facade |
| 4.3 | Validate | Passes with consistent openings |
| 4.4 | Generate | SketchUp geometry created in one undo step |
| 4.5 | Generate (after Apply Pattern) | Single shared window ComponentDefinition in Components panel |
| 4.6 | Ctrl+Z | Entire generation reverts |

## Phase 6 — Multi-view

| # | Step | Expected |
|---|---|---|
| 6.1 | Load Primary + Secondary images | Both paths shown in Sources panel |
| 6.2 | Register Views | Match/inlier counts; confidence > 0.4 on similar facades |
| 6.3 | Generate (after registration) | IR `sources[]` contains primary + `view_002` with transform |
| 6.4 | **Fuse Openings** (after Rectify recommended) | Merged windows on overlay; fewer duplicates than single-view detect |
| 6.5 | Generate (after fusion) | IR `sources[]` includes `fusion` metadata with `fusion_method` |
| 6.6 | Registration = COLMAP (if installed) | Method `colmap_sparse_v1`; pose debug in multiview metadata |
| 6.7 | Depth = MiDaS (if model downloaded) | Fusion debug `depth_method: midas_v21_v1` |
| 6.8 | Depth = Depth Anything V2 (if downloaded) | Fusion debug `depth_method: depth_anything_v2_small_v1` |
| 6.9 | Depth = Marigold (if requirements-depth installed) | Fusion debug `depth_method: marigold_v1_1_v1` |
| 6.10 | Registration = COLMAP dense | Method `colmap_dense_v1`; `dense_vertices` in debug |
| 6.11 | Depth = DA2 Q4 (if downloaded) | Fusion debug `depth_method: depth_anything_v2_small_q4_v1` |
| 6.12 | GPU ONNX (`GEOMORA_ONNX_DEVICE=cuda`) | `/multiview/capabilities` shows non-CPU `active_provider` |

## Phase 7 — Full building elements

| # | Step | Expected |
|---|---|---|
| 7.1 | Enable Floor + Roof (default) → Generate | `Geomora_Floors` / `Geomora_Roofs` tags in model |
| 7.2 | Enable Columns + Beam + Stair → Generate | Tagged groups under storey |
| 7.3 | Element tree | Shows enabled building elements before Generate |
| 7.4 | Validate | Passes with floor/roof in IR |

## Known limitations (acceptable for Stage A)

- `contour_v1` detection is heuristic — expect false positives on real photos
- Manual overlay editing is the primary correction path before Generate
- HtmlDialog may not expose browser DevTools in SketchUp

## CLI sanity (optional)

```powershell
cd backend
python run_rectify.py ..\examples\facade_perspective_synthetic.jpg --corners "[[80,60],[580,40],[600,430],[50,450]]"
```
