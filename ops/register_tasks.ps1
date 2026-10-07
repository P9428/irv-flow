# Registers the workstation tasks through ~/ops/run-hidden.vbs (no console pop-ups), same as the siblings.
#   irv-flow - HUNT GUARD : at boot, at logon and every 5 minutes, logged on or not (S4U), on battery too: keeps ops/hunt.py
#                           alive 24/7 (2026-10-06: a critical battery shut the laptop down at 22:15Z and an Interactive guard
#                           waited for the 11:23Z logon; 13.2 h of IF-02 sample lost, journal/gaps/2026-10-07.jsonl)
#   irv-flow - LOOP       : daily 05:20 local: seal, score forward captures, gate, read out, build the digest, push
#   irv-flow - MORNING    : daily 06:00 local: MR-01, the morning scan, after the LOOP and before board MORNING 07:10
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$vbs = Join-Path $env:USERPROFILE "ops\run-hidden.vbs"
$bash = "C:\Program Files\Git\bin\bash.exe"
$wsroot = "/" + $root.Substring(0, 1).ToLower() + ($root.Substring(2) -replace '\\', '/')   # no scriptblock -replace: PowerShell 5.1 pastes the block in as text

$guardArgs = "//B //Nologo `"$vbs`" `"powershell.exe`" -NoProfile -ExecutionPolicy Bypass -File `"$root\ops\hunt_guard.ps1`""
$loopArgs = "//B //Nologo `"$vbs`" `"$bash`" -lc `"cd $wsroot && python ops/loop.py > monitor/loop.log 2>&1`""

$guardAction = New-ScheduledTaskAction -Execute "wscript.exe" -Argument $guardArgs
$guardTriggers = @(
    (New-ScheduledTaskTrigger -AtStartup),
    (New-ScheduledTaskTrigger -AtLogOn),
    (New-ScheduledTaskTrigger -Once -At (Get-Date).Date -RepetitionInterval (New-TimeSpan -Minutes 5))
)
$s4u = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType S4U
$settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Hours 2) -StartWhenAvailable
$guardSettings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Hours 2) -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
Register-ScheduledTask -TaskName "irv-flow - HUNT GUARD" -Action $guardAction -Trigger $guardTriggers -Settings $guardSettings -Principal $s4u -Force | Out-Null

$loopAction = New-ScheduledTaskAction -Execute "wscript.exe" -Argument $loopArgs
$loopTrigger = New-ScheduledTaskTrigger -Daily -At 05:20
Register-ScheduledTask -TaskName "irv-flow - LOOP" -Action $loopAction -Trigger $loopTrigger -Settings $settings -Principal $s4u -Force | Out-Null

$morningArgs = "//B //Nologo `"$vbs`" `"$bash`" -lc `"cd $wsroot && python ops/morning.py build > monitor/morning.log 2>&1`""
$morningAction = New-ScheduledTaskAction -Execute "wscript.exe" -Argument $morningArgs
$morningTrigger = New-ScheduledTaskTrigger -Daily -At 06:00
$morningSettings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 30) -StartWhenAvailable -WakeToRun
Register-ScheduledTask -TaskName "irv-flow - MORNING" -Action $morningAction -Trigger $morningTrigger -Settings $morningSettings -Principal $s4u -Force | Out-Null
Export-ScheduledTask -TaskName "irv-flow - MORNING" | Out-File -Encoding utf8 (Join-Path $env:USERPROFILE "ops\task-backup\irv-flow - MORNING.xml")

Get-ScheduledTask -TaskName "irv-flow - *" | ForEach-Object { "{0,-24} {1}" -f $_.TaskName, $_.State }
