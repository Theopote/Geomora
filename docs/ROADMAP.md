# Geomora Roadmap

**This file is the single source of truth for project milestones and priorities.**

Phase design docs (`docs/PHASE_*.md`) explain *what* each layer does. They do **not** declare global progress — only this file does.

**Updated:** v0.36.0 · 2026-08-16

---

## Current milestone

### R0 — Reconstruction Metrics (in progress, P0)

**Goal:** Measure whether Photo → SketchUp reconstruction improves, rather than
whether a detector returns at least one window.

Reconstruction Metrics v1 evaluates six evidence groups: detection, topology,
relative geometry, metric scale (only with measured ground truth),
rationalization, and SketchUp E2E quality. Results must report annotation
`coverage`; a partial RQS cannot pass a gate.

Implementation: `backend/geomora_reconstruct/metrics/`
Minimal 5-photo GT: `tests/reconstruction/minimal_set.json`
Baseline exporter: `backend/scripts/run_reconstruction_baseline.py`

**R0 exit (phased):** 5-photo minimal set reviewed twice + baseline recorded;
then expand to 20 A1 photos. Metric scores only where a real scale anchor exists.

### R1 — Observation Graph + VLM Evidence v0.1 (in progress)

**Goal:** Perception outputs become evidence, not architectural facts.

Implementation: `backend/geomora_reconstruct/observations/` and
`backend/geomora_reconstruct/vlm_evidence.py`. YOLO, facade-row, and cached VLM
architectural evidence now share the Observation Graph. Architectural
Understanding v0.2 now reconciles CV counts with VLM evidence conservatively:
agreement increases confidence, high-confidence VLM may supplement weak/sparse
geometry, and unresolved conflicts remain explicit instead of becoming IR.

### R4 — Pattern/Constraint Evidence v0.1 (in progress)

Measured row/column repetition now produces IR-compatible soft constraint
proposals with targets, confidence, weight, source, and evidence. VLM can raise
confidence for a geometrically identified group but cannot create target
entities. The next step is a Python weighted solver with hard user anchors and
soft architectural constraints.

### A2 — Failure-driven Improvement (completed)

Detection smoke hold-out **5/5** via `auto_fusion_v1`. No further threshold
tuning until R0 baseline analysis identifies layer-specific failures.

| Priority | Failure class | A2 fix |
|----------|---------------|--------|
| P0 | `missed_window` (20/20) | YOLO + facade_row fusion (`auto_fusion_v1`) |
| P1 | `wrong_scale` (14/20) | Span extrapolation from facade bounds + window count |
| P2 | `false_door` / `missed_door` (15/20) | Door geometry + confidence filter |

### A1 — Real Photo Benchmark (completed)

**Goal:** Establish an honest baseline before any further feature work.

| Item | Target | Status |
|------|--------|--------|
| 20 real building photos curated | 5 res / 3 office / 3 old / 3 commercial / 2 occluded / 2 perspective / 2 low-light | ✅ manifest 20 |
| Split: train / val / hold-out | 10 / 5 / 5 (hold-out never in training) | ✅ |
| Run full Photo → SketchUp workflow | All 20 | ✅ 20/20 reviewed |
| Export checklist pack | `cache/benchmark_a1/index.html` | ✅ |
| Record failures (no code fixes yet) | `cache/benchmark_a1_e2e.json` | ✅ RQS avg 69.3 |
| Detection CLI baseline | 18/20 smoke pass (hold-out 3/5) | ✅ see `docs/A1_BASELINE_REPORT.md` |

**Exit:** ✅ Failure taxonomy populated; RQS scores recorded; hold-out untouched for training.

---

## Milestone queue

| ID | Name | Gate | Status |
|----|------|------|--------|
| **A1** | Real Photo Benchmark | 20 photos, baseline recorded | **Completed** |
| **A2** | Failure-driven Improvement | Detection smoke hold-out 5/5 | **Completed** |
| **R0** | Reconstruction Metrics + Minimal GT | 5-photo objective ruler + baseline | **In progress** |
| **R1** | Observation Graph → Understanding | Evidence layer before IR | **In progress** |
| **A3** | Reconstruction Baseline Gate | E2E Photo → SketchUp topology, relative geometry, anchored scale, and editable valid geometry | Frozen until R0+R1 |
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
| Phase 4 — Rationalization bootstrap | v0.2 | Snap + equal-spacing heuristic (not full Constraint Graph) |
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

## Reconstruction Core sequence

| Order | Milestone | Priority |
|-------|-----------|----------|
| 1 | R0 — Reconstruction Metrics | P0 |
| 2 | A2-final — documented failure fixes, no image-specific heuristics | P0 |
| 3 | A3 — E2E Reconstruction Baseline Gate | P0 |
| 4 | R1 — Observation Graph | P0 |
| 5 | R2 — Architectural Understanding (storeys, bays, grouping, patterns) | P0 core |
| 6 | R3 — Metric Anchors + Scale Solver | P0 core |
| 7 | R4 — Constraint Graph | P0 core |
| 8 | R5 — VLM semantic evidence | P1 |
| 9 | R6 — Multi-view / Video | P1 |
| 10 | R7 — richer architecture | P2 |

No heuristic may be added solely to make an individual benchmark photo pass.
Every heuristic requires an architectural rationale and train/val regression
evidence. Hold-out photos must not influence thresholds or parameters.

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
