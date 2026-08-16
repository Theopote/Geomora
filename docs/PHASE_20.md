# Geomora Phase 20 — Stream + Native Video + Layout Report

**Status:** Phase 20 **COMPLETE** (v0.29.0)

| Step | Status |
|---|---|
| 20.1 Ruby viewport live stream | ✅ |
| 20.2 Native AVI export (no ffmpeg) | ✅ |
| 20.3 Layout editor undo/redo | ✅ |
| 20.4 Multi-storey layout report HTML | ✅ |
| 20.5 Workspace + menu integration | ✅ |

---

## 1. Viewport live stream

Sources panel: **Live stream (1s)**

- Uses SketchUp `UI.start_timer` when available (Ruby-driven, not JS polling)
- Falls back to JS interval when timer API unavailable (tests/headless)
- Replaces Phase 19 manual **Auto (3s)** checkbox

Callbacks: `start_viewport_stream`, `stop_viewport_stream`

---

## 2. Native AVI export (no ffmpeg)

Menu: **Export LOD Tour AVI (native)...**

- Pure Ruby `AviEncoder` writes uncompressed RGB24 AVI
- **Export LOD Tour MP4** auto-falls back to `.avi` when ffmpeg is missing

---

## 3. Layout editor undo/redo

- **Undo** / **Redo** buttons (50-step history)
- History commits after drag, palette drop, rotate, apply size
- Ctrl+Z not wired (HtmlDialog focus) — use buttons

---

## 4. Layout report export

Workspace: **Export layout report**

- Generates printable HTML with SVG floor plan per room
- All storeys and rooms from `RoomLayoutEditor.preview_all_storeys`
- Print to PDF from browser (File → Print)

---

## 5. Workflow

```text
Live stream on → edit model → viewport updates every 1s
Layout editor → drag items → Undo/Redo → Export layout report
Create LOD Scene Pages → Export LOD Tour AVI (native)
```

---

## 6. Files

```text
plugin/geomora/core/avi_encoder.rb
plugin/geomora/core/viewport_stream.rb
plugin/geomora/core/layout_report_exporter.rb
plugin/geomora/ui/workspace/layout_editor.js
tests/core/avi_encoder_test.rb
tests/core/layout_report_exporter_test.rb
tests/core/viewport_stream_test.rb
```

---

## 7. Deferred (Phase 21+)

- True MP4 mux without ffmpeg
- Layout editor keyboard shortcuts
- PDF export without browser print
- Viewport stream pause on dialog blur

---

## 8. Gate to Phase 21

Streaming viewport and native video close the presentation loop for offline client deliverables.
