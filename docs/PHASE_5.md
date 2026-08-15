# Geomora Phase 5 — Pattern Intelligence

**Status:** Core bootstrap **COMPLETE** (v0.8.0)

| Step | Status |
|---|---|
| 5.1 Planning + pattern contract | ✅ |
| 5.2 `PatternAnalyzer` (translation / grid / mirror) | ✅ |
| 5.3 Shared `ComponentDefinition` id (`window_bay_WxH`) | ✅ |
| 5.4 Workspace **Apply Pattern** button | ✅ |
| 5.5 Storey repetition / column grid | ⏳ deferred |

---

## 1. Goal

Detect **repeating facade patterns** after rationalization and assign a **single shared component** for all identical window bays.

```text
Rationalized openings
      ↓
PatternAnalyzer (facade_bay_v1)
      ↓
Pattern metadata + shared component_id
      ↓
IR constraints (grid / symmetry)
      ↓
Generate → one ComponentDefinition, many instances
```

---

## 2. Detected Patterns (`facade_bay_v1`)

| Pattern | Detection rule |
|---|---|
| **translation** | All windows share width, height, sill (±5 mm) |
| **grid** | Equal pitch between adjacent window offsets (±25 mm) |
| **window_bay** | Translation + grid → repeating bay module |
| **mirror** | Window centers symmetric about wall midline (no door) |

### Output metadata

```json
{
  "method": "facade_bay_v1",
  "type": "translation_grid",
  "patterns_detected": ["translation", "grid", "window_bay"],
  "bay_count": 4,
  "bay_pitch": 1980,
  "component_id": "window_bay_1500x1500",
  "shared_component": true
}
```

---

## 3. Component reuse

All windows in a detected bay row receive:

```text
component_id = window_bay_{width}x{height}
```

`IRBuilder` maps this to a single entry in `components[]`. SketchUp `ComponentManager` creates one `ComponentDefinition` reused for every instance.

---

## 4. Workflow

```text
Detect → Overlay review → Rationalize → Apply Pattern → Validate → Generate
```

**Apply Pattern** requires ≥2 windows. Best results after **Rationalize**.

---

## 5. Files

```text
plugin/geomora/core/pattern_analyzer.rb
plugin/geomora/core/ir_builder.rb
plugin/geomora/ui/workspace/app.js
tests/ir/pattern_analyzer_test.rb
```

---

## 6. Gate to Phase 6

Phase 5 covers **single-storey facade bay patterns**. Phase 6 adds multi-view depth / camera fusion for full building reconstruction.
