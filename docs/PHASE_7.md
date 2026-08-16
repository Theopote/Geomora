# Geomora Phase 7 — Full Building Elements

**Status:** Phase 7 **COMPLETE** (v0.14.0) · Phase 7+ **COMPLETE** (v0.15.0)

| Step | Status |
|---|---|
| 7.1 Floor slab generator (`floor`) | ✅ |
| 7.2 Roof slab generator (`roof`) | ✅ |
| 7.3 Column generator (`column`) | ✅ |
| 7.4 Beam generator (`beam`) | ✅ |
| 7.5 Stair generator (`stair`) | ✅ |
| 7.6 `BuildingComposer` + Workspace toggles | ✅ |
| 7.7 Balcony (`balcony`) | ✅ |
| 7.8 Parapet (`parapet`) | ✅ |
| 7.9 Cornice (`cornice`) | ✅ |

---

## 1. Goal

Extend the facade-first pipeline to generate a **full building shell** around the primary wall:

```text
Facade wall + openings
      ↓
Optional floor / roof / columns / beam / stair / balcony / parapet / cornice
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
| `balcony` | `position`, `width`, `depth`, `thickness`, `direction` |
| `parapet` | `baseline`, `height`, `thickness` (roof edge wall) |
| `cornice` | `baseline`, `width`, `height`, `projection` (facade molding) |

Footprint defaults to a rectangle centred on the facade wall (`building_depth`, default 6000 mm).

**Balcony** aligns to the first window (offset, width, sill). **Parapet** runs along the front roof edge. **Cornice** is a horizontal band at the wall top.

---

## 3. Workspace

Inspector panel **Building Elements (Phase 7)**:

- Floor slab (default on)
- Roof slab (default on)
- Columns / Beam / Stair (optional)
- Balcony / Parapet / Cornice (optional)
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
Geomora_Balconies
Geomora_Parapets
Geomora_Cornices
```

---

## 5. Deferred (Phase 8+)

- Multi-storey stacks
- Wall joins and structural grids
- LOD 200/300 semantic refinement

---

## 6. Gate to Phase 8

Phase 7+ completes exterior shell elements. Phase 8 (Geometry Doctor) can clean and repair generated shells.
