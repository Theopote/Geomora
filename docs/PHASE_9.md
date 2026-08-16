# Geomora Phase 9 — Multi-Storey + Wall Joins

**Status:** Phase 9 bootstrap **COMPLETE** (v0.17.0)

| Step | Status |
|---|---|
| 9.1 Multi-storey IR (`storey_count`, cumulative elevation) | ✅ |
| 9.2 Repeat openings on upper floors | ✅ |
| 9.3 Per-storey floor slabs; roof on top storey only | ✅ |
| 9.4 Perimeter walls (back / left / right) | ✅ |
| 9.5 Wall join processor (intersect + coplanar merge) | ✅ |
| 9.6 Storey elevation validation | ✅ |
| 9.7 Workspace UI toggles | ✅ |

---

## 1. Goal

Stack repeated storeys vertically and close the building footprint with joined perimeter walls:

```text
Facade params + storey_count
      ↓
IR: storey_01 … storey_N (cumulative elevation)
      ↓
Generate → intersect perimeter walls at corners
```

---

## 2. Workspace params

| Param | Default | Description |
|---|---|---|
| `storey_count` | 1 | Number of stacked floors |
| `storey_height` | wall height | Per-storey vertical extent (mm) |
| `repeat_openings` | on | Copy window pattern to upper floors |
| `building_elements.perimeter_walls` | off | Add back/left/right walls + corner joins |

Door remains on **ground floor only**. Balcony / cornice on facade storey; roof / parapet on **top storey**.

---

## 3. IR layout

- Storey IDs: `storey_01`, `storey_02`, …
- Facade wall per storey: `wall_01_01`, `wall_02_01`, …
- Perimeter walls: `wall_01_back`, `wall_01_left`, `wall_01_right`, …
- Window IDs: `window_01_01`, `window_02_01`, … (per storey)

Wall semantic when perimeter enabled:

```json
{ "exterior": true, "join_group": "perimeter", "join_role": "facade|back|left|right" }
```

---

## 4. Wall joins

`Generators::WallJoinProcessor` runs after walls in a storey with matching `join_group`:

1. `intersect_with` between each wall pair
2. Erase edges between coplanar adjacent faces

---

## 5. Deferred (Phase 9+)

- Per-storey opening editors (different window layouts per floor)
- T / L junctions beyond rectangular footprint
- Multi-wall facades (non-rectangular plans)
- Automatic opening re-cut after wall join

---

## 6. Gate to Phase 10

Multi-storey shells with joined perimeter walls enable **LOD refinement and structural grids** — see `docs/PHASE_10.md`.
