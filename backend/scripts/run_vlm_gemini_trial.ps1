# Geomora VLM prelabel trial (Gemini)
# Usage:
#   cd F:\development\Geomora\backend
#   powershell -ExecutionPolicy Bypass -File .\scripts\run_vlm_gemini_trial.ps1

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot\..

if (-not $env:GEMINI_API_KEY -and -not $env:GOOGLE_API_KEY) {
    Write-Host "Enter Gemini API key (hidden):" -ForegroundColor Yellow
    $secure = Read-Host -AsSecureString
    $ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
    try {
        $env:GEMINI_API_KEY = [Runtime.InteropServices.Marshal]::PtrToStringAuto($ptr)
    } finally {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr)
    }
}

if (-not $env:GEMINI_API_KEY -and $env:GOOGLE_API_KEY) {
    $env:GEMINI_API_KEY = $env:GOOGLE_API_KEY
}

if (-not $env:GEMINI_API_KEY) {
    throw "GEMINI_API_KEY is not set."
}

Write-Host "=== Step 1/3: prelabel 1 image (gemini-2.5-flash) ===" -ForegroundColor Cyan
.\.venv\Scripts\python scripts\vlm_prelabel_facade.py `
    --images cache\real_photo_desktop_rectified `
    --out data\facade_yolo_vlm `
    --split train `
    --provider gemini `
    --model gemini-2.5-flash `
    --limit 1

if ($LASTEXITCODE -ne 0) {
    Write-Host "Primary model failed. The script will auto-fallback to other Gemini models." -ForegroundColor Yellow
    exit $LASTEXITCODE
}

Write-Host "=== Step 2/3: open review HTML ===" -ForegroundColor Cyan
$review = Resolve-Path "cache\vlm_prelabel_review\index.html"
Start-Process $review.Path

Write-Host "=== Step 3/3: done ===" -ForegroundColor Green
Write-Host "Check boxes in the browser."
Write-Host "If OK, run batch script:"
Write-Host '  powershell -ExecutionPolicy Bypass -File .\scripts\run_vlm_gemini_batch.ps1'
