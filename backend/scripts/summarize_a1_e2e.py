"""Summarize A1 E2E results after CSV import."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
E2E_PATH = BACKEND_ROOT / "cache" / "benchmark_a1_e2e.json"


def main() -> None:
    payload = json.loads(E2E_PATH.read_text(encoding="utf-8"))
    results = payload["results"]
    summary = payload.get("e2e_summary", {})

    print("A1 E2E Summary")
    print("==============")
    for key, value in summary.items():
        print(f"  {key}: {value}")

    fc = Counter()
    for row in results:
        for item in row.get("e2e", {}).get("failure_classes") or []:
            fc[item] += 1

    print("\nFailure taxonomy:")
    for name, count in fc.most_common():
        print(f"  {name}: {count}/20")

    print("\nRQS by split:")
    for split in ("holdout", "val", "train"):
        rows = [row for row in results if row["split"] == split]
        scores = [row["e2e"]["rqs_total"] for row in rows if row.get("e2e", {}).get("rqs_total") is not None]
        avg = sum(scores) / len(scores) if scores else 0.0
        grade_a = sum(1 for score in scores if score >= 70)
        print(f"  {split}: avg={avg:.1f} grade_A={grade_a}/{len(rows)}")

    print("\nPer image:")
    for row in results:
        e2e = row.get("e2e", {})
        rqs = e2e.get("rqs_total")
        grade = "A" if rqs and rqs >= 70 else ("B" if rqs and rqs >= 50 else "C")
        print(
            f"  {row['id']} [{row['split']}] RQS={rqs} {grade} "
            f"rectify={e2e.get('rectify_ok')} overlay={e2e.get('overlay_correction')}"
        )


if __name__ == "__main__":
    main()
