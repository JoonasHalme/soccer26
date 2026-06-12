# Closing-odds capture wrapper for Windows Task Scheduler.
# Runs the quota-aware capture and appends a timestamped line to a log so you can
# audit what was captured (and what was skipped to save quota). Safe to run hourly:
# it only spends an Odds API request when a match is genuinely near kickoff.
#
# Register it to run hourly (see docs/closing-odds-runbook.md):
#   schtasks /Create /TN "soccer26-closing-odds" /SC HOURLY /F `
#     /TR "powershell -NoProfile -ExecutionPolicy Bypass -File `"C:\Users\PC-PUFFY\projects\soccer26\scripts\capture-closing.ps1`""

$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $PSScriptRoot          # ...\soccer26
$log  = Join-Path $repo "closing-capture.log"
$py   = "python"                                   # adjust if python isn't on PATH

Set-Location $repo
$stamp = (Get-Date).ToUniversalTime().ToString("yyyy-MM-dd HH:mm") + "Z"
try {
    $out = & $py "model\capture_closing.py" --within-hours 6 --min-refresh-mins 30 2>&1
    Add-Content -Path $log -Value "$stamp $out"
} catch {
    Add-Content -Path $log -Value "$stamp ERROR: $_"
}
