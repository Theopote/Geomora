# Geomora Phase 4 — Geometry Rationalization

**Status:** Core bootstrap **COMPLETE** (v0.7.0)

| Step | Status |
|---|---|
| 4.1 Planning + constraint contract | ✅ |
| 4.2 `Rationalizer` (snap, equal size/spacing, symmetry) | ✅ |
| 4.3 Workspace **Rationalize** button | ✅ |
| 4.4 IR `constraints[]` from rationalization metadata | ✅ |
| 4.5 Constraint solver (full graph) | ⏳ deferred |

---

## 1. Goal

Turn noisy opening dimensions (from detection or manual edit) into **architecturally regular** facade geometry before Generate.

```text
Inspector openings (mm)
      ↓
Rationalizer (facade_row_v1)
      ↓
Snapped + aligned windows/door
      ↓
IR with constraint graph metadata
      ↓
Validate → Generate
```

Phase 4 operates on **mm opening parameters**, not pixels.

---

## 2. Rationalization Rules (`facade_row_v1`)

| Rule | Behaviour |
|---|---|
| **snap_grid** | Round all dimensions to 50 mm grid (default) |
| **equal_width** | All windows share median width (snapped) |
| **equal_height** | All windows share median height (snapped) |
| **align** | All windows share median sill height (snapped) |
| **equal_spacing** | Redistribute window offsets with equal gaps in available zone |
| **symmetry** | Window row centered in zone (left/right margins equal) |
| **fixed_dimension** | Door width/height snapped; offset clamped to wall |

### Door zone heuristic

- Door center on left half of wall → windows laid out to the **right** of door
- Door center on right half → windows laid out to the **left** of door

---

## 3. API

### Ruby

```ruby
Core::Rationalizer.rationalize(params, grid_mm: 50)
# => { 'windows' => [...], 'door' => {...}, 'rationalization' => {...} }
```

### Workspace

Footer button **Rationalize** → updates Inspector + overlay bboxes → stores `rationalization` in params for Validate/Generate.

---

## 4. IR Constraints

After rationalization, `IRBuilder` emits constraint entries matching applied rules:

```json
{
  "id": "constraint_equal_width",
  "type": "equal_width",
  "targets": ["window_001", "window_002", "..."],
  "priority": "hard"
}
```

Supported types (validated, not solved in generator): `equal_width`, `equal_height`, `equal_spacing`, `align`, `symmetry`.

---

## 5. Workflow

```text
Load Image → Rectify → Detect → Overlay review (delete/draw)
      ↓
Rationalize  ← NEW
      ↓
Validate → Generate
```

---

## 6. Files

```text
plugin/geomora/core/rationalizer.rb
plugin/geomora/core/ir_builder.rb      — constraints from rationalization
plugin/geomora/ui/workspace/app.js     — applyRationalization
plugin/geomora/ui/workspace_dialog.rb  — rationalize callback
tests/ir/rationalizer_test.rb
```

---

## 7. Gate to Phase 5

Phase 4 produces **regularized single-facade openings**. See [PHASE_5.md](PHASE_5.md) for pattern intelligence (bay detection, shared components).
