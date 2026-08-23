# A1 Detection Baseline Report

**Status:** Archived A1 snapshot · SketchUp E2E review completed
**Date:** 2026-08-16  
**Source:** `backend/cache/benchmark_a1_e2e.json`

---

## Summary

> **Archived A1 snapshot.** `docs/ROADMAP.md` is the source of truth for current
> progress. The E2E review was subsequently completed for 20/20 photos with
> average legacy RQS 69.3; see `backend/cache/benchmark_a1_e2e.json`. Those
> subjective scores are a baseline, not Reconstruction Metrics v1 ground truth.

| Metric | Value |
|--------|-------|
| Manifest images | 20 |
| Detection smoke pass | **18/20** |
| train detect pass | 10/10 |
| val detect pass | 5/5 |
| hold-out detect pass | **3/5** |

**RC-G1 target (legacy A3):** hold-out ≥4/5 Generate after ~1 min overlay · val window recall ≥0.80

---

## Hold-out (review first — never train)

| ID | Category | Windows | Doors | Conf | Hints | Smoke | SketchUp action |
|----|----------|---------|-------|------|-------|-------|-----------------|
| photo_16 | strong_perspective | 0 | 1 | 0.35 | missed_window, false_door | **FAIL** | 删误检门 + Draw window |
| photo_17 | low_light_reflection | 0 | 1 | 0.52 | missed_window, false_door, bad_rectify | **FAIL** | 手拖四角 Rectify + 补窗 |
| photo_18 | tree_occluded | 2 | 1 | 0.38 | opening_detection | PASS | 核对每框，记录 RQS |
| photo_19 | old_building | 10 | 0 | 0.75 | false_window | PASS | Delete 多余窗框 |
| photo_20 | tree_occluded | 7 | 1 | 0.62 | bad_rectify | PASS | 手拖四角 Rectify |

---

## Failure taxonomy (A2 targets)

| Class | Count (automated hints) | Notes |
|-------|-------------------------|-------|
| `bad_rectify` | 10 | Mostly `auto_full_frame` — need manual 4-corner |
| `false_window` | 3 | 8–10 window over-detection |
| `missed_window` | 2 | Both hold-out hard fails |
| `false_door` | 2 | Door detected when 0 windows |
| `opening_detection` | 4 | Confidence < 0.5 |

---

## Workflow

```powershell
cd F:\development\Geomora\backend

# 1. Regenerate checklist (overlays + HTML + CSV)
.\.venv\Scripts\python scripts\export_a1_checklist.py

# 2. Open cache\benchmark_a1\index.html — hold-out first

# 3. SketchUp E2E each image, fill checklist_scores.csv

# 4. Import scores
.\.venv\Scripts\python scripts\import_a1_e2e_scores.py
```

---

## E2E status (updated after score import)

| Field | Status |
|-------|--------|
| SketchUp reviewed | 20/20 |
| Legacy RQS recorded | 20/20 (average 69.3) |
| hold-out Generate OK | 5/5 |

Reconstruction Metrics v1 annotations remain separate work: the legacy review
does not contain reliable opening boxes, storey/bay assignments, or measured
dimensions and therefore must not be converted into objective ground truth.
