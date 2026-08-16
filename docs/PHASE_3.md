# Geomora Phase 3 — Semantic Reconstruction

**Status:** Core bootstrap **COMPLETE** (v0.6.0) · Real-photo path **v0.33.0**

| Step | Status |
|---|---|
| 3.1 Planning + API contract | ✅ |
| 3.2 Classical CV detector (`contour_v1`) | ✅ |
| 3.3 Ruby DetectClient + DetectionMapper | ✅ |
| 3.4 Workspace UI (Detect + Overlay) | ✅ |
| 3.5 YOLO ONNX (`yolo_v1`) | ✅ bootstrap — train via `backend/scripts/train_yolo_facade.py` |
| 3.6 SAM refinement | ✅ v0.35.0 (`sam_v1` — GrabCut + threshold; see `docs/PHASE_3_6.md`) |
| 3.7 `facade_row_v1` row detector | ✅ v0.33.0 |
| 3.8 Auto wall scale from detection | ✅ v0.33.0 |

### Quick start

```powershell
# Terminal 1 — backend (rectify + detect on same port)
cd F:\development\Geomora\backend
.\start_server.bat

# Terminal 2 — rebuild plugin
cd F:\development\Geomora
.\build_rbz.ps1
```

Then in SketchUp: **Open Workspace → Load Image → adjust corners → Rectify → Detect Elements → review overlay → Generate**

---

## 1. Goal

Detect **Wall / Window / Door** regions on a **rectified facade image** and map them into **Architectural IR** opening geometry (mm), editable in the workspace before Generate.

```text
Rectified Facade Image
      ↓
Element Detection (contour_v1 → future YOLO/SAM)
      ↓
BBox → mm mapping (wall_length / wall_height scale)
      ↓
IR openings (offset, width, height, sill_height)
      ↓
SketchUp Generator (Phase 0)
```

Phase 3 does **not** rationalize or snap dimensions (Phase 4). It produces **candidate** geometry with confidence scores.

---

## 2. Product Position

```text
┌─────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Phase 2    │     │    Phase 3       │     │    Phase 4      │
│  Rectify    │ ──► │  Detect win/door │ ──► │  Rationalize    │
│  front view │     │  → IR openings   │     │  snap / align   │
└─────────────┘     └──────────────────┘     └─────────────────┘
```

**Input:** rectified image (preferred) or original photo  
**Output:** IR-compatible window/door params + detection metadata in `sources[]`

---

## 3. Scope

### In scope (v0.4.0 bootstrap)

| Item | Description |
|---|---|
| `POST /detect` | Local FastAPI endpoint on port 8765 |
| `contour_v1` | OpenCV contour heuristic on dark rectangular regions |
| Detection overlay | JPEG with labeled boxes returned to workspace |
| `DetectionMapper` | Normalized bbox → mm offset / width / height / sill |
| Workspace | **Detect Elements** button, **Overlay** view toggle |
| IR metadata | `detection_method`, `detection_confidence`, `detected_elements` in sources |

### Out of scope (later Phase 3.x)

| Item | Notes |
|---|---|
| SAM 2 / YOLO / GroundingDINO | Phase 3.5+ — optional ONNX models |
| Automatic wall_length from image | User still sets wall dimensions in Inspector |
| Multi-storey / multi-wall | Single facade wall per workspace session |
| Constraint solver | Phase 4 |
| Cloud inference | Never |

---

## 4. Architecture Decisions

### ADR-P3-001: Detection extends the same local Python service

Rectify and detect share `127.0.0.1:8765`. One `start_server.bat`, one health check.

### ADR-P3-002: Image-space bboxes, mm mapping in Ruby

Python returns **normalized** `[x_min, y_min, x_max, y_max]` (0–1, y-down). Ruby `DetectionMapper` converts using user-supplied `wall_length` and `wall_height`:

| IR field | Formula |
|---|---|
| `offset` | `x_min × wall_length` |
| `width` | `(x_max - x_min) × wall_length` |
| `height` | `(y_max - y_min) × wall_height` |
| `sill_height` | `(1 - y_max) × wall_height` |

### ADR-P3-003: Human-in-the-loop before Generate

Detection fills the Inspector form; user reviews and edits before Validate/Generate. No silent auto-generate.

### ADR-P3-004: Bootstrap with classical CV, upgrade path to ML

`contour_v1` is intentionally simple. Same API contract supports future `yolo_v1` / `sam_v1` methods without plugin changes.

---

## 5. API

### `POST /detect`

```http
POST /detect
Content-Type: multipart/form-data

image: <file>   # rectified facade recommended
method: auto | yolo_v1 | facade_row_v1 | contour_v1 | sam_v1   # optional, default auto
```

**Response:**

```json
{
  "method": "contour_v1",
  "confidence": 0.72,
  "image_width": 1200,
  "image_height": 800,
  "elements": [
    {
      "type": "window",
      "bbox_norm": [0.05, 0.25, 0.22, 0.55],
      "confidence": 0.78
    }
  ],
  "overlay_base64": "...",
  "debug": { "candidate_count": 12, "element_count": 5 }
}
```

---

## 6. File Layout

```text
backend/
├── geomora_rectify/     # Phase 2 — rectify pipeline + unified server
├── geomora_detect/      # Phase 3 — detection pipeline
│   ├── contour_detector.py
│   ├── models.py
│   └── pipeline.py
plugin/geomora/
├── perception/
│   ├── detect_client.rb
│   └── detection_result.rb
├── core/
│   └── detection_mapper.rb
└── ui/workspace/        # Detect button + Overlay view
tests/backend/
└── test_detect_pipeline.py
```

---

## 7. Implementation Steps

| Step | Task | Gate |
|---|---|---|
| **3.1** | PHASE_3.md + API contract | Doc review |
| **3.2** | `geomora_detect` + `/detect` | pytest synthetic facade |
| **3.3** | Ruby client + mapper | Unit smoke in SketchUp |
| **3.4** | Workspace UI | Detect → form populated |
| **3.5** | YOLO ONNX (`yolo_v1`) | Train script + pytest when model present |
| **3.6** | SAM refinement (`sam_v1`) | Mask → tighter bbox — ✅ v0.35.0 |

---

## 8. Definition of Done (v0.4.0 core)

- [x] `POST /detect` returns windows + door on synthetic rectified image
- [x] Workspace **Detect Elements** fills window/door fields
- [x] Overlay view shows labeled boxes
- [x] Detection metadata stored in IR `sources[]` on Generate
- [ ] User verification on real rectified photo
- [ ] `contour_v1` tuned or replaced for production photos

---

## 9. Gate to Phase 4

Phase 3 must produce **repeatable** opening candidates from rectified images before rationalization (snap, equal spacing, symmetry). Phase 4 operates on IR constraints, not raw pixels.

```text
Phase 3 (detection → IR openings)
      ↓
Phase 4 (constraint graph + rationalization)
```

---

## 10. Tech Stack

| Layer | Tool | Role |
|---|---|---|
| CV bootstrap | OpenCV | Contour / threshold detector |
| CV future | ONNX Runtime + YOLO | Faster real-photo detection |
| CV future | SAM 2 | Mask refinement |
| API | FastAPI | `/detect` on existing server |
| Plugin | Ruby Net::HTTP | Multipart upload |
| IR | v0.1 schema | `confidence` on openings |

**Explicitly excluded in v0.4.0:** PyTorch in production path, cloud APIs, direct SketchUp API in Python.
