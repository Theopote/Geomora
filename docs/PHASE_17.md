# Geomora Phase 17 — Visual Layout + LOD Capture

**Status:** Phase 17 **COMPLETE** (v0.26.0)

| Step | Status |
|---|---|
| 17.1 Visual room layout editor | ✅ |
| 17.2 Furniture rotation + wall alignment | ✅ |
| 17.3 Catalog diff preview | ✅ |
| 17.4 LOD viewport capture export | ✅ |
| 17.5 Workspace Phase 17 UI | ✅ |

---

## 1. Visual room layout editor

Workspace: **Open layout editor**

- Canvas preview of each room footprint (from wall length, depth, partition count)
- Drag furniture blocks; positions are in millimetres
- **Apply editor to layouts field** writes `room_furniture_layouts`
- Ruby preview: `RoomLayoutEditor.preview(params)`

---

## 2. Furniture rotation + wall alignment

**Room furniture layouts** extended syntax:

```text
1:sofa@600,600@90
2:bed@wall_north
```

- `@90` — rotation in degrees (0/90/180/270)
- `@wall_north|wall_south|wall_east|wall_west` — snap against room walls
- **Wall-aligned furniture placement** applies orientation during auto placement

`FurnitureGenerator` extrudes rotated footprints when `geometry.rotation` is set.

---

## 3. Catalog diff preview

Workspace: **Preview catalog diff**

- Compares in-memory cached catalog vs on-disk JSON
- Shows added / removed / changed room sets before reload
- `FixtureCatalog.diff(params)`

---

## 4. LOD viewport capture export

Menu: **Extensions → Geomora → LOD View**

| Action | Description |
|---|---|
| **Export LOD Capture HTML...** | Slideshow with embedded viewport PNG captures |
| **Export LOD Tour Frames...** | PNG sequence per LOD scene page |

Uses `view.write_image` when SketchUp viewport is available; placeholder PNG in headless/tests.

---

## 5. Workflow

```text
Open layout editor → drag items → Apply editor to layouts field
Preview catalog diff → edit JSON → Reload fixture catalog
Wall align on → layout with wall_north anchors → Generate
Create LOD Scene Pages → Export LOD Capture HTML
```

---

## 6. Files

```text
plugin/geomora/core/room_layout_editor.rb
plugin/geomora/core/furniture_orientation.rb
plugin/geomora/core/lod_capture.rb
plugin/geomora/core/fixture_catalog.rb          (diff)
plugin/geomora/core/room_layout.rb              (rotation syntax)
plugin/geomora/ui/workspace/layout_editor.js
tests/core/room_layout_editor_test.rb
tests/core/furniture_orientation_test.rb
tests/core/lod_capture_test.rb
tests/core/fixture_catalog_diff_test.rb
```

---

## 7. Deferred (Phase 18+)

- True GIF/video encoder from captured frames
- Full drag-and-drop catalog item palette in editor
- Multi-storey layout editor tabs
- Live 3D furniture preview in Workspace

---

## 8. Gate to Phase 18

Captured LOD tours and visual layout editing close the loop between interior planning and client presentation.
