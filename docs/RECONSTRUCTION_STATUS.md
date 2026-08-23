# Geomora Reconstruction Status (Master Doc Alignment)

**Updated:** 2026-08-24

**Subsystem maturity and gate progress:** `docs/ROADMAP.md` (canonical)

**Canonical references:** `docs/Geomora Phase 0 — Cursor Master Prompt v0.1.md`, `docs/Geomora 技术架构与开发手册 v0.1.md`

Geomora's core mission:

```text
Photo / Video → Perception → Understanding → Rationalization → IR → SketchUp
```

Presentation features (LOD tours, layout PDF, MP4 export) are **secondary** and frozen after v0.32.

---

## Core pipeline status

| Layer | Capability | Status |
|-------|------------|--------|
| Phase 0 | IR + SketchUp geometry kernel | ✅ Complete |
| Phase 1 | Workspace + manual facade | ✅ Complete |
| Phase 2 | Perspective rectification | ✅ Core complete |
| Phase 3 | Window/door detection → IR | ⚠️ **v0.33 improves; real-photo tuning ongoing** |
| Phase 4 | Geometry rationalization | ✅ Core complete |
| Phase 5 | Pattern / component reuse | ✅ Core complete |
| Phase 6 | Multi-view + fusion + depth | ✅ Core complete |
| Phase 7+ | Full building from params | ✅ Code complete (not vision-driven) |

---

### Phase 3.6 — SAM mask refinement

| Feature | Description |
|---------|-------------|
| `sam_v1` | Auto detect → MobileSAM ONNX (or GrabCut fallback) → tighter `bbox_norm` |
| MobileSAM ONNX | `scripts/download_mobile_sam_onnx.py` → encoder + decoder in `models/` |
| Workspace | Detection: **SAM refine (Auto + mask)** |
| Overlay | Green mask tint on refined regions |

---

## v0.34 reconstruction deliverables

### Phase 3 — YOLO training + real-photo acceptance

| Feature | Description |
|---------|-------------|
| YOLO training pipeline | `dataset_builder`, `train_yolo_facade.py`, exported `facade_yolo_v1.onnx` |
| Labeling guide | `docs/YOLO_LABELING.md` |
| Workspace **Export YOLO Labels** | Overlay boxes → `facade_yolo_custom/{train\|val}/` |
| Real-photo acceptance | `docs/REAL_PHOTO_ACCEPTANCE.md`, `scripts/accept_real_photos.py` |

---

## v0.33 reconstruction deliverables

### Phase 3 — real photo path

| Feature | Description |
|---------|-------------|
| `facade_row_v1` | Row-aware detector for **rectified** facades (between YOLO and contour in `auto`) |
| `scale_hint` | Backend estimates `wall_length` / `wall_height` from door or window sill |
| Auto-scale checkbox | Inspector **Auto-estimate wall size from detection** |
| Detection fallback | Ruby: auto → `facade_row_v1` → `contour_v1` when empty |

### Video input (minimal)

| Feature | Description |
|---------|-------------|
| `POST /video/extract_frames` | Extract up to 24 key frames from MP4/MOV/WebM |
| Workspace **Load Video** | Thumbnail grid → pick frame → same Rectify → Detect flow |
| IR | Frame loaded as primary `source_path` (video metadata deferred) |

---

## Recommended workflow (Stage A)

```text
1. backend/start_server.bat
2. Install dist/geomora.rbz (v0.34.0+)
3. Open Workspace
4. Load Primary Image OR Load Video → pick key frame
5. Drag corners → Rectify Facade
6. Detection: Auto (YOLO → facade_row_v1 → contour_v1)
7. Review Overlay — delete false boxes, draw missing windows
8. Rationalize → Apply Pattern → Validate → Generate
```

Synthetic acceptance assets:

- `examples/facade_perspective_synthetic.jpg` — rectification
- `examples/generate_rectified_fixture.py` → `facade_rectified_synthetic.jpg` — detection
- `examples/real_photos/` — local real building photos (see `docs/REAL_PHOTO_ACCEPTANCE.md`)

---

## Still open (next priorities)

See **`docs/ROADMAP.md`** for the canonical queue. Summary:

| Priority | Item |
|----------|------|
| **P0** | **RC-M** — finish minimal GT audit and record the objective baseline |
| **P0** | **RC-S** — validate Metric Anchor and multi-anchor scale mathematics |
| **P0** | **RC-C** — solver on/off ablation; fixed-dimension correctness before new types |
| **P0** | **RC-A/RC-U** — frozen CV-only vs VLM topology ablation |
| **P0 gate** | **RC-G0** — record Prototype Bootstrap without a product-readiness claim |
| **P0 gate** | **RC-G1** — Reconstruction Core v0.1 Validation Gate |
| P1 | RC-O/RC-S multi-view and depth validation on real photos |
| P2 | Richer architectural hypotheses and video provenance |

---

## Frozen (do not extend without user request)

Phase 16–23: LOD presentation export, layout booklet, native H.264, interior layout editor polish.
