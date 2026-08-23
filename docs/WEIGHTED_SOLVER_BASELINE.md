# Weighted Constraint Solver v0.1 — baseline note

Date: 2026-08-23  
Set: `tests/reconstruction/minimal_set.json` (5 photos)

The solver was evaluated in a temporary output directory and did not overwrite
the recorded baseline.

| Metric | Recorded baseline | Solver v0.1 |
|--------|-------------------|-------------|
| Mean window recall | 0.4967 | 0.4967 |
| Mean normalized geometry MAE | 0.18460 | 0.18463 |
| Mean RQS | 53.7 | 50.0 |

The RQS values are not directly comparable. The recorded baseline's
rationalization score used a hypothetical fully equalized row as its `after`
state even though that geometry was not passed to IR. Solver v0.1 records the
actual solved geometry. On photos with inferred constraints, mean constraint
residuals decreased substantially (for example photo_11: 0.003855 → 0.000350),
while detection recall and relative geometry remained effectively unchanged.

Conclusion: retain the solver implementation, do not promote the temporary RQS
as a new quality baseline, and treat the lower score as removal of optimistic
measurement rather than demonstrated product regression. The next comparison
must use actual solved geometry on both sides and report constraint residuals
alongside global rationalization metrics.
