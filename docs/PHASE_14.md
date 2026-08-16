# Geomora Phase 14 — Fixture Libraries + Room Overrides

**Status:** Phase 14 **COMPLETE** (v0.23.0)

| Step | Status |
|---|---|
| 14.1 Custom room-type overrides | ✅ |
| 14.2 Multi-piece furniture sets | ✅ |
| 14.3 Kitchen / bathroom fixture library | ✅ |
| 14.4 LOD scene tour (next scene + manifest) | ✅ |
| 14.5 Structural partition grid constraints | ✅ |
| 14.6 Workspace Phase 14 UI | ✅ |

---

## 1. Room type overrides

**Room type overrides** field accepts comma-separated index mappings:

```text
1:kitchen,2:bathroom
```

- Applied after auto classification
- Sets `semantic.override = true`
- Updates room name to match type

---

## 2. Fixture sets (multi-piece)

When **Kitchen / bath fixture sets** is enabled (default with furniture):

| Room | Items |
|---|---|
| `kitchen` | counter, sink, stove, fridge |
| `bathroom` | vanity, toilet, shower |
| `living` | sofa, coffee table |
| `bedroom` | bed, wardrobe |
| `study` | desk, bookshelf |

Fixtures use tag `Geomora_Fixtures`; furniture uses `Geomora_Furniture`.

---

## 3. LOD scene tour

Menu: **Extensions → Geomora → LOD View**

| Action | Description |
|---|---|
| **Next LOD Scene** | Cycle Geomora LOD 100 → 200 → 300 scenes |
| **Export LOD Tour Manifest** | JSON list of scene order and LOD levels |

Requires **Create LOD Scene Pages** first.

---

## 4. Structural partition constraints

When **Snap partitions to structural grid** is enabled:

- Partition walls snap X position to `partition_grid_spacing` (default 300 mm)
- Semantic: `{ parallel: true, grid_snapped: true }`
- Uses `grid_x_spacing` as fallback

---

## 5. Constraint graph note

Phase 13 `parallel` / `perpendicular` / `coplanar` facade constraints remain acknowledged-only.
Phase 14 adds **geometry-level** partition snapping via `StructuralConstraintSolver`.

---

## 6. Workflow

```text
Partitions + room zones + overrides (e.g. 2:kitchen)
→ fixture sets + furniture at LOD 300
→ (optional) structural grid snap
→ Generate
→ Create LOD Scene Pages → Next LOD Scene
```

---

## 7. Files

```text
plugin/geomora/core/fixture_library.rb
plugin/geomora/core/room_overrides.rb
plugin/geomora/core/lod_presentation.rb
plugin/geomora/core/structural_constraint_solver.rb
plugin/geomora/core/furniture_planner.rb
tests/core/room_overrides_test.rb
tests/core/fixture_library_test.rb
tests/core/structural_constraint_solver_test.rb
tests/core/lod_presentation_test.rb
```

---

## 8. Deferred (Phase 15+)

- Per-room custom furniture layouts
- Animated LOD presentation export (video/GIF)
- Fixture libraries from external JSON catalog
- Multi-storey room override maps
- Perpendicular wall constraint geometry solver

---

## 9. Gate to Phase 15

Fixture libraries + overrides enable catalog-driven interior furnishing and layout refinement.
