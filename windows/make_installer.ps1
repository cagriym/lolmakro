param(
  [string]$PythonExe = "python"
)

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$BuildScript = Join-Path $PSScriptRoot "build_windows.ps1"
$IssPath = Join-Path $PSScriptRoot "LolMakroBridgeSetup.iss"
$isccCandidates = @(
  "C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
  "C:\Program Files\Inno Setup 6\ISCC.exe",
  "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe"
)
$IsccPath = $isccCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1

Write-Host "[1/4] Building application binaries"
powershell -ExecutionPolicy Bypass -File $BuildScript -PythonExe $PythonExe

if (-not $IsccPath) {
  Write-Host "[2/4] Inno Setup not found. Installing via winget..."
  winget install -e --id JRSoftware.InnoSetup --accept-package-agreements --accept-source-agreements
  $IsccPath = $isccCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
}

if (-not $IsccPath) {
  throw "ISCC.exe bulunamadi. Inno Setup kurulumunu kontrol et."
}

Write-Host "[3/4] Compiling installer"
& $IsccPath $IssPath

Write-Host "[4/4] Done"
Write-Host "Installer output: $(Join-Path $Root 'installer\LolMakroBridge_Setup.exe')"
