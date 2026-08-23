"""Import manual SketchUp scores from checklist CSV back into benchmark_a1_e2e.json.

Example:
  cd backend
  .venv\\Scripts\\python scripts/import_a1_e2e_scores.py --csv cache/benchmark_a1/checklist_scores.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]

E2E_DEFAULT = BACKEND_ROOT / "cache" / "benchmark_a1_e2e.json"
CSV_DEFAULT = BACKEND_ROOT / "cache" / "benchmark_a1" / "checklist_scores.csv"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import A1 SketchUp scores from CSV")
    parser.add_argument("--csv", type=Path, default=CSV_DEFAULT)
    parser.add_argument("--e2e", type=Path, default=E2E_DEFAULT)
    parser.add_argument("--out", type=Path, default=None, help="Output path (default: overwrite --e2e)")
    return parser.parse_args()


def parse_bool(value: str) -> bool:
    return str(value).strip().lower() in ("1", "true", "yes", "y")


def parse_optional_int(value: str) -> int | None:
    text = str(value).strip()
    if not text:
        return None
    return int(float(text))


def parse_optional_float(value: str) -> float | None:
    text = str(value).strip()
    if not text:
        return None
    return float(text)


def load_csv(path: Path) -> dict[str, dict]:
    with path.open(encoding="utf-8-sig") as handle:
        return {row["id"]: row for row in csv.DictReader(handle)}


def apply_row(result: dict, csv_row: dict, rqs_keys: list[str]) -> None:
    e2e = result.setdefault("e2e", {})
    e2e["sketchup_reviewed"] = parse_bool(csv_row.get("sketchup_reviewed", ""))

    rectify_ok = csv_row.get("rectify_ok", "").strip()
    if rectify_ok:
        e2e["rectify_ok"] = parse_bool(rectify_ok) if rectify_ok.lower() in ("true", "false", "1", "0", "yes", "no") else rectify_ok

    for field in ("windows_true", "doors_true", "overlay_correction", "notes"):
        val = csv_row.get(field, "").strip()
        if val:
            e2e[field] = val

    for field in ("generate_ok",):
        val = csv_row.get(field, "").strip().lower()
        if val in ("true", "false", "1", "0", "yes", "no"):
            e2e[field] = parse_bool(val)
        elif val:
            e2e[field] = val

    if csv_row.get("correction_time_sec", "").strip():
        e2e["correction_time_sec"] = parse_optional_float(csv_row["correction_time_sec"])

    failure = csv_row.get("failure_classes", "").strip()
    if failure:
        normalized = failure.replace(",", ";").replace("；", ";").replace("，", ";")
        e2e["failure_classes"] = [part.strip() for part in normalized.split(";") if part.strip()]

    rqs: dict[str, int | None] = e2e.setdefault("rqs", {})
    for key in rqs_keys:
        col = f"rqs_{key}"
        if csv_row.get(col, "").strip():
            rqs[key] = parse_optional_int(csv_row[col])

    if csv_row.get("rqs_total", "").strip():
        e2e["rqs_total"] = parse_optional_int(csv_row["rqs_total"])
    elif any(rqs.get(k) is not None for k in rqs_keys):
        e2e["rqs_total"] = sum(v for v in rqs.values() if isinstance(v, int))


def summarize_e2e(results: list[dict]) -> dict:
    reviewed = [r for r in results if r.get("e2e", {}).get("sketchup_reviewed")]
    generate_ok = [r for r in reviewed if r.get("e2e", {}).get("generate_ok") is True]
    holdout = [r for r in results if r["split"] == "holdout"]
    holdout_ok = [r for r in holdout if r.get("e2e", {}).get("generate_ok") is True]

    rqs_scores = [r["e2e"]["rqs_total"] for r in reviewed if r.get("e2e", {}).get("rqs_total") is not None]

    return {
        "reviewed": len(reviewed),
        "total": len(results),
        "generate_ok": len(generate_ok),
        "holdout_generate_ok": f"{len(holdout_ok)}/{len(holdout)}",
        "rqs_avg": round(sum(rqs_scores) / len(rqs_scores), 1) if rqs_scores else None,
    }


def main() -> None:
    args = parse_args()
    if not args.csv.exists():
        raise SystemExit(f"CSV not found: {args.csv}")

    payload = json.loads(args.e2e.read_text(encoding="utf-8"))
    csv_rows = load_csv(args.csv)
    rqs_keys = list(payload.get("rqs_rubric", {}).keys())

    merged = 0
    for result in payload["results"]:
        csv_row = csv_rows.get(result["id"])
        if csv_row:
            apply_row(result, csv_row, rqs_keys)
            merged += 1

    payload["e2e_summary"] = summarize_e2e(payload["results"])

    out_path = args.out or args.e2e
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    summary = payload["e2e_summary"]
    print(f"Merged {merged}/{len(payload['results'])} rows into {out_path.resolve()}")
    print(f"  Reviewed: {summary['reviewed']}/{summary['total']}")
    print(f"  Generate OK: {summary['generate_ok']}")
    print(f"  Hold-out Generate OK: {summary['holdout_generate_ok']}")
    if summary["rqs_avg"] is not None:
        print(f"  RQS average: {summary['rqs_avg']}/100")


if __name__ == "__main__":
    main()
