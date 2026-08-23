# Geomora RBZ build script
# Usage: .\build_rbz.ps1

$ErrorActionPreference = "Stop"

$Root = $PSScriptRoot
$PluginDir = Join-Path $Root "plugin"
$DistDir = Join-Path $Root "dist"
$RbzName = "geomora.rbz"
$StagingDir = Join-Path $env:TEMP "geomora-rbz-staging"

Write-Host "Geomora RBZ build"
Write-Host "================="

# Sync fixture into plugin bundle
$SourceFixture = Join-Path $Root "examples\facade_phase0.json"
$TargetFixtureDir = Join-Path $PluginDir "geomora\examples"
$TargetFixture = Join-Path $TargetFixtureDir "facade_phase0.json"

if (-not (Test-Path $SourceFixture)) {
    throw "Missing source fixture: $SourceFixture"
}

New-Item -ItemType Directory -Path $TargetFixtureDir -Force | Out-Null
Copy-Item $SourceFixture $TargetFixture -Force
Write-Host "[OK] Synced fixture -> plugin/geomora/examples/"

# Stage files for packaging
if (Test-Path $StagingDir) {
    Remove-Item $StagingDir -Recurse -Force
}
New-Item -ItemType Directory -Path $StagingDir | Out-Null

Copy-Item (Join-Path $PluginDir "geomora.rb") $StagingDir
Copy-Item (Join-Path $PluginDir "geomora") (Join-Path $StagingDir "geomora") -Recurse

$LicensePath = Join-Path $Root "LICENSE"
if (Test-Path $LicensePath) {
    Copy-Item $LicensePath $StagingDir
    Write-Host "[OK] Included LICENSE in package"
}

# Create RBZ (ZIP)
New-Item -ItemType Directory -Path $DistDir -Force | Out-Null
$ZipPath = Join-Path $DistDir "geomora.zip"
$RbzPath = Join-Path $DistDir $RbzName

if (Test-Path $ZipPath) { Remove-Item $ZipPath -Force }
if (Test-Path $RbzPath) { Remove-Item $RbzPath -Force }

Compress-Archive -Path (Join-Path $StagingDir "*") -DestinationPath $ZipPath -Force
Rename-Item $ZipPath $RbzPath

Remove-Item $StagingDir -Recurse -Force

Write-Host "[OK] Built: $RbzPath"
Write-Host ""
Write-Host "Install in SketchUp:"
Write-Host "  Window -> Extension Manager -> Install Extension -> select geomora.rbz"
