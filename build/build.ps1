# Build GitHub Actions Tray into a single-file .exe under release/.
#
# Usage (from the repo root):
#   powershell -ExecutionPolicy Bypass -File build\build.ps1
#
# Steps: ensure deps -> generate icon -> run PyInstaller -> output release\GitHubActionsTray.exe
$ErrorActionPreference = "Stop"

# Move to the repo root (parent of this script's folder).
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

Write-Host "==> Installing build dependencies..." -ForegroundColor Cyan
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt

Write-Host "==> Generating application icon..." -ForegroundColor Cyan
python build\make_icon.py

Write-Host "==> Building executable with PyInstaller..." -ForegroundColor Cyan
python -m PyInstaller build\app.spec --noconfirm --clean `
    --distpath release --workpath build\work

Write-Host "==> Cleaning up intermediate build files..." -ForegroundColor Cyan
if (Test-Path build\work) { Remove-Item -Recurse -Force build\work }

Write-Host ""
Write-Host "Done. Executable: release\GitHubActionsTray.exe" -ForegroundColor Green
