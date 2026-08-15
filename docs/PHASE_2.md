# Geomora Phase 2 — Perspective Rectification

**Status:** Planning complete · Implementation in progress (v0.3.0)

| Step | Status |
|---|---|
| 2.1–2.5 Backend pipeline + API | ✅ |
| 2.6–2.7 Ruby client + Workspace UI | ✅ |
| 2.8 Manual 4-corner UI | ⏳ |
| 2.9–2.11 Integration gate | ⏳ |

### Quick start

```powershell
# Terminal 1 — backend
cd F:\development\Geomora\backend
.\start_server.bat

# Terminal 2 — rebuild plugin
cd F:\development\Geomora
.\build_rbz.ps1
```

Then in SketchUp: **Open Workspace → Load Image → Rectify Facade → Original/Rectified toggle**

---

## 1. Goal

Transform a **perspective facade photograph** into a **rectified (fronto-parallel) facade image** suitable for manual measurement and future semantic detection.

```text
Perspective Photo
      ↓
Line Detection
      ↓
Vanishing Point Estimation
      ↓
Homography
      ↓
Rectified Facade Image
```

Phase 2 does **not** detect windows or walls automatically. It only corrects perspective.

---

## 2. Product Position in Pipeline

```text
┌─────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Phase 1    │     │    Phase 2       │     │    Phase 3      │
│  Workspace  │ ──► │  Rectification   │ ──► │  Semantic CV    │
│  + raw img  │     │  + rectified img │     │  wall/win/door  │
└─────────────┘     └──────────────────┘     └─────────────────┘
        │                     │                        │
        └─────────────────────┴────────────────────────┘
                              ▼
                    Architectural IR (v0.1+)
                              ▼
                    SketchUp Generator (Phase 0)
```

Phase 2 sits in **Layer 2 — Perception** (geometry-only, no semantics).

---

## 3. Scope

### In scope

| Item | Description |
|---|---|
| Line detection | Detect dominant horizontal / vertical facade lines |
| Vanishing points | Estimate VP from intersecting line families |
| Homography | Compute plane rectification transform |
| Rectified image output | Front-facing facade image in workspace viewer |
| Manual fallback | User-adjustable 4-corner facade region if auto fails |
| IR `sources` metadata | Store rectification matrix, VP, original path |
| Workspace UI | Toggle: Original / Rectified view |
| Minimal Python service | OpenCV-based rectification (local only) |

### Out of scope

| Item | Phase |
|---|---|
| SAM / YOLO / semantic segmentation | Phase 3 |
| Window/door auto-detection | Phase 3 |
| Depth estimation | Phase 3+ |
| Constraint solver / rationalization | Phase 4 |
| Cloud API / LLM | Never in Phase 2 |
| Multi-view / COLMAP | Phase 6 |
| Automatic IR generation from image | Phase 3+ |

---

## 4. Architecture Decision

### ADR-P2-001: Rectification runs outside SketchUp

**Decision:** Perspective rectification executes in a **local Python process**, not in Ruby or HtmlDialog JavaScript.

**Rationale:**

- OpenCV + NumPy are the right tools for line detection and homography
- Keeps SketchUp plugin thin (ADR-010)
- Matches handbook §6.3 Backend responsibilities
- HtmlDialog JS lacks robust CV libraries

**Interface:**

```text
SketchUp Plugin (Ruby)
    │  HTTP localhost (or stdin/stdout JSON)
    ▼
geomora-rectify (Python)
    │  OpenCV
    ▼
{ rectified_image_path, homography, vanishing_points, confidence }
```

### ADR-P2-002: Rectification result is not IR geometry

Rectified image and homography are stored in `sources[]` metadata. They do **not** directly become wall/window dimensions. Phase 1 manual definition (or Phase 3 detection) still produces IR elements.

### ADR-P2-003: Manhattan World assumption

Phase 2 assumes a **Manhattan facade**: dominant horizontal and vertical line families converging to two vanishing points on the horizon. Non-orthogonal architecture may need manual 4-point correction.

---

## 5. Proposed Repository Structure

```text
geomora/
├── plugin/geomora/          # existing — add rectification client
│   ├── perception/
│   │   ├── rectify_client.rb    # HTTP/JSON client to Python service
│   │   └── rectification_result.rb
│   └── ui/
│       └── workspace/           # add Rectified tab + corner editor
│
├── backend/                 # NEW — Phase 2 minimal service
│   ├── geomora_rectify/
│   │   ├── __init__.py
│   │   ├── server.py            # FastAPI or stdlib HTTP
│   │   ├── line_detection.py
│   │   ├── vanishing_point.py
│   │   ├── homography.py
│   │   └── pipeline.py
│   ├── requirements.txt         # opencv-python-headless, numpy, fastapi, uvicorn
│   └── README.md
│
├── examples/
│   └── facade_perspective.jpg   # test photo (user-provided or sample)
│
├── tests/
│   ├── backend/                   # pytest for Python pipeline
│   └── integration/               # rectify smoke test
│
└── docs/
    └── PHASE_2.md               # this file
```

---

## 6. IR Schema Extension (v0.1 compatible)

No breaking change to `schema_version`. Extend `sources` metadata:

```json
{
  "id": "photo_001",
  "type": "image",
  "metadata": {
    "original_path": "C:/photos/facade.jpg",
    "rectified_path": "C:/Geomora/cache/facade_rectified.jpg",
    "homography": [[1,0,0],[0,1,0],[0,0,1]],
    "vanishing_points": [[1200, 540], [80, 520]],
    "rectification_confidence": 0.87,
    "method": "auto_vanishing_point"
  }
}
```

Parser: preserve unknown metadata fields (already does). Validator: optional warnings if confidence < threshold (no hard fail in Phase 2).

---

## 7. Workspace UI Changes

### New panels / controls

| Control | Action |
|---|---|
| **Rectify** button | Send image to Python service |
| View toggle | `Original` \| `Rectified` |
| Overlay | Show detected lines + vanishing points (debug) |
| Manual mode | Drag 4 corners on image → homography from quad |
| Status | `Rectification confidence: 0.87` |

### Updated flow

```text
1. Load Reference Image
2. [Rectify]  ← NEW
3. Switch to Rectified view
4. Manually define dimensions (Phase 1, unchanged)
5. Validate → Generate
```

---

## 8. Python Pipeline (minimal)

### Step 2.1 — Line detection

```python
# LSD or HoughLinesP
lines = detect_lines(image)
horizontal, vertical = classify_line_families(lines)
```

### Step 2.2 — Vanishing points

```python
vp_left, vp_right = estimate_vanishing_points(horizontal)
```

### Step 2.3 — Facade plane + homography

```python
# Infer facade quadrilateral from VPs + image bounds
# Or use user-provided 4 corners
H = compute_rectifying_homography(corners_src, rect_dst)
rectified = cv2.warpPerspective(image, H, (width, height))
```

### Step 2.4 — API endpoint

```text
POST /rectify
Content-Type: multipart/form-data
  image: <file>
  corners: optional JSON [[x,y],...]

Response:
{
  "rectified_image_base64": "...",
  "homography": [[...]],
  "vanishing_points": [[x,y],[x,y]],
  "confidence": 0.87
}
```

### Step 2.5 — Ruby client

```ruby
Geomora::Perception::RectifyClient.rectify(image_path, corners: nil)
# → RectificationResult
```

---

## 9. Development Sequence

Execute in order. Do not skip ahead to Phase 3.

| Step | Task | Deliverable |
|---|---|---|
| **2.0** | Planning sign-off | This document |
| **2.1** | Python project skeleton | `backend/` + `requirements.txt` |
| **2.2** | Line detection module | Unit test with sample image |
| **2.3** | Vanishing point estimation | Unit test |
| **2.4** | Homography + warp | Rectified output file |
| **2.5** | FastAPI `/rectify` endpoint | curl smoke test |
| **2.6** | Ruby `RectifyClient` | Call from Ruby Console |
| **2.7** | Workspace UI: Rectify button + view toggle | Manual test in SketchUp |
| **2.8** | Manual 4-corner fallback | UI + pipeline |
| **2.9** | IR `sources` metadata write | Stored on rectify |
| **2.10** | Integration test | perspective photo → rectified view |
| **2.11** | Documentation + RBZ/backend README | Phase 2 gate |

---

## 10. Definition of Done

Phase 2 is complete when:

### Backend

- [ ] `backend/` starts locally (`uvicorn` or equivalent)
- [ ] `/rectify` accepts image, returns rectified result
- [ ] Line detection runs on sample facade photo
- [ ] Homography produces visibly fronto-parallel output
- [ ] Manual 4-corner input works as fallback
- [ ] No cloud / no AI models

### Plugin

- [ ] Workspace **Rectify** button calls Python service
- [ ] Rectified image displays in Image Viewer
- [ ] Original / Rectified toggle works
- [ ] Rectification metadata stored in session / IR sources
- [ ] Service offline → clear error message (no crash)
- [ ] Phase 0 + Phase 1 features still work

### Quality

- [ ] Python unit tests for line VP homography modules
- [ ] At least 2 test images (good perspective + failure case)
- [ ] `docs/PHASE_2.md` updated with results
- [ ] README documents how to start backend

---

## 11. Technology Stack

| Layer | Choice | Notes |
|---|---|---|
| CV | OpenCV (`opencv-python-headless`) | Line detect, warpPerspective |
| Math | NumPy | VP intersection, homography |
| API | FastAPI + uvicorn | Minimal local HTTP |
| Plugin bridge | Ruby `Net::HTTP` or `Sketchup::Http` | Localhost only |
| UI | Existing HtmlDialog workspace | Add rectify controls |

**Explicitly excluded:** PyTorch, SAM, YOLO, COLMAP, NeRF.

---

## 12. Risks and Mitigations

| Risk | Mitigation |
|---|---|
| User doesn't have Python installed | Document setup; optional bundled Python later |
| Auto VP fails on cluttered photos | Manual 4-corner mode (required) |
| Firewall blocks localhost | Use 127.0.0.1:8765, document port |
| Large images slow | Resize to max 2048px before processing |
| SketchUp blocks HTTP | Test `Net::HTTP` early in Step 2.6 |

---

## 13. Test Fixtures

| Fixture | Purpose |
|---|---|
| `examples/facade_perspective.jpg` | Typical 2-VP building facade |
| `examples/facade_oblique.jpg` | Strong perspective, known good rectify |
| `examples/facade_cluttered.jpg` | Trees/occlusion — expect manual fallback |

(User to provide real photos; add synthetic samples if needed.)

---

## 14. Effort Estimate

| Component | Estimate |
|---|---|
| Python pipeline | 3–5 days |
| FastAPI service | 1 day |
| Ruby client + workspace UI | 2–3 days |
| Tests + docs | 1–2 days |
| **Total** | **~1–2 weeks** |

---

## 15. Recommendation

### START WITH Step 2.1 — Backend Skeleton

Before touching SketchUp UI:

1. Create `backend/` with OpenCV line detection on a static image
2. Prove homography output visually (save `rectified.jpg` to disk)
3. Then wire Ruby client and workspace button

This de-risks the hardest part (CV quality) before UI integration.

---

## 16. Gate to Phase 3

Phase 2 must pass before semantic detection (SAM/YOLO). Phase 3 will use the **rectified image** as its input, not the raw perspective photo.

```text
Phase 2 output (rectified image)
        ↓
Phase 3 (segmentation / detection)
        ↓
IR elements (walls, windows, doors)
```

---

**Geomora Phase 2 Principle**

> Correct the camera before interpreting the architecture.
