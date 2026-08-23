# Reconstruction Metrics v1 fixtures

`ground_truth/` contains human-authored architectural truth. `predictions/`
contains pipeline output in the same normalized facade coordinate system.
`minimal_set.json` defines the five-photo objective test set for Reconstruction
Core v0.1.

## Minimal 5-photo set

| ID | Role | Split |
|----|------|-------|
| photo_01 | regular residential | train |
| photo_11 | commercial / office | val |
| photo_16 | strong perspective | holdout |
| photo_18 | tree / street occlusion | holdout |
| photo_19 | irregular old commercial | holdout |

Ground truth files are `draft_v1` and require a second human review before
gate use. `metric_anchors` with `status: pending_survey` are placeholders —
never infer millimetre truth from door-height priors.

## GT review pack (editable bbox)

Export the HTML annotator:

```powershell
cd backend
.venv\Scripts\python scripts\export_gt_review_pack.py
start ..\tests\reconstruction\review_pack\index.html
```

Workflow:

1. Open `tests/reconstruction/review_pack/index.html` in a browser.
2. Drag boxes / draw new window or door boxes / edit storey & bay in the panel.
3. For photo_11 and photo_19, enter surveyed `distance_mm` on metric anchors.
4. Click **Export All** and save JSON files to `review_pack/exports/`.
5. Import back into ground truth:

```powershell
.venv\Scripts\python scripts\import_gt_review_pack.py
```

Imported files get `annotation_status: reviewed_v1` and `review_rounds` incremented.

## Annotation order

1. opening bounding boxes and stable IDs;
2. storey/bay counts and each opening's assignment;
3. facade bbox and pattern groups;
4. metric dimensions only when a measured anchor exists;
5. SketchUp checks produced by the E2E review/export step.

## Commands

Run current pipeline baseline (Step 2):

```powershell
cd backend
.venv\Scripts\python scripts\run_reconstruction_baseline.py
```

Batch metrics + aggregate report:

```powershell
.venv\Scripts\python scripts\run_reconstruction_metrics_batch.py
```

`prediction.json` now includes inferred `topology` (`cluster_v0.1`) and per-opening
`geometry` ratios (`bbox_ratios_v0.1`). Topology and geometry metrics match
detections to GT by IoU, not by opening id.

## Reconstruction decision audit

Solver safety and exceptional human confirmations are operational audit data,
not subjective quality scores. Summarize exported Architectural IR files with:

```powershell
.venv\Scripts\python scripts\summarize_reconstruction_audit.py <ir-file-or-directory>
```

The report exposes individual train/validation events. Holdout events are
sealed into a count-only `gate_only_not_for_tuning` block so their decisions
cannot be used to tune solver weights or reconstruction rules.

Single pair:

```powershell
.venv\Scripts\python scripts\run_reconstruction_metrics.py `
  tests/reconstruction/ground_truth/photo_01.json `
  tests/reconstruction/baselines/current/photo_01/prediction.json
```

## Coverage policy

The output includes `coverage` and `not_evaluated`. An RQS without full
coverage must never be used to pass A2/A3. Missing topology, metric anchors, or
SketchUp checks remain `not_evaluated` — they do not auto-pass.
