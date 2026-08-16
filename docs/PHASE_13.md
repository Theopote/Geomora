# Geomora Phase 13 — Room Types + Furniture + LOD Scenes

**Status:** Phase 13 **COMPLETE** (v0.22.0)

| Step | Status |
|---|---|
| 13.1 Auto room type classification | ✅ |
| 13.2 Per-partition door offsets | ✅ |
| 13.3 LOD Scene Pages (SketchUp scenes) | ✅ |
| 13.4 Furniture placement by room type | ✅ |
| 13.5 Constraint solver v2 (horizontal / vertical / ack) | ✅ |
| 13.6 Workspace Phase 13 UI | ✅ |

---

## 1. Room type classification

When **Auto room types** is enabled (default with room zones):

| Rule | Type |
|---|---|
| Single room | `living` |
| Ground floor, first bay | `living` |
| Smallest bay (3+ rooms) | `bathroom` |
| Largest bay | `bedroom` |
| Two-room layout, second bay | `study` |
| Narrow bays | `corridor` |

Room names update to match: e.g. `Living Room 1`, `Bedroom 2`.

`RoomClassifier` runs after `RoomPlanner` in `IRBuilder`.

---

## 2. Per-partition door offsets

**Partition door offsets** accepts comma-separated mm values:

```text
1200, 1800
```

- One value per partition wall (left to right)
- Falls back to centred door when omitted
- Global `partition_door_offset` still works for single-partition layouts

---

## 3. LOD Scene Pages

Menu: **Extensions → Geomora → LOD View → Create LOD Scene Pages**

Creates/updates three SketchUp scenes:

- `Geomora LOD 100`
- `Geomora LOD 200`
- `Geomora LOD 300`

Each scene stores layer visibility via `LodScenePages` + `LodVisibility`.

---

## 4. Furniture placement

When **Place furniture (LOD 300)** is enabled:

| Room type | Furniture |
|---|---|
| `living` | sofa |
| `bedroom` | bed |
| `bathroom` | vanity |
| `kitchen` | counter |
| `study` | desk |
| `corridor` | bench |
| `generic` | table |

IR top-level `furniture[]`; SketchUp tag `Geomora_Furniture` (LOD 300 only).

---

## 5. Constraint solver v2

`facade_constraint_v2` adds:

| Type | Behaviour |
|---|---|
| `horizontal` | Align sill heights (same as `align`) |
| `vertical` | Align window offsets to median |
| `parallel` / `perpendicular` / `coplanar` | Acknowledged in metadata (structural; no facade mutation) |

Output: `constraints_solved` + `constraints_acknowledged`.

---

## 6. Workflow

```text
Partitions + room zones + room types
→ (optional) furniture at LOD 300
→ Validate → Generate
→ Create LOD Scene Pages (menu)
```

---

## 7. Files

```text
plugin/geomora/core/room_classifier.rb
plugin/geomora/core/furniture_planner.rb
plugin/geomora/core/lod_scene_pages.rb
plugin/geomora/core/constraint_solver.rb       — v2
plugin/geomora/core/interior_layout.rb         — per-wall offsets
plugin/geomora/generators/furniture_generator.rb
tests/core/room_classifier_test.rb
tests/core/furniture_planner_test.rb
tests/core/lod_scene_pages_test.rb
```

---

## 8. Deferred (Phase 14+)

- Custom room-type overrides per room
- Multi-piece furniture sets per room
- LOD scene animation / presentation export
- Kitchen/bathroom fixture libraries
- Full structural constraint solving (parallel wall geometry)

---

## 9. Gate to Phase 14

Typed rooms + furniture blocks enable fixture libraries and layout refinement on multi-storey interiors.
