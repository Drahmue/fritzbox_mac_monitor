# task_umstellen.ps1 - stellt den Task \AHSkripts\FritzboxMacMonitor auf lokale Pfade um (datahub DH-031)
# Aktion vorher: python src/fritzbox_mac_monitor.py, Arbeitsverzeichnis \\HauServer\Dataserver\... (UNC, globales Python)
# Aktion nachher: powershell.exe -File D:\...\start_fritzbox_mac_monitor.ps1 (.venv), Arbeitsverzeichnis D:\...
# Trigger, Konto (Service) und Einstellungen bleiben unveraendert. Als Administrator ausfuehren;
# das Kennwort des Kontos Service wird verdeckt abgefragt und nicht gespeichert.

$ErrorActionPreference = "Stop"
$TaskPath   = "\AHSkripts\"
$TaskName   = "FritzboxMacMonitor"
$ProjectDir = "D:\Dataserver\_Batchprozesse\fritzbox_mac_monitor"

$task = Get-ScheduledTask -TaskPath $TaskPath -TaskName $TaskName
Write-Host "Vorher: $($task.Actions[0].Execute) $($task.Actions[0].Arguments) | $($task.Actions[0].WorkingDirectory)"

$action = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$ProjectDir\start_fritzbox_mac_monitor.ps1`"" `
    -WorkingDirectory $ProjectDir

$secure = Read-Host -AsSecureString "Kennwort des Kontos Service"
$plain  = [System.Net.NetworkCredential]::new("", $secure).Password
try {
    Set-ScheduledTask -TaskPath $TaskPath -TaskName $TaskName -Action $action -User "Service" -Password $plain | Out-Null
}
finally {
    $plain = $null
}

$task = Get-ScheduledTask -TaskPath $TaskPath -TaskName $TaskName
Write-Host "Nachher: $($task.Actions[0].Execute) $($task.Actions[0].Arguments) | $($task.Actions[0].WorkingDirectory)"
Write-Host "Konto: $($task.Principal.UserId)  Trigger: $($task.Triggers[0].StartBoundary) alle $($task.Triggers[0].Repetition.Interval)"
