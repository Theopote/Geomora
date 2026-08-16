"""Export visual review pack for real-photo acceptance (overlays + HTML + priority CSV).

Example:
  cd backend
  .venv\\Scripts\\python scripts/export_real_photo_review.py `
    --images cache\\real_photo_desktop_rectified `
    --report cache\\real_photo_acceptance_auto.json `
    --rectify-log cache\\real_photo_rectify_log.json `
    --out cache\\real_photo_review
"""

from __future__ import annotations

import argparse
import csv
import html
import json
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from geomora_detect.image_io import imread_bgr, imwrite_bgr  # noqa: E402
from geomora_detect.overlays import draw_overlay  # noqa: E402
from geomora_detect.pipeline import detect_facade  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export overlay review pack for facade acceptance")
    parser.add_argument("--images", type=Path, required=True, help="Folder of rectified images")
    parser.add_argument("--report", type=Path, help="JSON report from accept_real_photos.py")
    parser.add_argument("--rectify-log", type=Path, help="JSON rectify log")
    parser.add_argument("--method", default="auto", help="Detection method for overlays")
    parser.add_argument("--out", type=Path, default=Path("cache/real_photo_review"))
    return parser.parse_args()


def priority_tier(
    passed: bool,
    confidence: float,
    window_count: int,
    door_count: int,
    rectify_method: str | None,
) -> str:
    if not passed:
        return "P0_FAIL"
    if confidence < 0.5:
        return "P0_LOW_CONF"
    if window_count >= 8:
        return "P1_HIGH_WINDOWS"
    if rectify_method == "auto_full_frame":
        return "P1_FULL_FRAME_RECTIFY"
    if window_count == 1 and door_count == 0:
        return "P2_SINGLE_WINDOW"
    return "P2_OK"


def priority_rank(tier: str) -> int:
    order = {
        "P0_FAIL": 0,
        "P0_LOW_CONF": 1,
        "P1_HIGH_WINDOWS": 2,
        "P1_FULL_FRAME_RECTIFY": 3,
        "P2_SINGLE_WINDOW": 4,
        "P2_OK": 5,
    }
    return order.get(tier, 9)


def load_report_map(report_path: Path | None) -> dict[str, dict]:
    if not report_path or not report_path.exists():
        return {}
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    return {Path(item["image_path"]).name: item for item in payload.get("results", [])}


def load_rectify_map(log_path: Path | None) -> dict[str, dict]:
    if not log_path or not log_path.exists():
        return {}
    items = json.loads(log_path.read_text(encoding="utf-8"))
    return {item["file"]: item for item in items}


def build_rows(
    image_dir: Path,
    report_map: dict[str, dict],
    rectify_map: dict[str, dict],
    method: str,
    out_dir: Path,
) -> list[dict]:
    overlay_dir = out_dir / "overlays"
    overlay_dir.mkdir(parents=True, exist_ok=True)

    rows: list[dict] = []
    for image_path in sorted(image_dir.glob("*.jpg")):
        name = image_path.name
        report = report_map.get(name, {})
        rectify = rectify_map.get(name, {})

        if report:
            passed = bool(report.get("passed", True))
            confidence = float(report.get("confidence", 0))
            window_count = int(report.get("window_count", 0))
            door_count = int(report.get("door_count", 0))
            detect_method = str(report.get("method", method))
        else:
            result = detect_facade(str(image_path), method=method, return_overlay=False)
            windows = [e for e in result.elements if e.type == "window"]
            doors = [e for e in result.elements if e.type == "door"]
            passed = len(windows) >= 1
            confidence = result.confidence
            window_count = len(windows)
            door_count = len(doors)
            detect_method = result.method

        rectify_method = rectify.get("method")
        tier = priority_tier(passed, confidence, window_count, door_count, rectify_method)

        detect_result = detect_facade(str(image_path), method=method, return_overlay=False)
        bgr = imread_bgr(image_path)
        overlay = draw_overlay(bgr, detect_result.elements)
        overlay_rel = f"overlays/{name}"
        imwrite_bgr(out_dir / overlay_rel, overlay)

        rows.append(
            {
                "file": name,
                "tier": tier,
                "rank": priority_rank(tier),
                "passed": passed,
                "confidence": round(confidence, 4),
                "windows": window_count,
                "doors": door_count,
                "detect_method": detect_method,
                "rectify_method": rectify_method or "",
                "rectify_confidence": rectify.get("confidence", ""),
                "overlay": overlay_rel,
                "sketchup_action": sketchup_action(tier, window_count, door_count),
            }
        )

    rows.sort(key=lambda row: (row["rank"], row["confidence"], row["file"]))
    return rows


def sketchup_action(tier: str, windows: int, doors: int) -> str:
    if tier == "P0_FAIL":
        return "手拖四角 Rectify + Overlay 手画窗/删误检门"
    if tier == "P0_LOW_CONF":
        return "Overlay 核对每框 + Export train"
    if tier == "P1_HIGH_WINDOWS":
        return "核对是否误检过多 + Delete 多余框"
    if tier == "P1_FULL_FRAME_RECTIFY":
        return "重拖四角 Rectify 后再 Detect"
    if tier == "P2_SINGLE_WINDOW":
        return "确认是否漏检其他窗"
    return "快速目视 → Generate"


def write_csv(rows: list[dict], path: Path) -> None:
    fields = [
        "tier",
        "file",
        "passed",
        "confidence",
        "windows",
        "doors",
        "detect_method",
        "rectify_method",
        "sketchup_action",
        "overlay",
    ]
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row[key] for key in fields})


def write_html(rows: list[dict], path: Path, method: str, image_count: int) -> None:
    tier_labels = {
        "P0_FAIL": "P0 · 失败",
        "P0_LOW_CONF": "P0 · 低置信",
        "P1_HIGH_WINDOWS": "P1 · 窗数偏多",
        "P1_FULL_FRAME_RECTIFY": "P1 · 整图 Rectify",
        "P2_SINGLE_WINDOW": "P2 · 仅 1 窗",
        "P2_OK": "P2 · 正常",
    }

    cards = []
    for row in rows:
        tier_label = tier_labels.get(row["tier"], row["tier"])
        status = "PASS" if row["passed"] else "FAIL"
        cards.append(
            f"""
            <article class="card tier-{html.escape(row['tier'])}">
              <header>
                <span class="tier">{html.escape(tier_label)}</span>
                <span class="status">{status}</span>
              </header>
              <h2>{html.escape(row['file'])}</h2>
              <img src="{html.escape(row['overlay'])}" alt="{html.escape(row['file'])}"/>
              <dl>
                <dt>检测</dt><dd>{row['windows']} 窗 / {row['doors']} 门 · {html.escape(row['detect_method'])} · conf {row['confidence']}</dd>
                <dt>Rectify</dt><dd>{html.escape(str(row['rectify_method']))} ({row['rectify_confidence']})</dd>
                <dt>SketchUp</dt><dd>{html.escape(row['sketchup_action'])}</dd>
              </dl>
            </article>
            """
        )

    document = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8"/>
  <title>Geomora 真实照片验收 · {image_count} 张</title>
  <style>
    body {{ font-family: "Segoe UI", sans-serif; margin: 24px; background: #f4f6f8; color: #1a1a1a; }}
    h1 {{ margin-bottom: 8px; }}
    .meta {{ color: #555; margin-bottom: 24px; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(360px, 1fr)); gap: 16px; }}
    .card {{ background: #fff; border-radius: 10px; padding: 12px; box-shadow: 0 1px 4px rgba(0,0,0,.08); }}
    .card img {{ width: 100%; border-radius: 6px; background: #ddd; }}
    .card header {{ display: flex; gap: 8px; margin-bottom: 8px; }}
    .tier {{ font-size: 12px; font-weight: 600; padding: 2px 8px; border-radius: 999px; background: #e8eef7; }}
    .status {{ font-size: 12px; font-weight: 600; }}
    .tier-P0_FAIL .tier, .tier-P0_LOW_CONF .tier {{ background: #fde8e8; color: #b42318; }}
    .tier-P1_HIGH_WINDOWS .tier, .tier-P1_FULL_FRAME_RECTIFY .tier {{ background: #fff4e5; color: #b54708; }}
    dl {{ margin: 8px 0 0; font-size: 13px; }}
    dt {{ font-weight: 600; margin-top: 6px; }}
    dd {{ margin: 2px 0 0; color: #444; }}
  </style>
</head>
<body>
  <h1>真实立面照片验收预览</h1>
  <p class="meta">方法: {html.escape(method)} · 共 {image_count} 张 · 按优先级排序（P0 最先验收）</p>
  <div class="grid">
    {''.join(cards)}
  </div>
</body>
</html>
"""
    path.write_text(document, encoding="utf-8")


def main() -> None:
    args = parse_args()
    image_dir = args.images.resolve()
    if not image_dir.exists():
        raise SystemExit(f"Image folder not found: {image_dir}")

    out_dir = args.out.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    report_map = load_report_map(args.report)
    rectify_map = load_rectify_map(args.rectify_log)

    rows = build_rows(image_dir, report_map, rectify_map, args.method, out_dir)
    write_csv(rows, out_dir / "acceptance_priority.csv")
    write_html(rows, out_dir / "index.html", args.method, len(rows))

    summary = {
        "total": len(rows),
        "by_tier": {},
    }
    for row in rows:
        summary["by_tier"][row["tier"]] = summary["by_tier"].get(row["tier"], 0) + 1
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    print(f"Review pack: {out_dir}")
    print(f"  HTML: {out_dir / 'index.html'}")
    print(f"  CSV:  {out_dir / 'acceptance_priority.csv'}")
    print(f"  Tier counts: {summary['by_tier']}")
    print("P0 first (open index.html in browser):")
    for row in rows[:8]:
        print(f"  [{row['tier']}] {row['file']} — {row['sketchup_action']}")


if __name__ == "__main__":
    main()
