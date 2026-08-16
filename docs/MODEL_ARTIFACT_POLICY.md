# Model Artifact Policy

Large binaries and training outputs must not bloat the git repository. This policy applies immediately — before the real-photo benchmark generates more `.pt`, `.onnx`, datasets, and cache.

---

## In git (keep)

| Path | Purpose |
|------|---------|
| `backend/scripts/download_*.py` | Fetch models on demand |
| `backend/models/manifest.json` | Model name, version, SHA, download URL |
| `schemas/` | IR and config schemas |
| `examples/` | Tiny synthetic fixtures only |
| `examples/real_photos/benchmark/manifest.json` | Benchmark **metadata** (not raw photos) |
| Config / training hyperparams | `train_yolo_facade.py` defaults, dataset YAML templates |

---

## Not in git (ignore or local only)

| Path | Reason |
|------|--------|
| `backend/yolov8n.pt` | Ultralytics base weights (~6.5 MB); download via train script |
| `backend/models/*.onnx` | Exported inference models |
| `backend/models/*.onnx_data` | External weight blobs |
| `backend/models/*.pt` | PyTorch checkpoints |
| `backend/runs/` | YOLO training runs |
| `backend/data/` | Labeled datasets (real photos) |
| `backend/cache/` | Rectified images, acceptance reports, review HTML |
| `examples/real_photos/perspective/` | User's original photos |
| `examples/real_photos/rectified/` | Local rectified copies (except synthetic fixture) |
| Raw video files | Use local paths only |

`.gitignore` enforces the above. CI and new clones run download scripts instead of committing weights.

---

## Distribution

| Artifact | Channel |
|----------|---------|
| Production ONNX (`facade_yolo_v1.onnx`) | GitHub Release asset or `download_*.py` |
| MobileSAM ONNX | `scripts/download_mobile_sam_onnx.py` |
| Depth models | `scripts/download_depth_models.py` |
| Trained custom YOLO | Release per benchmark milestone; manifest entry required |

---

## Benchmark photos

Real building photos are **local-only** unless the team explicitly approves de-identified samples.

- Store originals under `examples/real_photos/perspective/` (gitignored)
- Rectified copies under `backend/cache/` or local benchmark folder
- Commit only `manifest.json` with hashed filenames and split assignments

---

## Adding a new model (checklist)

Before merging any new model into the default pipeline, answer:

1. Which **RQS dimension** does it improve? (see `REAL_PHOTO_ACCEPTANCE.md` §3)
2. What is the latency cost on a typical 2 MP facade photo?
3. Does hold-out RQS improve by ≥5 points vs baseline?
4. Is there a download script + manifest entry?
5. Is the default path still usable without the model (graceful fallback)?

If any answer is "unknown", the model stays **opt-in** until A2 evidence exists.
