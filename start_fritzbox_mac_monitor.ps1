# fritzbox_mac_monitor - Start-Skript
# Wird stuendlich per Task Scheduler ausgefuehrt (Task \AHSkripts\FritzboxMacMonitor, Konto Service).
# Lokale Pfade, eigene .venv (datahub DH-031). Das Python-Skript schreibt sein Log selbst nach
# logs\mac_monitor_yyyy-MM.log und meldet neue Geraete bzw. Fehler per Telegram.

$ProjectDir = "D:\Dataserver\_Batchprozesse\fritzbox_mac_monitor"
$VenvPython = "$ProjectDir\.venv\Scripts\python.exe"
$Script     = "$ProjectDir\src\fritzbox_mac_monitor.py"

Set-Location -Path $ProjectDir
$env:PYTHONIOENCODING = "utf-8"

if (-not (Test-Path $VenvPython)) {
    Write-Error "Python-Interpreter nicht gefunden: $VenvPython"
    exit 1
}

& $VenvPython $Script
exit $LASTEXITCODE
