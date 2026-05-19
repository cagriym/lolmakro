param(
  [string]$PythonExe = "python"
)

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$DistDir = Join-Path $Root "dist"
$BuildDir = Join-Path $Root "build"

Write-Host "[1/5] Installing Python dependencies"
& $PythonExe -m pip install -r (Join-Path $Root "requirements.txt") pyinstaller

Write-Host "[2/5] Building mobile-panel"
Push-Location (Join-Path $Root "mobile-panel")
if (Test-Path "package-lock.json") {
  npm ci
} else {
  npm install
}
npm run build
Pop-Location

Write-Host "[3/5] Cleaning old build artifacts"
if (Test-Path $DistDir) { Remove-Item -Recurse -Force $DistDir }
if (Test-Path $BuildDir) { Remove-Item -Recurse -Force $BuildDir }

Write-Host "[4/5] Building Windows executable"
& $PythonExe -m PyInstaller `
  --noconfirm `
  --clean `
  --name LolMakroBridge `
  --onedir `
  --hidden-import live_server `
  --hidden-import qrcode `
  --hidden-import pystray `
  --hidden-import PIL `
  --add-data "mobile-panel/dist;mobile-panel/dist" `
  --collect-data lcu_backend `
  start_server.py

Write-Host "[5/5] Build completed"
Write-Host "Output: $(Join-Path $Root 'dist\LolMakroBridge')"
Write-Host "Next: run windows\\install_once.ps1"
