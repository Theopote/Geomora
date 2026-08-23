# Reconstruction Metrics v1 fixtures

`ground_truth/` contains human-authored architectural truth. `predictions/`
contains pipeline output in the same normalized facade coordinate system.

The checked-in `example_facade` pair is a schema and regression fixture, not one
of the A1 benchmark photos. The A1 photos must be annotated from the source
images; notes and old subjective RQS fields are not sufficient ground truth.

Required annotation order:

1. opening bounding boxes and stable IDs;
2. storey/bay counts and each opening's assignment;
3. facade-relative geometry;
4. metric dimensions only when a measured anchor exists;
5. SketchUp checks produced by the E2E review/export step.

Run one pair with:

```powershell
python backend/scripts/run_reconstruction_metrics.py `
  tests/reconstruction/ground_truth/example_facade.json `
  tests/reconstruction/predictions/example_facade.json
```

The output includes `coverage` and `not_evaluated`. An RQS without full coverage
must never be used to pass A2/A3.

