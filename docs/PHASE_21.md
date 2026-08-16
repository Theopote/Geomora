# Geomora Phase 21 — Native MP4 + PDF + Shortcuts

**Status:** Phase 21 **COMPLETE** (v0.30.0)

| Step | Status |
|---|---|
| 21.1 Native MP4 mux (no ffmpeg) | ✅ |
| 21.2 Layout PDF export | ✅ |
| 21.3 Layout editor keyboard shortcuts | ✅ |
| 21.4 Viewport stream pause on blur | ✅ |
| 21.5 Workspace + menu integration | ✅ |

---

## 1. Native MP4 export

Menu: **Export LOD Tour MP4 (native)...**

- `JpegFrameEncoder` — minimal baseline JPEG per frame
- `Mp4Encoder` — ISO BMFF mux with `jpeg` video track
- **Export LOD Tour MP4** without ffmpeg tries native MP4 first, falls back to AVI on error

---

## 2. Layout PDF export

Workspace: **Export layout PDF**

- `PdfReportExporter` writes vector PDF (room outline + furniture blocks + item list)
- No browser print required

---

## 3. Keyboard shortcuts (layout editor)

| Shortcut | Action |
|---|---|
| Ctrl+Z | Undo |
| Ctrl+Y | Redo |
| R | Rotate selected 90° |
| Del / Backspace | Remove selected item |

---

## 4. Viewport stream pause

- **Live stream** pauses when Workspace tab/window loses focus (`blur` / `visibilitychange`)
- Dialog close stops stream via `set_on_closed`
- Callbacks: `pause_viewport_stream`, `resume_viewport_stream`

---

## 5. Workflow

```text
Layout editor → drag items → Ctrl+Z / Ctrl+Y
Export layout PDF → open in PDF viewer
Create LOD Scene Pages → Export LOD Tour MP4 (native)
```

---

## 6. Files

```text
plugin/geomora/core/jpeg_frame_encoder.rb
plugin/geomora/core/mp4_encoder.rb
plugin/geomora/core/pdf_report_exporter.rb
plugin/geomora/core/viewport_stream.rb
plugin/geomora/ui/workspace/layout_editor.js
tests/core/mp4_encoder_test.rb
tests/core/pdf_report_exporter_test.rb
tests/core/jpeg_frame_encoder_test.rb
```

---

## 7. Deferred (Phase 22 — delivered in v0.31.0)

See `docs/PHASE_22.md` for H.264 MP4, PDF booklet, copy/paste, and viewport auto-resume.

Remaining for Phase 23+:

- Smaller native H.264 file size (DCT intra encoding)

---

## 8. Gate to Phase 22

H.264 video and printable booklet complete the client presentation package.
