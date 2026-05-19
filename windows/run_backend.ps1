param(
  [switch]$Hidden
)

$TargetRoot = Join-Path $env:LOCALAPPDATA "LolMakroBridge"
$ExePath = Join-Path $TargetRoot "app\LolMakroBridge.exe"
$VbsPath = Join-Path $TargetRoot "run_hidden.vbs"

if (-not (Test-Path $ExePath)) {
  throw "Installed executable not found: $ExePath"
}

if ($Hidden) {
  Start-Process -WindowStyle Hidden -FilePath "wscript.exe" -ArgumentList "`"$VbsPath`""
} else {
  & $ExePath
}

$LinkFile = Join-Path $TargetRoot "latest-link.txt"
if (Test-Path $LinkFile) {
  Write-Host "Current link:"
  Get-Content $LinkFile
}
