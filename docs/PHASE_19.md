# Geomora Phase 19 — Video Export + Live View

**Status:** Phase 19 **COMPLETE** (v0.28.0)

| Step | Status |
|---|---|
| 19.1 MP4/WebM video export (ffmpeg hook) | ✅ |
| 19.2 Palette search + custom item sizing | ✅ |
| 19.3 Snap-to-grid + wall magnet | ✅ |
| 19.4 SketchUp viewport snapshot in Workspace | ✅ |
| 19.5 Workspace + menu integration | ✅ |

---

## 1. LOD tour video export

Menu: **Extensions → Geomora → LOD View**

| Action | Description |
|---|---|
| **Export LOD Tour MP4...** | Capture frames → encode with ffmpeg when available |
| **Export LOD Tour WebM...** | VP9 WebM via ffmpeg |

When ffmpeg is not in PATH:

- PNG frames are still exported to cache
- `encode_lod_tour.ps1` (Windows) or `encode_lod_tour.sh` (Unix) is written alongside frames

---

## 2. Palette search + custom sizing

Layout editor:

- **Palette search** filters catalog chips by kind/label
- Select a furniture block → **W / D / H** fields appear
- **Apply size** writes custom dimensions into serialized layouts (`sofa@600,600,2000x900x800`)

---

## 3. Snap-to-grid + wall magnet

- **Snap to grid (100 mm)** — positions round to 100 mm while dragging
- **Wall magnet** — snaps within 80 mm of interior wall inset lines
- Grid overlay drawn on plan canvas when snap is enabled
- Ruby helper: `LayoutSnap.snap_position` (mirrors editor logic for tests)

---

## 4. Live viewport snapshot

Sources panel: **Live View (Phase 19)**

- **Refresh viewport** — captures active SketchUp view as PNG data URL
- **Auto (3s)** — polls viewport snapshot every 3 seconds
- `ViewportSnapshot.capture` uses `view.write_image` when available

---

## 5. Workflow

```text
Open layout editor → search palette → drag sofa → snap to wall
Apply size → Apply editor to layouts field → Generate
Refresh viewport (or Auto) while reviewing model
Create LOD Scene Pages → Export LOD Tour MP4
```

---

## 6. Files

```text
plugin/geomora/core/lod_video_exporter.rb
plugin/geomora/core/viewport_snapshot.rb
plugin/geomora/core/layout_snap.rb
plugin/geomora/ui/workspace/layout_editor.js
tests/core/lod_video_exporter_test.rb
tests/core/viewport_snapshot_test.rb
tests/core/layout_snap_test.rb
```

---

## 7. Deferred (Phase 20+)

- In-dialog live viewport streaming (no manual refresh)
- MP4 export without ffmpeg (native encoder)
- Layout editor undo/redo stack
- Batch export all storeys as layout PDF

---

## 8. Gate to Phase 20

Video export and live viewport preview complete the presentation pipeline for client deliverables beyond static GIF/HTML.
