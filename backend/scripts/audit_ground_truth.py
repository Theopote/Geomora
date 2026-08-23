"""Audit Reconstruction Metrics ground truth before tuning or evaluation."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
sys.path.insert(0, str(BACKEND_ROOT))

from geomora_reconstruct.metrics import validate_ground_truth  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*", type=Path)
    parser.add_argument("--ground-truth-dir", type=Path, default=REPO_ROOT / "tests" / "reconstruction" / "ground_truth")
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--allow-warnings", action="store_true", help="Exit successfully when only warnings exist")
    args = parser.parse_args()
    paths = args.paths or sorted(args.ground_truth_dir.glob("photo_*.json"))
    reports = []
    for path in paths:
        truth = json.loads(path.read_text(encoding="utf-8"))
        report = validate_ground_truth(truth).to_dict()
        report["path"] = str(path)
        reports.append(report)
        print(f"{report['photo_id']}: errors={report['error_count']} warnings={report['warning_count']} gate_ready={report['gate_ready']}")
        for issue in report["issues"]:
            print(f"  {issue['severity'].upper()} {issue['code']} {issue['path']}: {issue['message']}")
    payload = {"schema_version": "gt-audit-v1", "files": len(reports), "gate_ready": all(row["gate_ready"] for row in reports), "reports": reports}
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    has_errors = any(row["error_count"] for row in reports)
    has_warnings = any(row["warning_count"] for row in reports)
    return 1 if has_errors or (has_warnings and not args.allow_warnings) else 0


if __name__ == "__main__":
    raise SystemExit(main())
