# Observation Layer (Design)

Geomora's core boundary remains:

```text
AI Perception  →  Architectural IR  →  SketchUp Generator
```

The generator must never know which detector produced a window. As perception grows (YOLO, SAM, depth, multi-view), we need an explicit intermediate layer so **observations** do not pollute **architectural facts**.

---

## Problem

Today these are mixed at the detection boundary:

| Signal | Nature |
|--------|--------|
| YOLO bbox | Observation |
| MobileSAM mask | Observation |
| Depth map | Observation |
| Scale hint | Observation |
| Multi-view correspondence | Observation |
| `Window` in IR | Architectural fact |

A bbox is not a window. It is evidence that a window *might* exist.

---

## Proposed stack

```text
Perception (models)
        ↓
Observation Graph          ← raw evidence, source-tagged, replaceable
        ↓
Architectural Understanding ← grouping, naming, storey/wall assignment
        ↓
Constraint Graph           ← equal width, sill height, spacing (solver)
        ↓
Architectural IR           ← validated facts for SketchUp
```

---

## Observation schema (draft)

```json
{
  "id": "obs_window_17",
  "type": "window_candidate",
  "source": "photo_03",
  "bbox_norm": [0.12, 0.20, 0.21, 0.48],
  "mask_rle": null,
  "confidence": 0.82,
  "evidence": {
    "detector": "yolo_facade_v1",
    "sam_refined": true,
    "depth_plane_id": null
  }
}
```

| Field | Rule |
|-------|------|
| `type` | `window_candidate`, `door_candidate`, `wall_plane`, `sill_line`, … |
| `source` | Photo ID or view ID — never a SketchUp entity |
| `bbox_norm` | 0–1 rectified image space |
| `evidence` | Provenance only; not exported to IR |

---

## Understanding → IR

Understanding consumes observations + constraints and emits IR entities:

```text
obs_window_17 + obs_window_18 + obs_window_19
  + pattern_evidence (equal spacing)
  + depth_evidence (coplanar)
        ↓
WindowBay_03  (architectural grouping)
        ↓
IR openings[] with rationalized mm dimensions
```

Replacing YOLO → GroundingDINO → future foundation model only changes the Observation Graph. IR schema stays stable.

---

## Implementation status

| Item | Status |
|------|--------|
| Design doc | ✅ This file |
| Observation Graph data structure | ✅ `geomora_reconstruct/observations/` v0.1 |
| YOLO / facade-row adapters + fusion | ✅ |
| Understanding layer | ☐ Detections still map directly to overlay elements in UI |
| Constraint Graph solver | ☐ P0 after Understanding v0.1 (see `ROADMAP.md` B0) |

Production update: `POST /reconstruct` now runs detection evidence through the
Observation Graph, Understanding, constraint safety checks, and IR export.
Workspace **Analyze building** uses this endpoint; the legacy detection callback
is retained for diagnostics and compatibility.

**Rule:** Observation Graph is now the required boundary for new perception work.
Legacy detection → overlay path remains via adapters until Understanding v0.1 lands.

---

## ADR

| ID | Decision |
|----|----------|
| ADR-011 | Observations are ephemeral evidence; IR holds architectural facts only |
| ADR-012 | Understanding layer may be rule-based first, ML later |
| ADR-013 | Constraint solver operates on Understanding output, not raw bboxes |
