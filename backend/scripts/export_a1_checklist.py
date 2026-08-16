"""Export A1 SketchUp acceptance checklist (overlays + HTML + CSV template).

Reads benchmark_a1_e2e.json and produces a printable review pack ordered by priority.

Example:
  cd backend
  .venv\\Scripts\\python scripts/export_a1_checklist.py
  .venv\\Scripts\\python scripts/import_a1_e2e_scores.py --csv cache/benchmark_a1/checklist_scores.csv
"""

from __future__ import annotations

import argparse
import csv
import html
import json
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
sys.path.insert(0, str(BACKEND_ROOT))

from geomora_detect.image_io import imread_bgr, imwrite_bgr  # noqa: E402
from geomora_detect.overlays import draw_overlay  # noqa: E402
from geomora_detect.pipeline import detect_facade  # noqa: E402

E2E_DEFAULT = BACKEND_ROOT / "cache" / "benchmark_a1_e2e.json"
OUT_DEFAULT = BACKEND_ROOT / "cache" / "benchmark_a1"

RQS_LABELS = {
    "perspective_rectification": ("Perspective Rectification", 15),
    "opening_detection": ("Opening Detection", 20),
    "opening_placement": ("Opening Placement", 15),
    "scale": ("Scale", 10),
    "pattern_rationalization": ("Pattern Rationalization", 10),
    "geometry_validity": ("Geometry Validity", 15),
    "sketchup_editability": ("SketchUp Editability", 10),
    "human_correction_cost": ("Human Correction Cost", 5),
}

SPLIT_ORDER = {"holdout": 0, "val": 1, "train": 2}
HINT_RANK = {
    "missed_window": 0,
    "false_door": 1,
    "false_window": 2,
    "opening_detection": 3,
    "bad_rectify": 4,
    "none": 9,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export A1 SketchUp acceptance checklist")
    parser.add_argument("--e2e", type=Path, default=E2E_DEFAULT)
    parser.add_argument("--out", type=Path, default=OUT_DEFAULT)
    parser.add_argument("--method", default="auto", help="Detection method for overlay regeneration")
    return parser.parse_args()


def priority_key(row: dict) -> tuple:
    hints = row.get("automated_failure_hints") or ["none"]
    worst_hint = min(hints, key=lambda h: HINT_RANK.get(h, 8))
    detect = row.get("detection", {})
    return (
        SPLIT_ORDER.get(row.get("split", ""), 9),
        HINT_RANK.get(worst_hint, 8),
        0 if detect.get("passed_smoke") else -1,
        float(detect.get("confidence", 1)),
        row.get("id", ""),
    )


def sketchup_action(row: dict) -> str:
    hints = set(row.get("automated_failure_hints") or [])
    split = row.get("split", "")
    detect = row.get("detection", {})
    rectify = row.get("rectify", {})

    if "missed_window" in hints and detect.get("door_count", 0) > 0:
        return "删误检门 + Draw window 补漏检"
    if "missed_window" in hints:
        return "Overlay Draw window 补漏检"
    if "false_window" in hints:
        return "Delete 多余窗框，核对真实窗数"
    if "false_door" in hints:
        return "Delete 误检门，door width=0"
    if "bad_rectify" in hints or rectify.get("method") == "auto_full_frame":
        return "手拖四角 Rectify 后再 Detect"
    if "opening_detection" in hints:
        return "核对每框 + Export train（仅 train split）"
    if split == "holdout":
        return "完整 E2E → 记录 RQS（禁止 Export train）"
    if split == "val":
        return "完整 E2E → 记录 RQS"
    return "快速目视 → Rationalize → Generate → Export train"


def write_overlay(image_path: Path, method: str, overlay_dir: Path) -> str:
    overlay_dir.mkdir(parents=True, exist_ok=True)
    result = detect_facade(str(image_path), method=method, return_overlay=False)
    bgr = imread_bgr(image_path)
    overlay = draw_overlay(bgr, result.elements)
    rel = f"overlays/{image_path.name}"
    imwrite_bgr(overlay_dir / image_path.name, overlay)
    return rel


def csv_fields(rqs_rubric: dict) -> list[str]:
    base = [
        "id",
        "split",
        "category",
        "file",
        "sketchup_reviewed",
        "rectify_ok",
        "windows_detected",
        "windows_true",
        "doors_detected",
        "doors_true",
        "overlay_correction",
        "generate_ok",
        "correction_time_sec",
        "failure_classes",
        "rqs_total",
        "notes",
    ]
    base.extend(f"rqs_{key}" for key in rqs_rubric)
    return base


def row_to_csv(row: dict, rqs_rubric: dict) -> dict:
    detect = row.get("detection", {})
    e2e = row.get("e2e", {})
    rqs = e2e.get("rqs") or {}
    return {
        "id": row["id"],
        "split": row["split"],
        "category": row.get("category", ""),
        "file": row["file"],
        "sketchup_reviewed": e2e.get("sketchup_reviewed", False),
        "rectify_ok": e2e.get("rectify_ok", ""),
        "windows_detected": detect.get("window_count", ""),
        "windows_true": e2e.get("windows_true", ""),
        "doors_detected": detect.get("door_count", ""),
        "doors_true": e2e.get("doors_true", ""),
        "overlay_correction": e2e.get("overlay_correction", ""),
        "generate_ok": e2e.get("generate_ok", ""),
        "correction_time_sec": e2e.get("correction_time_sec", ""),
        "failure_classes": ";".join(e2e.get("failure_classes") or []),
        "rqs_total": e2e.get("rqs_total", ""),
        "notes": e2e.get("notes", ""),
        **{f"rqs_{k}": rqs.get(k, "") for k in rqs_rubric},
    }


def write_csv(rows: list[dict], rqs_rubric: dict, path: Path) -> None:
    fields = csv_fields(rqs_rubric)
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow(row_to_csv(row, rqs_rubric))


def write_html(rows: list[dict], rqs_rubric: dict, overlays: dict[str, str], path: Path) -> None:
  split_labels = {"holdout": "HOLD-OUT（禁止训练）", "val": "VAL", "train": "TRAIN"}
  cards = []
  for row in rows:
    detect = row["detection"]
    rectify = row.get("rectify") or {}
    hints = ", ".join(row.get("automated_failure_hints") or [])
    action = sketchup_action(row)
    split_label = split_labels.get(row["split"], row["split"])
    overlay_src = html.escape(overlays.get(row["file"], ""))

    rqs_rows = []
    for key, (label, max_pts) in RQS_LABELS.items():
      rqs_rows.append(
        f"<tr><td>{html.escape(label)}</td><td>{max_pts}</td><td class='score'>—</td></tr>"
      )

    cards.append(
      f"""
      <article class="card split-{html.escape(row['split'])}">
        <header>
          <span class="badge split">{html.escape(split_label)}</span>
          <span class="badge id">{html.escape(row['id'])}</span>
          <span class="badge cat">{html.escape(row.get('category',''))}</span>
        </header>
        <h2>{html.escape(row['file'])}</h2>
        <img src="{overlay_src}" alt="{html.escape(row['file'])}"/>
        <dl class="meta">
          <dt>检测</dt><dd>{detect['window_count']} 窗 / {detect['door_count']} 门 · {html.escape(detect['method'])} · conf {detect['confidence']}</dd>
          <dt>Rectify</dt><dd>{html.escape(str(rectify.get('method','?')))} (conf {rectify.get('confidence','?')})</dd>
          <dt>Hints</dt><dd>{html.escape(hints)}</dd>
          <dt>SketchUp 动作</dt><dd><strong>{html.escape(action)}</strong></dd>
        </dl>
        <table class="rqs">
          <thead><tr><th>RQS 维度</th><th>满分</th><th>得分</th></tr></thead>
          <tbody>{''.join(rqs_rows)}</tbody>
          <tfoot><tr><td colspan="2">合计</td><td class="score">/100</td></tr></tfoot>
        </table>
        <div class="checklist">
          <label><input type="checkbox" disabled/> Rectify OK</label>
          <label><input type="checkbox" disabled/> Overlay 修正完成</label>
          <label><input type="checkbox" disabled/> Generate OK</label>
          <label><input type="checkbox" disabled/> 修正 &lt; 1 min</label>
        </div>
      </article>
      """
    )

  document = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8"/>
  <title>Geomora A1 SketchUp 验收清单</title>
  <style>
    body {{ font-family: "Segoe UI", sans-serif; margin: 24px; background: #f4f6f8; color: #1a1a1a; }}
    h1 {{ margin-bottom: 4px; }}
    .intro {{ color: #555; margin-bottom: 24px; max-width: 900px; line-height: 1.5; }}
    .intro code {{ background: #e8eef7; padding: 2px 6px; border-radius: 4px; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(400px, 1fr)); gap: 16px; }}
    .card {{ background: #fff; border-radius: 10px; padding: 14px; box-shadow: 0 1px 4px rgba(0,0,0,.08); }}
    .card img {{ width: 100%; border-radius: 6px; background: #ddd; }}
    .card header {{ display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 8px; }}
    .badge {{ font-size: 11px; font-weight: 600; padding: 2px 8px; border-radius: 999px; }}
    .badge.split {{ background: #e8eef7; }}
    .split-holdout .badge.split {{ background: #fde8e8; color: #b42318; }}
    .badge.id {{ background: #f0f0f0; }}
    .badge.cat {{ background: #eef7ee; }}
    .meta {{ font-size: 13px; margin: 8px 0; }}
    .meta dt {{ font-weight: 600; margin-top: 6px; }}
    .meta dd {{ margin: 2px 0 0; color: #444; }}
    table.rqs {{ width: 100%; font-size: 12px; border-collapse: collapse; margin-top: 10px; }}
    table.rqs th, table.rqs td {{ border: 1px solid #ddd; padding: 4px 6px; text-align: left; }}
    table.rqs .score {{ text-align: center; font-weight: 600; }}
    .checklist {{ margin-top: 10px; font-size: 13px; display: grid; grid-template-columns: 1fr 1fr; gap: 4px; }}
    @media print {{
      body {{ background: #fff; }}
      .grid {{ display: block; }}
      .card {{ break-inside: avoid; margin-bottom: 16px; page-break-inside: avoid; }}
    }}
  </style>
</head>
<body>
  <h1>A1 · SketchUp 验收清单（{len(rows)} 张）</h1>
  <p class="intro">
    顺序：hold-out → val → train。每张走完整流程：
    Load → Rectify → Detect → Overlay → Scale → Rationalize → Validate → Generate。<br/>
  分数填 <code>checklist_scores.csv</code>，然后运行
  <code>python scripts/import_a1_e2e_scores.py --csv cache/benchmark_a1/checklist_scores.csv</code>
  </p>
  <div class="grid">
    {''.join(cards)}
  </div>
</body>
</html>
"""
  path.write_text(document, encoding="utf-8")


def write_summary_md(rows: list[dict], summary: dict, path: Path) -> None:
    holdout = [r for r in rows if r["split"] == "holdout"]
    fails = [r for r in rows if not r["detection"]["passed_smoke"]]

    lines = [
        "# A1 Detection Baseline Report",
        "",
        f"**Generated from:** `benchmark_a1_e2e.json`",
        f"**Images:** {summary.get('images', len(rows))} | **Detect smoke pass:** {summary.get('detect_pass', '?')}/{summary.get('images', len(rows))}",
        "",
        "## Hold-out (gate: ≥4/5 Generate after light overlay)",
        "",
        "| ID | File | Windows | Doors | Conf | Hints | Smoke |",
        "|----|------|---------|-------|------|-------|-------|",
    ]
    for row in holdout:
        d = row["detection"]
        hints = ", ".join(row.get("automated_failure_hints") or [])
        status = "PASS" if d["passed_smoke"] else "**FAIL**"
        lines.append(
            f"| {row['id']} | `{row['file'][:16]}…` | {d['window_count']} | {d['door_count']} | {d['confidence']} | {hints} | {status} |"
        )

    lines.extend([
        "",
        "## Detection failures",
        "",
    ])
    if fails:
        for row in fails:
            d = row["detection"]
            lines.append(f"- **{row['id']}** `{row['file']}` — {d['window_count']}w/{d['door_count']}d, conf {d['confidence']}")
    else:
        lines.append("- None")

    lines.extend([
        "",
        "## Next step",
        "",
        "1. Open `cache/benchmark_a1/index.html` in browser",
        "2. SketchUp E2E on each image (hold-out first)",
        "3. Fill `cache/benchmark_a1/checklist_scores.csv`",
        "4. `python scripts/import_a1_e2e_scores.py`",
        "",
    ])
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    args = parse_args()
    payload = json.loads(args.e2e.read_text(encoding="utf-8"))
    rows = sorted(payload["results"], key=priority_key)
    rqs_rubric = payload.get("rqs_rubric", {k: v for k, (_, v) in RQS_LABELS.items()})

    out_dir = args.out.resolve()
    overlay_dir = out_dir / "overlays"
    out_dir.mkdir(parents=True, exist_ok=True)

    overlays: dict[str, str] = {}
    for row in rows:
        image_path = Path(row["image_path"])
        if image_path.exists():
            overlays[row["file"]] = write_overlay(image_path, args.method, overlay_dir)

    write_csv(rows, rqs_rubric, out_dir / "checklist_scores.csv")
    write_html(rows, rqs_rubric, overlays, out_dir / "index.html")
    write_summary_md(rows, payload.get("summary", {}), out_dir / "BASELINE_REPORT.md")

    print(f"A1 checklist: {out_dir}")
    print(f"  HTML:  {out_dir / 'index.html'}")
    print(f"  CSV:   {out_dir / 'checklist_scores.csv'}")
    print(f"  Report: {out_dir / 'BASELINE_REPORT.md'}")
    print("Order: hold-out first, then val, then train")
    for row in rows[:5]:
        print(f"  [{row['split']}] {row['id']} — {sketchup_action(row)}")


if __name__ == "__main__":
    main()
