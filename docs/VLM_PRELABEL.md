# VLM Pre-labeling (Cloud API)

Use a **cloud vision LLM** (OpenAI or Gemini) to pre-annotate rectified facade images for YOLO training. Human review corrects mistakes; export is compatible with `train_yolo_facade.py --custom-dataset`.

---

## Prerequisites

1. **Rectified** facade images only (after Workspace **Rectify Facade**).
2. API key in environment:

```powershell
# OpenAI (recommended default)
$env:OPENAI_API_KEY = "sk-..."

# Or Gemini
$env:GEMINI_API_KEY = "..."
```

3. Backend venv:

```powershell
cd F:\development\Geomora\backend
.\.venv\Scripts\pip install -r requirements.txt
```

---

## Quick start (OpenAI)

```powershell
cd F:\development\Geomora\backend

# Trial on 3 images
.\.venv\Scripts\python scripts\vlm_prelabel_facade.py `
  --images cache\real_photo_desktop_rectified `
  --out data\facade_yolo_vlm `
  --split train `
  --provider openai `
  --model gpt-4o-mini `
  --limit 3

# Open review HTML
start cache\vlm_prelabel_review\index.html
```

Outputs:

| Path | Content |
|------|---------|
| `data/facade_yolo_vlm/train/images/` | Copied rectified JPGs |
| `data/facade_yolo_vlm/train/labels/` | YOLO `.txt` (class 0=window, 1=door) |
| `cache/vlm_prelabel_review/` | Overlay previews + `index.html` |
| `cache/vlm_prelabel_report.json` | Machine-readable log |

---

## Gemini

```powershell
$env:GEMINI_API_KEY = "..."
.\.venv\Scripts\python scripts\vlm_prelabel_facade.py `
  --images cache\real_photo_desktop_rectified `
  --provider gemini `
  --model gemini-2.0-flash
```

---

## Recommended workflow

```text
Collect rectified facades (100+ target)
    ↓
vlm_prelabel_facade.py  (cloud API)
    ↓
Review cache/vlm_prelabel_review/index.html
    ↓
Fix bad labels in LabelImg / makesense / Workspace Overlay
    ↓
Merge into data/facade_yolo_custom/
    ↓
train_yolo_facade.py --custom-dataset data/facade_yolo_custom --epochs 80
    ↓
accept_real_photos.py --dataset ... --split val
```

**Cost control:** use `--limit` for trials; `gpt-4o-mini` is cheaper than `gpt-4o`. Images are resized to max 1600px before upload.

---

## Train YOLO on VLM dataset

```powershell
.\.venv\Scripts\python scripts\train_yolo_facade.py `
  --custom-dataset data\facade_yolo_vlm `
  --epochs 80
```

Merge with manually corrected data by copying `images/` + `labels/` into `data/facade_yolo_custom/train/`.

---

## Models

| Provider | Default model | Env var |
|----------|---------------|---------|
| `openai` | `gpt-4o-mini` | `OPENAI_API_KEY` |
| `gemini` | `gemini-2.0-flash` | `GEMINI_API_KEY` or `GOOGLE_API_KEY` |

Override with `--model`. For OpenAI-compatible proxies, use `--base-url`.

---

## Limitations

- VLM boxes are **observations**, not ground truth — always spot-check before training.
- Works best on **rectified** facades; perspective photos should be Rectify first.
- API latency and cost scale with image count; batch overnight for large sets.
- Privacy: building photos are sent to the cloud provider — use only images you may upload.

---

## Related

- `docs/YOLO_LABELING.md` — bbox rules
- `docs/YOLO_TRAINING.md` — train + export ONNX
- `docs/REAL_PHOTO_ACCEPTANCE.md` — val recall targets
