# Geomora Phase 12 — Room Semantics + Constraint Solver

**Status:** Phase 12 **COMPLETE** (v0.21.0)

| Step | Status |
|---|---|
| 12.1 Partition doors on interior walls | ✅ |
| 12.2 Room zone semantics in IR | ✅ |
| 12.3 Room zone geometry (`Geomora_Rooms`) | ✅ |
| 12.4 LOD scene presets (menu) | ✅ |
| 12.5 Constraint solver (`facade_constraint_v1`) | ✅ |
| 12.6 Workspace **Solve Constraints** button | ✅ |

---

## 1. Partition doors

When **Interior partition walls** and **Partition doors** are enabled:

- Each partition wall receives a centred door opening
- Opening id: `partition_door_{storey}_{index}`
- Component: `door_partition_{W}x{H}`
- Respects LOD — no partition doors at LOD 100

Params: `partition_door_width`, `partition_door_height`, optional `partition_door_offset`.

---

## 2. Room zones

When **Interior partition walls** and **Room zone labels** are enabled:

- IR top-level `rooms[]` with polygon, name, zone, `area_mm2`
- One room per bay between partition lines
- SketchUp: thin floor zone on tag `Geomora_Rooms` (LOD 200+)

Example room:

```json
{
  "id": "room_01_01",
  "storey_id": "storey_01",
  "name": "Room 1",
  "geometry": { "polygon": [[0,120,0],[4500,120,0],[4500,2880,0],[0,2880,0]] },
  "semantic": { "zone": "front_left", "room_type": "generic", "area_mm2": 12420000 }
}
```

---

## 3. LOD scene presets

Menu: **Extensions → Geomora → LOD View**

| Preset | Effect |
|---|---|
| LOD 100 — Massing | Hide openings, rooms, details |
| LOD 200 — Openings | Show rooms + openings; hide trim/eaves |
| LOD 300 — Details | Show all Geomora tags |

Uses `LodScenes.apply_preset` — no re-generate required.

---

## 4. Constraint solver

`ConstraintSolver.solve` applies explicit IR constraints:

```text
equal_width | equal_height | equal_spacing | align | symmetry
```

- **Rationalize** also runs solver when `constraints[]` is present
- **Solve Constraints** button applies constraints from IR (after Rationalize / Apply Pattern)

Output metadata: `constraint_solution.constraints_solved`.

---

## 5. Workflow

```text
Detect → Rationalize → Apply Pattern → Solve Constraints (optional)
→ Validate → Generate
```

For interior layout:

```text
Enable partitions + partition doors + room zones → Generate
```

Switch LOD view anytime via Geomora menu.

---

## 6. Files

```text
plugin/geomora/core/room_planner.rb
plugin/geomora/core/constraint_solver.rb
plugin/geomora/core/lod_scenes.rb
plugin/geomora/core/interior_layout.rb      — partition doors
plugin/geomora/core/ir_builder.rb           — rooms + partition openings
plugin/geomora/generators/room_generator.rb
plugin/geomora/ir/parser.rb                 — rooms[]
plugin/geomora/ui/commands.rb               — LOD View submenu
tests/core/room_planner_test.rb
tests/core/constraint_solver_test.rb
tests/core/lod_scenes_test.rb
```

---

## 7. Deferred (Phase 13+)

- Room-type assignment (kitchen, bedroom) from layout rules
- Partition doors at custom offsets per wall
- LOD animation / scene pages
- Interior furniture placement
- Full constraint graph (parallel, perpendicular, coplanar)

---

## 8. Gate to Phase 13

Room semantics + constraint solving enable layout refinement and furnishing pipelines on stacked interior shells.
