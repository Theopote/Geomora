"""Export GT review HTML pack with editable bbox overlays.

Example:
  cd backend
  .venv\\Scripts\\python scripts/export_gt_review_pack.py
  start ..\\tests\\reconstruction\\review_pack\\index.html
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
sys.path.insert(0, str(BACKEND_ROOT))

MINIMAL_SET = REPO_ROOT / "tests" / "reconstruction" / "minimal_set.json"
GT_DIR = REPO_ROOT / "tests" / "reconstruction" / "ground_truth"
PACK_DIR = REPO_ROOT / "tests" / "reconstruction" / "review_pack"
ASSETS_DIR = PACK_DIR / "assets"
TEMPLATE = ASSETS_DIR / "index.template.html"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--minimal-set", type=Path, default=MINIMAL_SET)
    parser.add_argument("--ground-truth-dir", type=Path, default=GT_DIR)
    parser.add_argument("--out", type=Path, default=PACK_DIR)
    return parser.parse_args()


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def entry_by_id(manifest: dict, photo_id: str) -> dict:
    for entry in manifest["images"]:
        if entry["id"] == photo_id:
            return entry
    raise KeyError(photo_id)


def build_pack(minimal: dict, gt_dir: Path, out_dir: Path) -> dict:
    manifest = load_json(REPO_ROOT / minimal["manifest"])
    image_root = REPO_ROOT / manifest["image_root"]
    images_dir = out_dir / "images"
    exports_dir = out_dir / "exports"
    images_dir.mkdir(parents=True, exist_ok=True)
    exports_dir.mkdir(parents=True, exist_ok=True)

    photos = []
    for item in minimal["photos"]:
        photo_id = item["id"]
        gt_path = gt_dir / f"{photo_id}.json"
        if not gt_path.exists():
            raise FileNotFoundError(f"Missing ground truth: {gt_path}")
        entry = entry_by_id(manifest, photo_id)
        source_image = image_root / entry["file"]
        if not source_image.exists():
            raise FileNotFoundError(f"Missing image: {source_image}")

        dest_name = f"{photo_id}{source_image.suffix.lower()}"
        dest_image = images_dir / dest_name
        shutil.copy2(source_image, dest_image)

        photos.append(
            {
                "id": photo_id,
                "split": item.get("split", entry.get("split", "")),
                "category": item.get("category", entry.get("category", "")),
                "image_rel": f"images/{dest_name}",
                "ground_truth": load_json(gt_path),
            }
        )

    return {
        "version": "gt-review-pack-v1",
        "minimal_set": minimal.get("version", "minimal-v1"),
        "metric_anchor_required": minimal.get("metric_anchor_required", []),
        "photos": photos,
    }


def write_index(out_dir: Path, pack: dict) -> None:
    template = TEMPLATE.read_text(encoding="utf-8")
    pack_json = json.dumps(pack, ensure_ascii=False)
    html = template.replace("__PACK_JSON__", pack_json)
    (out_dir / "index.html").write_text(html, encoding="utf-8")


def main() -> int:
    args = parse_args()
    minimal = load_json(args.minimal_set)
    pack = build_pack(minimal, args.ground_truth_dir, args.out)
    write_index(args.out, pack)

    index_path = args.out / "index.html"
    print(f"GT review pack -> {index_path.resolve()}")
    print(f"  photos: {len(pack['photos'])}")
    print(f"  images: {args.out / 'images'}")
    print(f"  exports: {args.out / 'exports'} (save downloaded JSON here)")
    print("")
    print("Open index.html in a browser, edit boxes, Export All, then:")
    print("  .venv\\Scripts\\python scripts/import_gt_review_pack.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
