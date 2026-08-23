# Geomora Roadmap

**This file is the single source of truth for current priorities, subsystem
maturity, and release gates.** Phase documents describe design history; they do
not declare current progress.

**Updated:** 2026-08-24

---

## How progress is represented

Reconstruction Core is being developed as parallel subsystems. Subsystem IDs do
not prescribe implementation order.

| Maturity | Meaning |
|----------|---------|
| **Experimental** | Vertical slice exists, but interfaces may change and benchmark gain is unproven. |
| **Prototype** | In the production path with tests and safe fallback, but real-photo validation is incomplete. |
| **Validated** | Reviewed GT and benchmark evidence meet the subsystem exit criteria without material regression. |
| **Stable** | Interface is versioned/frozen, expanded real-photo validation passes, and compatibility is maintained. |

Writing code does not advance a subsystem to Validated. Gates are policies over
multiple subsystems, not development phases.

---

## Reconstruction Core v0.1 snapshot

| ID | Subsystem | Maturity | Current evidence | Next exit work |
|----|-----------|----------|------------------|----------------|
| **RC-M** | Metrics & Ground Truth | **Prototype** | Metrics v1, five-photo GT, GT validator, RC-G1 evaluator | Complete two-person GT review and record reproducible baseline |
| **RC-O** | Observation Graph | **Prototype** | CV, structural, depth and VLM adapters feed a shared graph | Validate provenance/fusion on reviewed real photos |
| **RC-U** | Architectural Understanding | **Prototype** | Storey, bay, opening and pattern hypotheses run in production | Measure topology accuracy beyond regular window arrays |
| **RC-S** | Metric Scale & Anchors | **Experimental** | Typed anchors and scale derivation exist | Validate multi-anchor consistency and anchored scale error |
| **RC-C** | Constraint Solver | **Prototype** | Weighted hard/soft solver, fixed dimensions, residuals and safety fallback run in production | Prove non-negative geometry gain through ablation |
| **RC-A** | AI/VLM Evidence | **Experimental** | OpenAI, Gemini and OpenAI-compatible evidence can enter the graph | Record CV-only vs VLM paired benchmark; do not add providers first |
| **RC-I** | Architectural IR Integration | **Prototype** | Understanding, metric and solver audit export to editable IR | Freeze v0.1 reconstruction schema after gate evidence |
| **RC-E** | SketchUp E2E Generation | **Prototype** | `POST /reconstruct` feeds Workspace and editable generation | Pass reviewed real-photo topology, scale and editability checks |

Current status is intentionally parallel: RC-C may be Prototype while RC-G1 is
not passed. This is not a sequencing contradiction.

---

## Current validation gate

### RC-G1 — Reconstruction Core v0.1 Validation Gate (not passed, P0)

RC-G1 was historically called **A3 Reconstruction Baseline Gate**. The legacy
name remains accepted in scripts and archived reports, but new planning text
must use RC-G1.

| Dependency | Exit evidence |
|------------|---------------|
| RC-M | Five-photo GT reviewed twice, validator clean or warnings adjudicated, baseline archived |
| RC-O | Observation source/provenance present for every evaluated prediction |
| RC-U | Topology thresholds reported for storeys, bays and openings |
| RC-S | Metric scores reported only for genuinely anchored samples |
| RC-C | Solver ablation recorded; hard constraints satisfied or the run fails visibly |
| RC-A | CV-only/VLM paired result recorded using frozen evidence, not live benchmark calls |
| RC-I | IR validator and reconstruction audit pass |
| RC-E | Hold-out ≥4/5 produces editable SketchUp geometry after bounded review |

A subsystem may continue prototype work before RC-G1. It may not be described
as Validated merely because it is connected to the production pipeline.

---

## P0 work queue

This is a dependency-aware queue, not a phase sequence.

1. **RC-M:** finish GT audit and freeze the minimal baseline inputs.
2. **RC-M/RC-E:** record the current full Reconstruction Metrics baseline.
3. **RC-S:** verify typed Metric Anchor mathematics and multi-anchor residuals.
4. **RC-C:** run solver on/off ablation; fix hard-constraint failures before adding constraint types.
5. **RC-A/RC-U:** run frozen CV-only vs CV+VLM topology ablation.
6. **RC-G1:** evaluate the gate and publish failed criteria without threshold tuning to individual photos.

No heuristic may be added solely to make one benchmark photo pass. Every
heuristic needs an architectural rationale and train/validation regression
evidence. Hold-out photos must not influence thresholds or parameters.

---

## Historical benchmark work

| Legacy ID | Result | Status |
|-----------|--------|--------|
| **A1** | 20-photo real-photo baseline and failure taxonomy | **Completed** |
| **A2** | Failure-driven detector/rectification improvement; smoke hold-out 5/5 | **Completed (diagnostic, not RC-G1 evidence)** |

Detection smoke success such as `window_count > 0` must not be used to pass
RC-G1. The objective Reconstruction Metrics contract remains authoritative.

---

## Legacy ID mapping

These aliases exist only to interpret old commits, scripts, and reports.

| Legacy ID | Canonical owner now |
|-----------|---------------------|
| R0 — Reconstruction Metrics | RC-M |
| R1 — Observation Graph | RC-O |
| R2 — Architectural Understanding | RC-U |
| R3 — Metric Anchors / Scale | RC-S |
| R4 / B0 — Constraint Graph Solver | RC-C |
| R5 — VLM semantic evidence | RC-A |
| A3 — Reconstruction Baseline Gate | RC-G1 |
| B1 — Multi-view production path | RC-O + RC-S future validation |
| B2 — Evidence-driven model selection | RC-A benchmark policy |

Do not assign new work to R0–R7, A3, or B0. Checklist row numbers must use a
document-specific prefix such as `RP-1`, never an `R` milestone ID.

---

## Secondary backlog

| Priority | Work |
|----------|------|
| P1 | Multi-view/depth real-photo validation under RC-O and RC-S |
| P1 | Evidence-driven local model inclusion only when an ablation shows gain |
| P2 | Richer architecture: balconies, slabs, cornices, split levels and occlusion reasoning |
| P2 | Video source metadata and key-frame evidence provenance |

---

## Frozen without explicit request

- Phase 16–23 presentation expansion: LOD tours, layout PDF and MP4 export
- New AI providers or models without evidence of Reconstruction Metrics gain
- New constraint types before RC-C fixed dimensions and solver ablation pass
- New export formats, UI chrome, or parametric elements unrelated to RC-G1

---

## Related documents

| Document | Role |
|----------|------|
| `docs/RECONSTRUCTION_METRICS.md` | Objective measurement contract |
| `docs/REAL_PHOTO_ACCEPTANCE.md` | Real-photo workflow and RC-G1 E2E checklist |
| `docs/OBSERVATION_LAYER.md` | RC-O evidence boundary design |
| `docs/RECONSTRUCTION_STATUS.md` | Technical delivery log; defers here for priorities/maturity |
| `docs/ARCHITECTURE.md` | Layer architecture, not progress claims |
| `docs/MODEL_ARTIFACT_POLICY.md` | Model inclusion and distribution policy |
