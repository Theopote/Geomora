# Geomora Acceptance Checklist (Stage A)

Use this checklist after installing `dist/geomora.rbz` and starting `backend/start_server.bat`.

**Real building photos:** see **`docs/REAL_PHOTO_ACCEPTANCE.md`** (SketchUp checklist + CLI batch metrics).

## Prerequisites

- [ ] Python backend responds at `http://127.0.0.1:8765/health`
- [ ] SketchUp extension **Geomora** enabled (v0.19.0+)
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
| 3.1 | Detect Elements (after rectify) | Form populated; method shows `yolo_v1`, `facade_row_v1`, or `contour_v1` |
| 3.2 | Auto-estimate wall size | Checkbox on; wall length/height update after Detect |
| 3.3 | Load Video → pick frame | Frame loads as primary image; Rectify works |
| 3.2 | Overlay view | Click box selects window; Delete removes it |
| 3.3 | Draw window | Drag creates new window box on rectified image |
| 3.4 | Resize / move | Corner handles resize; drag moves box |
| 3.5 | >8 windows | Generate blocked with review message |
| 3.6 | **Export YOLO Labels** (after rectify + overlay boxes) | Writes `{dataset}/{split}/images/*.jpg` + matching `labels/*.txt` |

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

## Phase 7+ — Exterior details

| # | Step | Expected |
|---|---|---|
| 7.5 | Enable Balcony → Generate | `Geomora_Balconies` tag; slab at first window sill |
| 7.6 | Enable Parapet + Cornice → Generate | `Geomora_Parapets` / `Geomora_Cornices` tags |
| 7.7 | Element tree | Shows balcony, parapet, cornice when enabled |

## Phase 8 — Geometry Doctor

| # | Step | Expected |
|---|---|---|
| 8.1 | Generate model → **Repair Geometry** | Status lists repairs or “no changes needed” |
| 8.2 | Inspector toggles (tiny edges, coplanar, normals) | Repair respects enabled options |
| 8.3 | Extensions → Geomora → Repair Geometry | Same repair on active model; one undo step |
| 8.4 | Ctrl+Z after repair | Repair changes revert |

## Phase 9 — Multi-storey + wall joins

| # | Step | Expected |
|---|---|---|
| 9.1 | Storey count = 2 → Generate | Two storey groups; elevations 0 and storey height |
| 9.2 | Repeat openings on | Windows on both floors; door only on ground |
| 9.3 | Perimeter walls on | Four walls per storey; corners intersect |
| 9.4 | Roof / parapet | Only on top storey |
| 9.5 | Validate | Passes with cumulative storey elevations |

## Phase 10 — LOD + structural grid

| # | Step | Expected |
|---|---|---|
| 10.1 | LOD 100 → Generate | Walls + slabs only; no window cuts |
| 10.2 | LOD 300 + balcony → Generate | Trim, railing, eaves tags present |
| 10.3 | Structural grid + columns → Generate | Multiple `grid_col_*` columns |
| 10.4 | Element tree | Shows selected LOD level |
| 10.5 | Storey count 2, repeat off | Per-floor tabs; different window counts per floor |

## Phase 11 — Interior layout + LOD visibility

| # | Step | Expected |
|---|---|---|
| 11.1 | Interior partitions on, count = 1 → Generate | One centre partition wall per storey; `Geomora_InteriorWalls` tag |
| 11.2 | LOD 300 + windows → Generate | Four trim pieces per window (lintel, sill, 2 jambs) |
| 11.3 | LOD 100 → Generate | `Geomora_Windows` / `Geomora_Trim` tags hidden in model |
| 11.4 | LOD 200 → Generate | Openings visible; trim / eaves tags hidden |
| 11.5 | Perimeter + partitions | Partitions span interior Y range inside footprint |

## Phase 12 — Rooms + constraint solver

| # | Step | Expected |
|---|---|---|
| 12.1 | Partitions + partition doors → Generate | Door cut on each partition; `partition_door_*` in IR |
| 12.2 | Room zones on → Generate | `rooms[]` in IR; `Geomora_Rooms` tag in model |
| 12.3 | Menu LOD 100 View | Windows/rooms/trim hidden |
| 12.4 | Solve Constraints after Rationalize | Window widths equalized per constraint graph |
| 12.5 | LOD 100 Generate | No partition doors in openings |

## Phase 13 — Room types + furniture + LOD scenes

| # | Step | Expected |
|---|---|---|
| 13.1 | Room zones + auto types → Generate | `rooms[].semantic.room_type` set (living, bedroom, etc.) |
| 13.2 | Furniture on, LOD 300 → Generate | `furniture[]` in IR; `Geomora_Furniture` tag |
| 13.3 | Partition door offsets `1200,1800` | Each partition door at specified offset |
| 13.4 | Create LOD Scene Pages (menu) | Three scenes: Geomora LOD 100/200/300 |
| 13.5 | Constraint parallel in graph | Acknowledged in `constraint_solution` |

## Phase 14 — Fixtures + overrides

| # | Step | Expected |
|---|---|---|
| 14.1 | Room override `2:kitchen` → Generate | Room 2 type = kitchen; name updated |
| 14.2 | Fixture sets on, LOD 300 | Multiple items per room; sink/toilet tags |
| 14.3 | Structural grid snap on | Partition X snapped to grid spacing |
| 14.4 | Next LOD Scene (menu) | Cycles Geomora LOD scenes |
| 14.5 | Export LOD Tour Manifest | JSON with scene order + LOD level |

## Phase 15 — Catalog + custom layouts

| # | Step | Expected |
|---|---|---|
| 15.1 | Fixture catalog on → kitchen | Extra catalog items (e.g. island) in IR |
| 15.2 | Room layout `1:sofa@600,600` | Custom position in `furniture[]` |
| 15.3 | Override `s2:1:bedroom` | Floor 2 room 1 type = bedroom |
| 15.4 | Perpendicular constraints on | `semantic.perpendicular` on partitions |
| 15.5 | Save LOD Tour JSON | File written with 3 scenes |

## Phase 16 — Presentation + layout tools

| # | Step | Expected |
|---|---|---|
| 16.1 | Reload fixture catalog (menu or Workspace) | Cache cleared; updated JSON items appear on Generate |
| 16.2 | Furniture collision on, fixture sets, LOD 300 | Multiple items per room without identical positions |
| 16.3 | Suggest layout presets | `room_furniture_layouts` field populated |
| 16.4 | Perpendicular repair on, skewed partition | Baseline axis-aligned; `semantic.repaired` set |
| 16.5 | Export LOD Tour HTML | `.html` slideshow with auto-advance |

## Phase 17 — Visual layout + LOD capture

| # | Step | Expected |
|---|---|---|
| 17.1 | Open layout editor | Canvas shows rooms; furniture draggable |
| 17.2 | Apply editor to layouts field | `room_furniture_layouts` updated |
| 17.3 | Layout `sofa@600,600@90` | Rotated furniture in model |
| 17.4 | Preview catalog diff | Summary of added/changed sets |
| 17.5 | Export LOD Capture HTML | HTML with embedded viewport images |

## Phase 18 — GIF export + editor polish

| # | Step | Expected |
|---|---|---|
| 18.1 | Export LOD Tour GIF | `.gif` file with animated LOD frames |
| 18.2 | Catalog palette drag-drop | New item appears on plan canvas |
| 18.3 | storey_count = 2, layout editor | Storey selector with per-floor rooms |
| 18.4 | Rotate selected 90° | Item rotation updates in serialized layout |
| 18.5 | 3D preview canvas | Isometric boxes update while dragging |

## Phase 19 — Video export + live view

| # | Step | Expected |
|---|---|---|
| 19.1 | Export LOD Tour MP4 (ffmpeg installed) | `.mp4` file created |
| 19.2 | Export without ffmpeg | Frames + `encode_lod_tour.ps1` / `.sh` |
| 19.3 | Palette search | Chips filter by keyword |
| 19.4 | Apply custom W/D/H | Serialized layout includes dimensions |
| 19.5 | Snap + wall magnet on drag | Positions align to grid/walls |
| 19.6 | Refresh viewport | PNG preview in Sources panel |

## Phase 20 — Stream + native video + layout report

| # | Step | Expected |
|---|---|---|
| 20.1 | Live stream (1s) | Viewport updates via Ruby timer |
| 20.2 | Export LOD Tour AVI (native) | `.avi` without ffmpeg |
| 20.3 | Export MP4 without ffmpeg | Falls back to `.avi` |
| 20.4 | Layout Undo / Redo | Prior positions restored |
| 20.5 | Export layout report | HTML with SVG per room |

## Phase 21 — Native MP4 + PDF + shortcuts

| # | Step | Expected |
|---|---|---|
| 21.1 | Export LOD Tour MP4 (native) | `.mp4` without ffmpeg |
| 21.2 | Export layout PDF | Valid `%PDF-1.4` file |
| 21.3 | Ctrl+Z / Ctrl+Y in editor | Undo / redo positions |
| 21.4 | Del with item selected | Item removed |
| 21.5 | Live stream + blur window | Stream pauses |

## Phase 22 — H.264 + booklet + copy/paste

| # | Step | Expected |
|---|---|---|
| 22.1 | Export LOD Tour MP4 (H.264) | Valid `.mp4` with `avc1` or ffmpeg libx264 |
| 22.2 | Export layout booklet PDF | Cover + TOC + room spreads |
| 22.3 | Ctrl+C / Ctrl+V in editor | Copy and paste furniture item |
| 22.4 | Live stream blur then focus | Stream resumes automatically |

## Phase 23 — Compact H.264 + booklet HTML + multi-select

| # | Step | Expected |
|---|---|---|
| 23.1 | Export LOD Tour MP4 (H.264) without ffmpeg | Smaller file than Phase 22 I_PCM |
| 23.2 | Export layout booklet HTML | Cover + TOC + two-room spreads |
| 23.3 | Ctrl+click + Ctrl+C/V | Multi-item copy/paste |
| 23.4 | Ctrl+A in editor | All items selected |

## Real photos (Stage A)

Full workflow: **`docs/REAL_PHOTO_ACCEPTANCE.md`**

| # | Step | Expected |
|---|---|---|
| RP.1 | ≥5 real photos: Rectify → Detect → Overlay fix → Generate | ≥4/5 succeed after light overlay edits |
| RP.2 | Export YOLO Labels from corrected overlays | Files under `data/facade_yolo_custom/train` |
| RP.3 | `accept_real_photos.py --dataset data/facade_yolo_custom --split val` | Exit 0; window recall ≥ 0.70 on val |

## Known limitations (acceptable for Stage A)

- `contour_v1` detection is heuristic — expect false positives on real photos
- Manual overlay editing is the primary correction path before Generate
- HtmlDialog may not expose browser DevTools in SketchUp

## CLI sanity (optional)

```powershell
cd backend
python run_rectify.py ..\examples\facade_perspective_synthetic.jpg --corners "[[80,60],[580,40],[600,430],[50,450]]"
python ..\examples\generate_rectified_fixture.py
.\.venv\Scripts\python scripts\validate_yolo_facade.py
.\.venv\Scripts\python scripts\accept_real_photos.py --images ..\examples\real_photos\rectified --method auto
```

Real-photo checklist: **`docs/REAL_PHOTO_ACCEPTANCE.md`**
