"""Tests for A1 benchmark import/export scripts."""

from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[2] / "backend"
EXPORT_SCRIPT = BACKEND_ROOT / "scripts" / "export_a1_checklist.py"
IMPORT_SCRIPT = BACKEND_ROOT / "scripts" / "import_a1_e2e_scores.py"
BENCHMARK_SCRIPT = BACKEND_ROOT / "scripts" / "run_real_photo_benchmark.py"
E2E_JSON = BACKEND_ROOT / "cache" / "benchmark_a1_e2e.json"


@pytest.mark.skipif(not E2E_JSON.exists(), reason="benchmark_a1_e2e.json not generated yet")
def test_export_a1_checklist_produces_csv_and_html(tmp_path):
    out = tmp_path / "checklist"
    completed = subprocess.run(
        [sys.executable, str(EXPORT_SCRIPT), "--e2e", str(E2E_JSON), "--out", str(out)],
        cwd=BACKEND_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert (out / "index.html").exists()
    assert (out / "checklist_scores.csv").exists()
    rows = list(csv.DictReader((out / "checklist_scores.csv").open(encoding="utf-8-sig")))
    assert len(rows) == 20
    assert rows[0]["split"] == "holdout"


@pytest.mark.skipif(not E2E_JSON.exists(), reason="benchmark_a1_e2e.json not generated yet")
def test_import_a1_e2e_scores_merges_csv(tmp_path):
    out = tmp_path / "checklist"
    subprocess.run(
        [sys.executable, str(EXPORT_SCRIPT), "--e2e", str(E2E_JSON), "--out", str(out)],
        cwd=BACKEND_ROOT,
        check=True,
    )
    csv_path = out / "checklist_scores.csv"
    rows = list(csv.DictReader(csv_path.open(encoding="utf-8-sig")))
    rows[0]["sketchup_reviewed"] = "true"
    rows[0]["generate_ok"] = "true"
    rows[0]["rqs_total"] = "72"
    rows[0]["rqs_perspective_rectification"] = "12"
    rows[0]["failure_classes"] = "missed_window;false_door"
    with csv_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    merged_path = tmp_path / "merged.json"
    completed = subprocess.run(
        [
            sys.executable,
            str(IMPORT_SCRIPT),
            "--csv",
            str(csv_path),
            "--e2e",
            str(E2E_JSON),
            "--out",
            str(merged_path),
        ],
        cwd=BACKEND_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    payload = json.loads(merged_path.read_text(encoding="utf-8"))
    holdout_id = rows[0]["id"]
    merged = next(r for r in payload["results"] if r["id"] == holdout_id)
    assert merged["e2e"]["sketchup_reviewed"] is True
    assert merged["e2e"]["rqs_total"] == 72
    assert "missed_window" in merged["e2e"]["failure_classes"]
