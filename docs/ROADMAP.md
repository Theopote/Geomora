# Geomora Roadmap

**This file is the single source of truth for project milestones and priorities.**

Phase design docs (`docs/PHASE_*.md`) explain *what* each layer does. They do **not** declare global progress — only this file does.

**Updated:** v0.36.0 · 2026-08-16

---

## Current milestone

### A1 — Real Photo Benchmark (in progress)

**Goal:** Establish an honest baseline before any further feature work.

| Item | Target | Status |
|------|--------|--------|
| 20 real building photos curated | 5 res / 3 office / 3 old / 3 commercial / 2 occluded / 2 perspective / 2 low-light | ⚠️ 28 local, manifest selecting 20 |
| Split: train / val / hold-out | 10 / 5 / 5 (hold-out never in training) | ⚠️ manifest created |
| Run full Photo → SketchUp workflow | All 20 | ☐ SketchUp manual pass pending |
| Export checklist pack | `cache/benchmark_a1/index.html` | ✅ ready |
| Record failures (no code fixes yet) | `cache/benchmark_a1_e2e.json` | ✅ detection baseline done |
| Detection CLI baseline | 18/20 smoke pass (hold-out 3/5) | ✅ see `docs/A1_BASELINE_REPORT.md` |

**Exit:** Failure taxonomy populated; RQS scores recorded per image; hold-out untouched.

---

## Milestone queue

| ID | Name | Gate | Status |
|----|------|------|--------|
| **A1** | Real Photo Benchmark | 20 photos, baseline recorded | **In progress** |
| **A2** | Failure-driven Improvement | Fix only documented failure classes | Frozen until A1 done |
| **A3** | Reconstruction Gate | hold-out ≥4/5 usable SketchUp after ~1 min overlay; window recall ≥0.80 on val; Generate stable | Frozen until A2 done |
| **B0** | Constraint Graph Solver | Equal-width / equal-sill / equal-spacing after A3 | P0 after Stage A |
| B1 | Multi-view production path | Fuse + depth on real photos | P1 |
| B2 | Evidence-driven model selection | SAM / depth only if RQS gain proven | P1 |

---

## Completed

| Area | Version | Notes |
|------|---------|-------|
| Phase 0 — IR + SketchUp kernel | v0.1 | Deterministic geometry foundation |
| Phase 1 — Workspace | v0.2 | HtmlDialog + manual facade |
| Phase 2 — Rectification | v0.5 | 4-corner UI + OpenCV backend |
| Phase 3 — Detection bootstrap | v0.34 | YOLO train/export, `accept_real_photos.py` |
| Phase 4 — Rationalization | v0.2 | Snap, equal spacing, symmetry |
| Phase 5 — Pattern reuse | v0.2 | Bay detection, shared components |
| Phase 6 — Multi-view | v0.3 | Registration, fusion, depth hooks |
| Phase 7+ — Parametric building | v0.32 | Floor/roof/stair from params (not vision) |
| Phase 3.6 — SAM refine | v0.35 | Optional mask refinement |

---

## In validation

| Item | Blocker |
|------|---------|
| Real Photo Stage A sign-off | A1 → A2 → A3 not complete |
| YOLO on real rectified facades | Needs ≥10 train labels from benchmark |
| End-to-end RQS ≥ 70 avg on hold-out | Not measured yet |

---

## Frozen (do not extend without explicit request)

- Phase 16–23: LOD tours, layout PDF, MP4 export, interior layout polish
- New AI models without evidence of RQS improvement
- New export formats, UI chrome, or parametric elements

---

## Maturity snapshot (2026-08-16)

| Layer | Score | Evidence |
|-------|-------|----------|
| Architecture | 9/10 | IR boundary, generator isolation |
| SketchUp kernel | 9/10 | Phase 0 acceptance |
| IR | 8/10 | Schema + validator |
| Workspace | 8/10 | Full manual path |
| Rectification | 7/10 | 28-photo log; 11/28 auto_full_frame |
| Detection | 6/10 | 26/28 smoke pass; 2 hard fails |
| Rationalization | 7/10 | Synthetic + manual tests |
| Multi-view | 5/10 | Code complete, no real-photo proof |
| Real-world validation | 3/10 | A1 in progress |
| Product focus | 6/10 | Pivoting to benchmark-first |

---

## Related docs

| Doc | Role |
|-----|------|
| `docs/REAL_PHOTO_ACCEPTANCE.md` | Stage A workflow + RQS rubric |
| `docs/A1_BASELINE_REPORT.md` | A1 detection baseline snapshot |
| `docs/MODEL_ARTIFACT_POLICY.md` | What stays in git vs releases |
| `docs/OBSERVATION_LAYER.md` | Perception → Understanding boundary |
| `docs/ARCHITECTURE.md` | Layer design (no progress claims) |
| `docs/RECONSTRUCTION_STATUS.md` | Technical deliverable log (defers to this file for priority) |
