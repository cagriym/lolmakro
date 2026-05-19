param(
  [string]$SourceDist = "",
  [int]$Port = 8765,
  [switch]$RunNow
)

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
if ([string]::IsNullOrWhiteSpace($SourceDist)) {
  $SourceDist = Join-Path $Root "dist\LolMakroBridge"
}

if (-not (Test-Path $SourceDist)) {
  throw "Source dist folder not found: $SourceDist"
}

$TargetRoot = Join-Path $env:LOCALAPPDATA "LolMakroBridge"
$TargetApp = Join-Path $TargetRoot "app"
$TaskName = "LolMakroBridgeBackend"
$ExePath = Join-Path $TargetApp "LolMakroBridge.exe"
$VbsPath = Join-Path $TargetRoot "run_hidden.vbs"
$CmdPath = Join-Path $TargetRoot "run_visible.cmd"

New-Item -ItemType Directory -Force $TargetApp | Out-Null

Write-Host "[1/6] Copying app files to $TargetApp"
robocopy $SourceDist $TargetApp /MIR /NFL /NDL /NJH /NJS /NP | Out-Null

if (-not (Test-Path $ExePath)) {
  throw "Executable not found after copy: $ExePath"
}

Write-Host "[2/6] Writing runtime env file"
@"
LOL_BRIDGE_HOST=0.0.0.0
LOL_BRIDGE_PORT=$Port
LOL_BRIDGE_ICON_PATH=C:\Users\xmemo\OneDrive\Desktop\coding\projelerim\python\makro_programi\app_icon.ico
"@ | Set-Content -Encoding utf8 (Join-Path $TargetRoot ".env")

Write-Host "[3/6] Creating hidden launcher"
@"
Set WshShell = CreateObject("WScript.Shell")
WshShell.Run """$ExePath""", 0, False
"@ | Set-Content -Encoding ascii $VbsPath

Write-Host "[3b/6] Creating visible launcher"
@"
@echo off
start "" "$ExePath"
"@ | Set-Content -Encoding ascii $CmdPath

Write-Host "[4/6] Registering startup scheduled task"
$action = New-ScheduledTaskAction -Execute "cmd.exe" -Argument "/c `"$CmdPath`""
$trigger = New-ScheduledTaskTrigger -AtLogOn
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable

try {
  if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
  }
  Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Principal $principal -Settings $settings | Out-Null
} catch {
  Write-Warning "Scheduled Task kaydi yapilamadi. Startup klasoru fallback kullanilacak."
  $startupDir = [Environment]::GetFolderPath("Startup")
  $startupCmd = Join-Path $startupDir "LolMakroBridge.cmd"
@"
@echo off
start "" "$ExePath"
"@ | Set-Content -Encoding ascii $startupCmd
}

Write-Host "[5/6] Ensuring firewall rule for local network"
$ruleName = "LolMakroBridge $Port"
try {
  if (-not (Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue)) {
    New-NetFirewallRule -DisplayName $ruleName -Direction Inbound -Action Allow -Protocol TCP -LocalPort $Port -Profile Private | Out-Null
  }
} catch {
  Write-Warning "Firewall rule eklenemedi (yonetici yetkisi gerekebilir). Kurulum devam ediyor."
}

Write-Host "[6/6] Installation complete"
Write-Host "Backend URL: http://$(hostname):$Port"
Write-Host "LAN URL is printed at startup and stored in: $TargetRoot\latest-link.txt"
Write-Host "QR PNG path: $TargetRoot\latest-qr.png"

if ($RunNow) {
  Start-Process -WindowStyle Hidden -FilePath "wscript.exe" -ArgumentList "`"$VbsPath`""
  Write-Host "Backend started in background."
}
