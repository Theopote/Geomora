# Geomora Phase 6 — Multi-view Reconstruction

**Status:** Core bootstrap **COMPLETE** (v0.9.0)

| Step | Status |
|---|---|
| 6.1 Planning + API contract | ✅ |
| 6.2 Feature matching + planar homography (`feature_homography_v1`) | ✅ |
| 6.3 `POST /multiview/register` + Ruby client | ✅ |
| 6.4 Workspace secondary image + Register Views | ✅ |
| 6.5 Depth / COLMAP / opening fusion | ⏳ deferred |

---

## 1. Goal

Register **two facade photographs** of the same building plane and store camera-relative alignment metadata in IR `sources[]`.

```text
Primary image + Secondary image
      ↓
ORB feature match + RANSAC homography
      ↓
Multiview metadata (transform view_002 → view_001)
      ↓
IR sources[] (primary + secondary)
      ↓
Continue single-facade pipeline (Rectify → Detect → Rationalize → Generate)
```

Phase 6 bootstrap aligns views in **image space**. Depth estimation and full 3D fusion are deferred.

---

## 2. Backend (`feature_homography_v1`)

| Step | Tool |
|---|---|
| Feature detection | OpenCV ORB (5000 keypoints) |
| Matching | BFMatcher Hamming, cross-check |
| Pose / plane | `cv2.findHomography` (RANSAC, 5 px) |
| Output | 3×3 homography mapping secondary → primary pixels |

### `POST /multiview/register`

```http
POST /multiview/register
Content-Type: multipart/form-data

primary: <file>
secondary: <file>
```

**Response:**

```json
{
  "method": "feature_homography_v1",
  "confidence": 0.82,
  "match_count": 156,
  "inlier_count": 98,
  "homography": [[...], [...], [...]],
  "views": [
    { "id": "view_001", "role": "primary", "image_width": 800, "image_height": 600 },
    { "id": "view_002", "role": "secondary", "image_width": 800, "image_height": 600,
      "transform_to_primary": [[...]] }
  ]
}
```

---

## 3. Workspace workflow

1. **Load Primary Image** — main facade photo (existing flow)
2. **Load Secondary Image** — another angle of same facade
3. **Register Views** — calls `/multiview/register`, shows match/inlier counts
4. Continue: Rectify → Detect → Rationalize → Apply Pattern → Generate

Multi-view metadata is stored in IR `sources[]` on Generate.

---

## 4. Files

```text
backend/geomora_multiview/
├── feature_match.py
├── models.py
└── pipeline.py
plugin/geomora/perception/
├── multiview_client.rb
└── multiview_result.rb
tests/backend/
├── test_multiview_pipeline.py
└── test_multiview_endpoint.py
```

---

## 5. Future (Phase 6.5+)

- Monocular depth (Depth Anything / Marigold) for opening depth ranking
- COLMAP sparse reconstruction for true camera poses
- Fuse detections from multiple rectified views into one opening set

---

## 6. Gate to Phase 7

Phase 6 links multiple **photos** to one facade session. Phase 7 extends geometry to full building elements (floor, roof, stair, etc.).
