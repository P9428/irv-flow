# Registers the two workstation tasks through ops/run-hidden.vbs (no console pop-ups).
#   irv-flow - HUNT GUARD : every 5 minutes, and at logon, keeps ops/hunt.py alive 24/7
#   irv-flow - LOOP       : daily 05:20 local, seals, scores, gates, reads out
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$vbs = Join-Path $env:USERPROFILE "ops\run-hidden.vbs"
$guard = "wscript.exe `"$vbs`" `"powershell -NoProfile -ExecutionPolicy Bypass -File `"`"$root\ops\hunt_guard.ps1`"`"`""
$loop = "wscript.exe `"$vbs`" `"python `"`"$root\ops\loop.py`"`" > `"`"$root\monitor\loop.log`"`" 2>&1`""
schtasks /Create /F /TN "irv-flow - HUNT GUARD" /SC MINUTE /MO 5 /TR $guard /RL LIMITED | Out-Null
schtasks /Create /F /TN "irv-flow - HUNT GUARD (logon)" /SC ONLOGON /TR $guard /RL LIMITED | Out-Null
schtasks /Create /F /TN "irv-flow - LOOP" /SC DAILY /ST 05:20 /TR $loop /RL LIMITED | Out-Null
schtasks /Query /TN "irv-flow - HUNT GUARD" /FO LIST | Select-String "TaskName|Status|Next Run"
schtasks /Query /TN "irv-flow - LOOP" /FO LIST | Select-String "TaskName|Status|Next Run"
