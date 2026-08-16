# Geomora Phase 16 — Presentation + Layout Tools

**Status:** Phase 16 **COMPLETE** (v0.25.0)

| Step | Status |
|---|---|
| 16.1 Catalog hot-reload | ✅ |
| 16.2 Furniture collision avoidance | ✅ |
| 16.3 LOD tour HTML export | ✅ |
| 16.4 Room layout presets | ✅ |
| 16.5 Perpendicular partition repair | ✅ |
| 16.6 Workspace Phase 16 UI | ✅ |

---

## 1. Fixture catalog hot-reload

- `FixtureCatalog.clear_cache!` and `FixtureCatalog.reload!(params)` bypass the in-memory cache
- Menu: **Extensions → Geomora → LOD View → Reload Fixture Catalog**
- Workspace: **Reload fixture catalog** button (uses current catalog path from the form)

Edit `default_fixtures.json` or a custom catalog path, reload, then Generate — no SketchUp restart required.

---

## 2. Furniture collision avoidance

When **Furniture collision avoidance** is enabled (default on):

- Auto and custom layouts run through `FurnitureCollision.resolve`
- Overlapping AABBs are nudged in 200 mm steps inside room bounds
- Applies at LOD 300 when furniture placement is enabled

---

## 3. LOD tour HTML export

Menu: **Extensions → Geomora → LOD View → Export LOD Tour HTML...**

- Writes a self-contained HTML slideshow from existing Geomora LOD scene pages
- Auto-advances every 2 seconds (configurable in code)
- Useful as a lightweight presentation proxy until true video/GIF capture exists

---

## 4. Room layout presets

Workspace: **Suggest layout presets**

- Fills **Room furniture layouts** based on partition count and inferred room types
- Example output: `1:sofa@600,600|coffee_table@1200,600;2:bed@600,600|wardrobe@600,2200`
- Multi-storey prefixes (`s2:`) are added when `storey_count > 1`

---

## 5. Perpendicular partition repair

When **Repair perpendicular partitions** is enabled:

- Skewed partition baselines snap to the nearest axis aligned with the facade
- Sets `semantic.repaired` and updates `semantic.perpendicular`
- Works independently of validation-only mode

---

## 6. Workflow

```text
Suggest layout presets → review Room furniture layouts
Fixture catalog on → Reload after JSON edits
Furniture + collision on → LOD 300 → Generate
Perpendicular repair on → Validate → Generate
Create LOD Scene Pages → Export LOD Tour HTML
```

---

## 7. Files

```text
plugin/geomora/core/furniture_collision.rb
plugin/geomora/core/room_layout_presets.rb
plugin/geomora/core/fixture_catalog.rb          (cache + reload)
plugin/geomora/core/furniture_planner.rb        (collision integration)
plugin/geomora/core/perpendicular_constraint_solver.rb
plugin/geomora/core/lod_presentation.rb         (export_tour_html)
tests/core/furniture_collision_test.rb
tests/core/room_layout_presets_test.rb
```

---

## 8. Deferred (Phase 17 — delivered in v0.26.0)

See `docs/PHASE_17.md` for layout editor, rotation/wall align, catalog diff, and LOD capture export.

Remaining for Phase 18+:

- True GIF/video encoder from captured frames
- Full drag-and-drop catalog palette in editor

---

## 9. Gate to Phase 17

Presentation export and layout tooling enable client-facing walkthroughs and faster interior iteration loops.
