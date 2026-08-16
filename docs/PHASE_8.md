# Geomora Phase 8 — Geometry Doctor

**Status:** Phase 8 bootstrap **COMPLETE** (v0.16.0)

| Step | Status |
|---|---|
| 8.1 Tiny edge removal | ✅ |
| 8.2 Tiny face removal | ✅ |
| 8.3 Coplanar face merge | ✅ |
| 8.4 Duplicate face removal | ✅ |
| 8.5 Duplicate component instance removal | ✅ |
| 8.6 Face normal repair | ✅ |
| 8.7 Vertex grid alignment (optional) | ✅ |
| 8.8 Opening gap audit | ✅ |
| 8.9 Component inventory report | ✅ |
| 8.10 Workspace **Repair Geometry** + menu item | ✅ |

---

## 1. Goal

Post-generation cleanup for Geomora project geometry in the active SketchUp model:

```text
Generate building shell
      ↓
Geometry Doctor (audit + repair in one undo step)
      ↓
Cleaner solids, merged coplanar faces, repair report
```

---

## 2. Operations

| Operation | Default | Description |
|---|---|---|
| Tiny edges | on | Erase edges shorter than 1 mm |
| Tiny faces | on | Erase faces smaller than 100 mm² |
| Coplanar merge | on | Erase edges between coplanar adjacent faces |
| Duplicate faces | on | Remove faces with identical vertex signatures |
| Duplicate instances | on | Remove component instances with same def + origin |
| Normal repair | on | Reverse faces whose normals point toward container center |
| Alignment repair | off | Snap vertices to grid (default 10 mm) |
| Opening audit | on | Count solid walls with no inner opening loops |

---

## 3. API

```ruby
Geomora::Core::Project.repair_geometry(options)
Geomora::Core::Project.audit_geometry(options)
```

`options` may include `project_id` to scope repair, or repair all Geomora project roots when omitted.

Workspace passes `geometry_doctor` toggles from the inspector panel and `expected_openings` from window/door counts.

---

## 4. Report keys

```text
tiny_edges_removed
tiny_faces_removed
coplanar_edges_merged
duplicate_faces_removed
duplicate_instances_removed
normals_reversed
vertices_snapped
empty_groups_removed
opening_gaps_found
components — entity_type counts
issues_before / issues_after — audit tallies
```

---

## 5. Deferred (Phase 8+)

- Automatic opening re-cut when gaps detected
- Wall join cleanup across storeys
- Semantic LOD-aware repair rules
- IR-linked repair (re-cut from opening IR without manual params)

---

## 6. Gate to Phase 9

Geometry Doctor provides baseline mesh hygiene. **Phase 9** adds multi-storey stacks and perimeter wall joins — see `docs/PHASE_9.md`.
