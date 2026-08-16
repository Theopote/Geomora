# Geomora Phase 15 — Catalog + Custom Layouts

**Status:** Phase 15 **COMPLETE** (v0.24.0)

| Step | Status |
|---|---|
| 15.1 External JSON fixture catalog | ✅ |
| 15.2 Per-room custom furniture layouts | ✅ |
| 15.3 Multi-storey room override maps | ✅ |
| 15.4 Perpendicular wall constraint validation | ✅ |
| 15.5 LOD tour save + play | ✅ |
| 15.6 Workspace Phase 15 UI | ✅ |

---

## 1. External fixture catalog

Bundled catalog: `plugin/geomora/catalogs/default_fixtures.json`

- **External fixture catalog** (default on) merges extra items into room sets
- Optional **Fixture catalog path** for custom JSON
- Format:

```json
{
  "version": "1.0",
  "sets": {
    "kitchen": [{ "kind": "island", "width": 1200, "depth": 800, "height": 900, "anchor": "front_centre", "category": "fixture" }]
  }
}
```

---

## 2. Per-room furniture layouts

**Room furniture layouts** field:

```text
1:sofa@600,600|desk@1800,800
s2:1:bed@1200,900,2000x1500x500
```

- `room:kind@x,y` or `kind@x,y,WxDxH`
- Multiple items per room separated by `|`
- Storey prefix `sN:` for multi-storey layouts
- Overrides auto fixture placement for that room

---

## 3. Multi-storey room type overrides

**Room type overrides** now supports storey prefix:

```text
1:kitchen,s2:1:bedroom,s2:2:bathroom
```

- Ground floor: room 1 → kitchen
- Floor 2: room 1 → bedroom, room 2 → bathroom

---

## 4. Perpendicular wall constraints

When **Validate perpendicular walls** is enabled:

- Compares facade axis vs partition axis
- Sets `semantic.perpendicular` and `angle_to_facade` on partition walls
- Requires facade wall reference during IR build

---

## 5. LOD tour export + play

Menu: **Extensions → Geomora → LOD View**

| Action | Description |
|---|---|
| **Save LOD Tour JSON...** | Write manifest to file |
| **Play LOD Tour** | Step through scenes (timer-based in SketchUp) |

---

## 6. Workflow

```text
Room overrides: s1:1:kitchen,s2:1:bedroom
Room layouts: 1:sofa@600,600
Fixture catalog on (default)
→ LOD 300 + furniture → Generate
→ Create LOD Scene Pages → Play LOD Tour
```

---

## 7. Files

```text
plugin/geomora/catalogs/default_fixtures.json
plugin/geomora/core/fixture_catalog.rb
plugin/geomora/core/room_layout.rb
plugin/geomora/core/perpendicular_constraint_solver.rb
plugin/geomora/core/lod_presentation.rb
tests/core/fixture_catalog_test.rb
tests/core/room_layout_test.rb
tests/core/perpendicular_constraint_solver_test.rb
```

---

## 8. Deferred (Phase 16 — delivered in v0.25.0)

See `docs/PHASE_16.md` for catalog reload, collision avoidance, HTML tour export, layout presets, and perpendicular repair.

Remaining for Phase 17+:

- True animated LOD export (video/GIF)
- Visual room layout editor in Workspace

---

## 9. Gate to Phase 16

Catalog-driven layouts enable visual editing and presentation export pipelines.
