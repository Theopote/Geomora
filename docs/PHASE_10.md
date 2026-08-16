# Geomora Phase 10 — LOD + Structural Grid

**Status:** Phase 10 **COMPLETE** (v0.18.0) · Per-floor windows (v0.19.0)

| Step | Status |
|---|---|
| 10.1 LOD policy (100 / 200 / 300) | ✅ |
| 10.2 LOD-aware IR + generation filtering | ✅ |
| 10.3 Structural column grid | ✅ |
| 10.4 LOD 300 trim / railing / eaves | ✅ |
| 10.5 Window mullion at LOD 300 | ✅ |
| 10.6 Workspace LOD + grid UI | ✅ |
| 10.7 Per-floor window editor | ✅ |

---

## 1. LOD semantics

| Level | Includes |
|---|---|
| **LOD 100** | Floor, roof, wall massing — no openings |
| **LOD 200** | + windows, doors, columns, balcony, beam, stair, parapet |
| **LOD 300** | + cornice, trim lintels, balcony railing, roof eaves, window mullion |

`project.lod_level` stored in IR; geometry metadata `lod_level` on project/storey/detail groups.

---

## 2. Structural grid

When **Structural column grid** is enabled (requires **Columns**):

- Columns at grid intersections across footprint
- Params: `grid_x_spacing`, `grid_y_spacing` (default ≈ half span)
- Replaces corner-only columns when grid is on
- Column semantic: `{ grid: true }`

---

## 3. LOD 300 elements

| Type | Tag | Description |
|---|---|---|
| `trim` | `Geomora_Trim` | Lintel band above each window |
| `railing` | `Geomora_Railings` | Balcony guard band |
| `eaves` | `Geomora_Eaves` | Front roof overhang |

---

## 4. Per-floor windows (v0.19.0)

- Set **Storey count** > 1 → floor tabs appear above the window list
- **Repeat openings on** (default): upper floors copy ground floor; only Ground is editable
- **Repeat openings off**: edit each floor independently; overlay shows active floor only
- **Copy ground to all floors** — one-click sync
- IR: `storey_windows[]` array; Generate uses per-floor layouts

---

## 5. Deferred (Phase 11+)

- LOD-driven layer visibility in SketchUp
- Interior partition walls
- Full frame / sill / jamb trim sets

---

## 6. Gate to Phase 11

LOD + structural grid enable semantic refinement pipelines and interior layout on stacked shells.
