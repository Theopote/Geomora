# Geomora Phase 11 — Interior Layout + LOD Visibility

**Status:** Phase 11 **COMPLETE** (v0.20.0)

| Step | Status |
|---|---|
| 11.1 Interior partition walls | ✅ |
| 11.2 Full window trim set (lintel / sill / jambs) | ✅ |
| 11.3 LOD-driven tag visibility in SketchUp | ✅ |
| 11.4 `Geomora_InteriorWalls` tag | ✅ |
| 11.5 Workspace UI (partitions + full trim) | ✅ |

---

## 1. Interior partition walls

When **Interior partition walls** is enabled:

- One or more walls divide the floor plate along the X axis (perpendicular to the facade)
- Count controlled by **Partition count** (default 1 = centre line)
- Walls use semantic `{ interior: true, partition: true }`
- Generated on every storey
- Works with or without perimeter walls (Y range adapts to footprint)

IR element id: `partition_{storey}_{index}`

---

## 2. Full window trim set

At **LOD 300** (or when **Full window trim** is checked):

| Detail | Tag | Position |
|---|---|---|
| `lintel` | `Geomora_Trim` | Above window head |
| `sill` | `Geomora_Trim` | Below window sill |
| `jamb_left` | `Geomora_Trim` | Left side of opening |
| `jamb_right` | `Geomora_Trim` | Right side of opening |

LOD 200 with full-trim unchecked → lintel band only (Phase 10 behaviour).

Params: `trim_projection`, `trim_height`, `trim_jamb_width` (defaults in `BuildingComposer`).

---

## 3. LOD tag visibility

After Generate, `LodVisibility.apply` sets SketchUp tag visibility:

| LOD | Visible tags |
|---|---|
| **100** | Walls, floors, roofs, reference |
| **200** | + windows, doors, columns, beams, stairs, balconies, parapets, interior walls |
| **300** | + cornices, trim, railings, eaves |

Hidden tags remain in the model but are not drawn — useful for LOD switching without re-generating.

---

## 4. Workflow

```text
… → Validate → Generate
      ↓
LOD visibility applied to Geomora_* tags
```

Enable partitions and LOD 300 trim from the **Interior Layout (Phase 11)** section in Workspace.

---

## 5. Files

```text
plugin/geomora/core/interior_layout.rb
plugin/geomora/core/lod_visibility.rb
plugin/geomora/core/building_composer.rb   — full trim set
plugin/geomora/core/ir_builder.rb          — partition walls in IR
plugin/geomora/generators/wall_generator.rb — interior wall tag
plugin/geomora/generators/trim_generator.rb — jamb / sill geometry
plugin/geomora/generators/project_generator.rb — LOD visibility hook
plugin/geomora/tags/manager.rb
tests/core/interior_layout_test.rb
tests/core/lod_visibility_test.rb
```

---

## 6. Deferred (Phase 12+)

- ~~Partition walls with openings (doors between rooms)~~ → Phase 12 ✅
- ~~LOD scene presets / animation~~ → Phase 12 presets ✅ (animation deferred)
- ~~Interior furniture / room semantics~~ → Phase 12 room zones ✅ (furniture deferred)
- ~~Constraint solver (Phase 4.5)~~ → Phase 12 basic solver ✅

---

## 7. Gate to Phase 12

Interior shells + LOD visibility enable room-level layout and semantic refinement on stacked buildings. See [PHASE_12.md](PHASE_12.md).
