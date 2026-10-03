# Registers the workstation tasks through ~/ops/run-hidden.vbs (no console pop-ups), same as the siblings.
#   irv-flow - HUNT GUARD : at logon and every 5 minutes, keeps ops/hunt.py alive 24/7
#   irv-flow - LOOP       : daily 05:20 local: seal, score forward captures, gate, read out, build the digest, push
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$vbs = Join-Path $env:USERPROFILE "ops\run-hidden.vbs"
$bash = "C:\Program Files\Git\bin\bash.exe"
$wsroot = "/" + $root.Substring(0, 1).ToLower() + ($root.Substring(2) -replace '\\', '/')   # no scriptblock -replace: PowerShell 5.1 pastes the block in as text

$guardArgs = "//B //Nologo `"$vbs`" `"powershell.exe`" -NoProfile -ExecutionPolicy Bypass -File `"$root\ops\hunt_guard.ps1`""
$loopArgs = "//B //Nologo `"$vbs`" `"$bash`" -lc `"cd $wsroot && python ops/loop.py > monitor/loop.log 2>&1`""

$guardAction = New-ScheduledTaskAction -Execute "wscript.exe" -Argument $guardArgs
$guardTriggers = @(
    (New-ScheduledTaskTrigger -AtLogOn),
    (New-ScheduledTaskTrigger -Once -At (Get-Date).Date -RepetitionInterval (New-TimeSpan -Minutes 5))
)
$settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Hours 2) -StartWhenAvailable
Register-ScheduledTask -TaskName "irv-flow - HUNT GUARD" -Action $guardAction -Trigger $guardTriggers -Settings $settings -Force | Out-Null

$loopAction = New-ScheduledTaskAction -Execute "wscript.exe" -Argument $loopArgs
$loopTrigger = New-ScheduledTaskTrigger -Daily -At 05:20
Register-ScheduledTask -TaskName "irv-flow - LOOP" -Action $loopAction -Trigger $loopTrigger -Settings $settings -Force | Out-Null

Get-ScheduledTask -TaskName "irv-flow - *" | ForEach-Object { "{0,-24} {1}" -f $_.TaskName, $_.State }
