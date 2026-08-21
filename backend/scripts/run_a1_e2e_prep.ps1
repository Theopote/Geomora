# A1 SketchUp E2E prep — regenerate checklist and show progress.
# Run from repo root or backend directory.

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Backend = Split-Path -Parent $ScriptDir
$Repo = Split-Path -Parent $Backend
$Python = Join-Path $Backend ".venv\Scripts\python.exe"

if (-not (Test-Path $Python)) {
    Write-Error "Backend venv not found. Run backend\start_server.bat or create .venv first."
}

Write-Host "== A1 E2E prep ==" -ForegroundColor Cyan

if (-not (Test-Path (Join-Path $Backend "cache\benchmark_a1_e2e.json"))) {
    Write-Host "Running detection baseline..."
    & $Python (Join-Path $Backend "scripts\run_real_photo_benchmark.py")
}

Write-Host "Exporting checklist pack..."
& $Python (Join-Path $Backend "scripts\export_a1_checklist.py")

$Csv = Join-Path $Backend "cache\benchmark_a1\checklist_scores.csv"
if (Test-Path $Csv) {
    $reviewed = (Import-Csv $Csv | Where-Object { $_.sketchup_reviewed -match '^(?i:true|1|yes)$' }).Count
    Write-Host "Reviewed: $reviewed / 20"
    Write-Host "CSV: $Csv"
}

$html = Join-Path $Backend "cache\benchmark_a1\index.html"
if (Test-Path $html) {
    Write-Host "Checklist HTML: $html"
}

Write-Host ""
Write-Host "SketchUp workflow:" -ForegroundColor Yellow
Write-Host "  Extensions -> Geomora -> A1 Real Photo Benchmark -> Review Next Photo"
Write-Host "  After each image: Record A1 Score..."
Write-Host ""
Write-Host "When done (or after each batch):" -ForegroundColor Yellow
Write-Host "  SketchUp -> Geomora -> A1 Real Photo Benchmark -> Import A1 Scores to JSON"
Write-Host "  or: .\.venv\Scripts\python scripts\import_a1_e2e_scores.py"
