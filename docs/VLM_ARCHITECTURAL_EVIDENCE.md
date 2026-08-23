# VLM Architectural Evidence v0.1

This layer asks a multimodal model to read facade structure, not to generate a
SketchUp model. Its output is uncertain evidence for the Observation Graph.

The contract includes building type, visible storey count, bay count,
repetition strength, opening groups, occlusion regions, and explicit
uncertainties. It deliberately excludes millimetre dimensions and final IR.

Generate and cache evidence:

```powershell
backend\.venv\Scripts\python.exe backend\scripts\run_vlm_architecture.py `
  path\to\rectified.jpg `
  --photo-id photo_01 `
  --provider openai `
  --cache backend\cache\vlm_architecture\photo_01.json `
  --observation-graph backend\cache\vlm_architecture\photo_01.graph.json
```

Use cached evidence in a reconstruction baseline without making network calls:

```powershell
backend\.venv\Scripts\python.exe backend\scripts\run_reconstruction_baseline.py `
  --vlm-cache-dir backend\cache\vlm_architecture
```

Cached evidence records provider, model, and prompt version. Changing the
prompt contract requires a new prompt version and regenerated cache. VLM output
must pass strict parsing before it enters reconstruction.

## Reconciliation policy

Architectural Understanding remains the decision boundary. CV row/column
clusters are the default geometric evidence. Matching VLM evidence increases
confidence. VLM counts override only when VLM confidence is high and geometric
support is demonstrably weak, such as a single visible opening. Other conflicts
retain the CV count and are written to `topology.uncertainties` together with
both candidates, confidences, and the selected source.
