# Geomora VLM prelabel batch (Gemini) - all rectified images
# Prerequisite: GEMINI_API_KEY set in this terminal session

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot\..

if (-not $env:GEMINI_API_KEY -and -not $env:GOOGLE_API_KEY) {
    throw "Set GEMINI_API_KEY first, or run run_vlm_gemini_trial.ps1"
}
if (-not $env:GEMINI_API_KEY) {
    $env:GEMINI_API_KEY = $env:GOOGLE_API_KEY
}

$model = "gemini-2.5-flash"
Write-Host "Batch prelabel 28 images, model: $model (auto-fallback enabled)" -ForegroundColor Cyan

.\.venv\Scripts\python scripts\vlm_prelabel_facade.py `
    --images cache\real_photo_desktop_rectified `
    --out data\facade_yolo_vlm `
    --split train `
    --provider gemini `
    --model $model

if ($LASTEXITCODE -ne 0) {
    Write-Host "Batch failed. Check cache\vlm_prelabel_report.json" -ForegroundColor Yellow
    exit $LASTEXITCODE
}

Start-Process (Resolve-Path "cache\vlm_prelabel_review\index.html").Path
Write-Host "Done. Dataset: data\facade_yolo_vlm\train\" -ForegroundColor Green
