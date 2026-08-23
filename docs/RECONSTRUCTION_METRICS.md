# Reconstruction Quality Metrics v1

This is the measurement contract for Geomora Reconstruction Core v0.1.

The evaluator accepts a ground-truth JSON and a prediction JSON with the same
`photo_id`. Coordinates are facade-normalized `[x1, y1, x2, y2]`; opening IDs
remain stable across truth and prediction so topology and geometry assignments
can be compared independently from pixel matching.

## Metric groups

| Group | Measures | RQS weight |
|-------|----------|------------|
| Detection | window/door precision, recall and F1 at IoU 0.5 | 25 |
| Topology | storey/bay count and opening assignments | 25 |
| Relative geometry | normalized opening width, height and sill error | 20 |
| Metric scale | relative errors for measured dimensions only | 10 |
| Rationalization | reduction in variance/alignment error | 10 |
| SketchUp E2E | stable generation, holes, editability, validity and reuse | 10 |

RQS is normalized over available groups for diagnostic use, while `coverage`
reports how much of the 100-point contract was actually evaluated. A release
gate requires full required coverage; missing annotations cannot count as a
pass. Metric scale may be unavailable when no measured anchor exists, but an
anchored RC-G1 sample requires it (legacy reports call this A3).

## Gate policy

- train/val establish regressions and thresholds;
- hold-out is evaluation-only and never used for parameter tuning;
- a smoke result such as `window_count > 0` is diagnostic, never RC-G1 gate evidence;
- image-specific heuristics are rejected without an architectural rationale;
- aggregate scores must retain per-photo results and annotation coverage.

The executable example and annotation order are documented in
`tests/reconstruction/README.md`.
