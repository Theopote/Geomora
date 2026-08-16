# Geomora Phase 7 — Full Building Elements

**Status:** Bootstrap **COMPLETE** (v0.14.0)

| Step | Status |
|---|---|
| 7.1 Floor slab generator (`floor`) | ✅ |
| 7.2 Roof slab generator (`roof`) | ✅ |
| 7.3 Column generator (`column`) | ✅ |
| 7.4 Beam generator (`beam`) | ✅ |
| 7.5 Stair generator (`stair`) | ✅ |
| 7.6 `BuildingComposer` + Workspace toggles | ✅ |
| 7.7 Balcony / Parapet / Cornice | ⏳ deferred |

---

## 1. Goal

Extend the facade-first pipeline to generate a minimal **full building shell** around the primary wall:

```text
Facade wall + openings
      ↓
Optional floor / roof / columns / beam / stair
      ↓
SketchUp geometry (tagged layers)
```

---

## 2. IR element types

| Type | Geometry |
|---|---|
| `floor` | `polygon`, `thickness`, `elevation` |
| `roof` | `polygon`, `thickness`, `elevation` (top of wall) |
| `column` | `position`, `width`, `depth`, `height` |
| `beam` | `baseline`, `width`, `height` |
| `stair` | `origin`, `width`, `run`, `rise`, `steps` |

Footprint defaults to a rectangle centred on the facade wall (`building_depth`, default 6000 mm).

---

## 3. Workspace

Inspector panel **Building Elements (Phase 7)**:

- Floor slab (default on)
- Roof slab (default on)
- Columns / Beam / Stair (optional)
- Building depth (mm)

Generate creates IR elements via `Core::BuildingComposer` and dispatches to generators in `StoreyGenerator`.

---

## 4. Tags

```text
Geomora_Floors
Geomora_Roofs
Geomora_Columns
Geomora_Beams
Geomora_Stairs
```

---

## 5. Deferred (Phase 7+)

- Balcony, parapet, cornice
- Multi-storey stacks
- Wall joins and structural grids
- LOD 200/300 semantic refinement

---

## 6. Gate to Phase 8

Phase 7 proves the IR + generator path for non-facade elements. Phase 8 (Geometry Doctor) can clean and repair generated shells.
