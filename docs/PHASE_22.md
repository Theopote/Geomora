# Geomora Phase 22 — H.264 MP4 + Booklet + Copy/Paste

**Status:** Phase 22 **COMPLETE** (v0.31.0)

| Step | Status |
|---|---|
| 22.1 H.264 MP4 export (ffmpeg + native fallback) | ✅ |
| 22.2 Layout PDF booklet (cover + TOC + spreads) | ✅ |
| 22.3 Layout editor copy/paste (Ctrl+C/V) | ✅ |
| 22.4 Viewport stream auto-resume on focus | ✅ |
| 22.5 Workspace + menu integration | ✅ |

---

## 1. H.264 MP4 export

Menu: **Export LOD Tour MP4 (H.264)...**

- With ffmpeg: `libx264` via existing frame capture pipeline
- Without ffmpeg: `H264FrameEncoder` (baseline I_PCM intra frames) + `H264Mp4Encoder` (`avc1` track)
- Broader player compatibility than JPEG-in-MP4 native export

---

## 2. Layout PDF booklet

Workspace: **Export layout booklet PDF**

- Cover page with title, date, room count
- Table of contents listing all rooms
- Two-room spreads per page after TOC

---

## 3. Layout editor copy/paste

| Shortcut | Action |
|---|---|
| Ctrl+C | Copy selected item |
| Ctrl+V | Paste with +200 mm offset (snap-aware) |

---

## 4. Viewport stream auto-resume

- Blur / tab hide pauses stream (Phase 21)
- Focus / tab visible resumes stream **if Live stream was enabled before pause**
- Uses `resume_viewport_stream` Ruby callback (no duplicate JS polling)

---

## 5. Workflow

```text
Layout editor → select item → Ctrl+C → Ctrl+V
Export layout booklet PDF → client handoff package
Create LOD Scene Pages → Export LOD Tour MP4 (H.264)
Live stream on → switch app → return → stream resumes
```

---

## 6. Files

```text
plugin/geomora/core/h264_bitstream.rb
plugin/geomora/core/h264_frame_encoder.rb
plugin/geomora/core/h264_mp4_encoder.rb
plugin/geomora/core/pdf_report_exporter.rb
plugin/geomora/ui/workspace/layout_editor.js
plugin/geomora/ui/workspace/app.js
tests/core/h264_mp4_encoder_test.rb
tests/core/pdf_booklet_exporter_test.rb
```

---

## 7. Deferred (Phase 23 — delivered in v0.32.0)

See `docs/PHASE_23.md` for compact H.264, booklet HTML, and multi-item clipboard.

Remaining for Phase 24+:

- Full CAVLC for non-flat macroblocks
- Layout editor marquee selection

---

## 8. Gate to Phase 23

Compact video and multi-format booklet exports complete the offline client review package.
