# Starts ops/hunt.py if no live hunter is heartbeating. Idempotent; safe to run every 5 minutes.
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$hb = Join-Path $root "monitor\hunt-heartbeat.json"
$alive = $false
if (Test-Path $hb) {
    $age = ((Get-Date) - (Get-Item $hb).LastWriteTime).TotalSeconds
    if ($age -lt 120) {
        try {
            $pid = (Get-Content $hb -Raw | ConvertFrom-Json).pid
            if ($pid -and (Get-Process -Id $pid -ErrorAction Stop).ProcessName -like "python*") { $alive = $true }
        } catch { $alive = $false }
    }
}
if (-not $alive) {
    New-Item -ItemType Directory -Force (Join-Path $root "monitor") | Out-Null
    $log = Join-Path $root "monitor\hunt-stdout.log"
    Start-Process -FilePath "python" -ArgumentList @((Join-Path $root "ops\hunt.py")) -WorkingDirectory $root -WindowStyle Hidden -RedirectStandardOutput $log -RedirectStandardError (Join-Path $root "monitor\hunt-stderr.log")
    Add-Content (Join-Path $root "monitor\hunt-guard.log") ("{0} started hunter" -f (Get-Date -Format o))
}
