"""Pre-label rectified facade images with a cloud vision LLM (OpenAI / Gemini).

Examples:
  cd backend
  set OPENAI_API_KEY=sk-...
  .venv\\Scripts\\python scripts/vlm_prelabel_facade.py ^
    --images cache\\real_photo_desktop_rectified ^
    --out data\\facade_yolo_vlm ^
    --split train ^
    --provider openai ^
    --model gpt-4o-mini

  set GEMINI_API_KEY=...
  .venv\\Scripts\\python scripts/vlm_prelabel_facade.py --images ... --provider gemini
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from geomora_detect.acceptance_metrics import discover_images  # noqa: E402
from geomora_detect.vlm_prelabel import (  # noqa: E402
    build_client,
    default_model,
    write_review_overlay,
    write_yolo_label,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Cloud VLM pre-labeling for facade YOLO dataset")
    parser.add_argument("--images", type=Path, required=True, help="Folder of rectified facade images")
    parser.add_argument("--out", type=Path, default=Path("data/facade_yolo_vlm"), help="Dataset root")
    parser.add_argument("--split", choices=("train", "val"), default="train")
    parser.add_argument("--provider", choices=("openai", "gemini"), default="openai")
    parser.add_argument("--model", default=None, help="Model name (default: gpt-4o-mini or gemini-2.0-flash)")
    parser.add_argument("--api-key", default=None, help="API key override (else use env var)")
    parser.add_argument("--base-url", default=None, help="OpenAI-compatible base URL override")
    parser.add_argument("--limit", type=int, default=None, help="Process only first N images")
    parser.add_argument("--dry-run", action="store_true", help="Call API but do not write dataset files")
    parser.add_argument("--report", type=Path, default=Path("cache/vlm_prelabel_report.json"))
    parser.add_argument("--review-dir", type=Path, default=Path("cache/vlm_prelabel_review"))
    return parser.parse_args()


def write_review_html(results: list[dict], path: Path) -> None:
    cards = []
    for item in results:
        name = Path(item["image_path"]).name
        status = "ERROR" if item.get("error") else "OK"
        overlay = item.get("overlay")
        cards.append(
            f"""
            <article>
              <h3>{name} <small>{status}</small></h3>
              <p>{item.get('windows', 0)} windows, {item.get('doors', 0)} doors
                 | {item.get('provider')} / {item.get('model')}</p>
              <p>{item.get('notes', '')}</p>
              {'<img src="' + overlay + '" alt="' + name + '"/>' if overlay else ''}
              <pre>{item.get('error', '')}</pre>
            </article>
            """
        )
    html = f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8"/><title>VLM Prelabel Review</title>
<style>
body {{ font-family: Segoe UI, sans-serif; margin: 24px; }}
article {{ border: 1px solid #ddd; border-radius: 8px; padding: 12px; margin-bottom: 16px; }}
img {{ max-width: 100%; }}
pre {{ color: #b42318; white-space: pre-wrap; }}
</style></head><body>
<h1>VLM Prelabel Review</h1>
{''.join(cards)}
</body></html>"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding="utf-8")


def main() -> None:
    args = parse_args()
    image_dir = args.images.resolve()
    if not image_dir.exists():
        raise SystemExit(f"Image folder not found: {image_dir}")

    model = args.model or default_model(args.provider)
    client = build_client(args.provider, args.api_key, base_url=args.base_url)

    images = discover_images(image_dir)
    if args.limit is not None:
        images = images[: args.limit]
    if not images:
        raise SystemExit("No images found.")

    split_images = args.out / args.split / "images"
    split_labels = args.out / args.split / "labels"
    review_dir = args.review_dir.resolve()
    review_dir.mkdir(parents=True, exist_ok=True)

    results: list[dict] = []
    ok_count = 0

    for index, image_path in enumerate(images, start=1):
        print(f"[{index}/{len(images)}] {image_path.name} ...", flush=True)
        result = client.detect_openings(image_path, model=model)
        overlay_rel = None

        record = {
            "image_path": str(image_path),
            "provider": result.provider,
            "model": result.model,
            "windows": result.window_count,
            "doors": result.door_count,
            "notes": result.notes,
            "error": result.error,
            "elements": [
                {
                    "type": element.type,
                    "bbox_norm": element.bbox_norm,
                    "confidence": element.confidence,
                }
                for element in result.elements
            ],
        }

        if result.error:
            print(f"  ERROR: {result.error}")
            results.append(record)
            continue

        print(f"  OK: {result.window_count} windows, {result.door_count} doors")
        ok_count += 1

        if not args.dry_run:
            split_images.mkdir(parents=True, exist_ok=True)
            split_labels.mkdir(parents=True, exist_ok=True)
            target_image = split_images / image_path.name
            shutil.copy2(image_path, target_image)
            write_yolo_label(split_labels / f"{image_path.stem}.txt", result.elements)

        overlay_path = review_dir / f"{image_path.stem}_vlm.jpg"
        write_review_overlay(image_path, result.elements, overlay_path)
        overlay_rel = overlay_path.name
        record["overlay"] = overlay_rel
        results.append(record)

    args.report.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "provider": args.provider,
        "model": model,
        "split": args.split,
        "dataset_root": str(args.out.resolve()),
        "processed": len(images),
        "ok": ok_count,
        "results": results,
    }
    args.report.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    write_review_html(results, review_dir / "index.html")

    print()
    print(f"Processed: {len(images)} | OK: {ok_count} | Errors: {len(images) - ok_count}")
    print(f"Report: {args.report.resolve()}")
    if not args.dry_run:
        print(f"Dataset: {args.out.resolve()} ({args.split})")
    print(f"Review:  {review_dir / 'index.html'}")


if __name__ == "__main__":
    main()
