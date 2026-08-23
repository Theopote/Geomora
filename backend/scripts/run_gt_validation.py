"""Validate every Ground Truth document referenced by the minimal set."""

from __future__ import annotations

import json
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
sys.path.insert(0, str(BACKEND_ROOT))

from geomora_reconstruct.metrics import validate_ground_truth  # noqa: E402


def main() -> int:
    manifest = json.loads((REPO_ROOT / "tests/reconstruction/minimal_set.json").read_text(encoding="utf-8"))
    gt_dir = REPO_ROOT / manifest["ground_truth_dir"]
    failed = False
    for item in manifest["photos"]:
        path = gt_dir / f"{item['id']}.json"
        if not path.exists():
            print(f"[FAIL] {item['id']}: missing {path}")
            failed = True
            continue
        truth = json.loads(path.read_text(encoding="utf-8"))
        report = validate_ground_truth(truth)
        status = "PASS" if report.gate_ready else "FAIL"
        print(f"[{status}] {item['id']}: errors={len(report.errors)} warnings={len(report.warnings)}")
        for issue in report.issues:
            print(f"  - {issue.severity} {issue.code}: {issue.message}")
        failed = failed or not report.gate_ready
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
