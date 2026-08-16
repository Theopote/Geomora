# Geomora Phase 23 — Compact H.264 + Booklet HTML + Multi-select

**Status:** Phase 23 **COMPLETE** (v0.32.0)

| Step | Status |
|---|---|
| 23.1 Compact native H.264 (I_16x16 DC + CAVLC) | ✅ |
| 23.2 Layout booklet HTML export | ✅ |
| 23.3 Multi-item clipboard (Ctrl+click, Ctrl+A) | ✅ |
| 23.4 Workspace + tests integration | ✅ |

---

## 1. Compact native H.264

Native H.264 export (no ffmpeg) now uses **I_16x16_0_0_0** macroblocks with DC-only CAVLC residuals instead of I_PCM.

- `H264Cavlc` — minimal coeff_token / level encoding for flat macroblocks
- `H264FrameEncoder` — Hadamard DC transform per 16×16 MB
- Smaller `.mp4` files at same resolution vs Phase 22 I_PCM fallback

Menu **Export LOD Tour MP4 (H.264)...** unchanged; native path is automatically more compact.

---

## 2. Layout booklet HTML

Workspace: **Export layout booklet HTML**

- Cover page + linked table of contents
- Two-room spreads (matches PDF booklet layout)
- Print to PDF from browser optional

---

## 3. Multi-item clipboard

| Action | Shortcut |
|---|---|
| Multi-select | Ctrl+click items |
| Select all | Ctrl+A |
| Copy | Ctrl+C (all selected items) |
| Paste | Ctrl+V (batch paste with staggered offset) |
| Delete | Del / Backspace (all selected) |

---

## 4. Workflow

```text
Ctrl+click sofa + table → Ctrl+C → Ctrl+V
Export layout booklet HTML → share with client
Export LOD Tour MP4 (H.264) without ffmpeg → smaller file
```

---

## 5. Files

```text
plugin/geomora/core/h264_cavlc.rb
plugin/geomora/core/h264_frame_encoder.rb
plugin/geomora/core/layout_report_exporter.rb
plugin/geomora/ui/workspace/layout_editor.js
tests/core/h264_cavlc_test.rb
tests/core/layout_booklet_html_exporter_test.rb
```

---

## 6. Deferred (Phase 24+)

- Full CAVLC tables for detailed macroblocks
- Booklet cover branding / logo slot
- Drag-select marquee in layout editor

---

## 7. Gate to Phase 24

Compact video and multi-format booklet exports complete the offline client review package.
