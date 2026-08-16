# Geomora Phase 18 — GIF Export + Editor Polish

**Status:** Phase 18 **COMPLETE** (v0.27.0)

| Step | Status |
|---|---|
| 18.1 Animated LOD GIF export | ✅ |
| 18.2 Catalog item palette (drag-drop) | ✅ |
| 18.3 Multi-storey layout editor tabs | ✅ |
| 18.4 Live isometric 3D preview | ✅ |
| 18.5 Workspace + menu integration | ✅ |

---

## 1. Animated LOD GIF export

Menu: **Extensions → Geomora → LOD View → Export LOD Tour GIF...**

- Captures each Geomora LOD scene page via `view.write_image`
- Decodes PNG frames (`PngReader`) and encodes animated GIF (`GifEncoder`)
- Falls back to gradient placeholder RGB when viewport capture is unavailable (tests/headless)

---

## 2. Catalog item palette

Workspace layout editor:

- Palette chips loaded from bundled catalog + `FixtureLibrary` sets
- **Drag** onto plan canvas or **click** to insert at default position
- `FixtureCatalog.palette(params)` deduplicates by `kind`

---

## 3. Multi-storey layout editor

- **Storey** selector appears when `storey_count > 1`
- Each floor loads rooms via `RoomLayoutEditor.preview_all_storeys`
- **Apply editor to layouts field** writes `s2:` prefixes automatically

---

## 4. Live isometric 3D preview

- Secondary canvas renders extruded furniture blocks from plan positions
- Updates while dragging items or adding from palette
- **Rotate selected 90°** updates plan rotation suffix in serialized layouts

---

## 5. Workflow

```text
storey_count = 2 → Open layout editor → switch Storey tabs
Drag sofa from palette → check 3D preview → Rotate selected 90°
Apply editor to layouts field → Generate
Create LOD Scene Pages → Export LOD Tour GIF
```

---

## 6. Files

```text
plugin/geomora/core/gif_encoder.rb
plugin/geomora/core/png_reader.rb
plugin/geomora/core/lod_capture.rb              (export_gif)
plugin/geomora/core/fixture_catalog.rb          (palette)
plugin/geomora/core/room_layout_editor.rb       (preview_all_storeys)
plugin/geomora/ui/workspace/layout_editor.js
tests/core/gif_encoder_test.rb
tests/core/png_reader_test.rb
tests/core/fixture_catalog_palette_test.rb
```

---

## 7. Deferred (Phase 19 — delivered in v0.28.0)

See `docs/PHASE_19.md` for MP4/WebM export, palette search, snap/magnet, and viewport snapshot.

Remaining for Phase 20+:

- In-dialog live viewport streaming
- Native MP4 without ffmpeg

---

## 8. Gate to Phase 19

Video export and live viewport preview complete the presentation pipeline for client deliverables.
