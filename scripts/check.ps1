# One-command quality gate: Python tests -> JS/TS tests -> site build.
# Stops at the first failure with a non-zero exit code. Run from anywhere:
#   powershell -NoProfile -ExecutionPolicy Bypass -File scripts/check.ps1
#
# Wire it as a pre-push / pre-commit step, or run it before shipping. (No git hooks
# are installed automatically — this is a manual/CI gate, since the project isn't a
# git repo yet.)

$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $PSScriptRoot
Set-Location $repo

function Step([string]$name, [scriptblock]$cmd) {
    Write-Host "`n=== $name ===" -ForegroundColor Cyan
    & $cmd
    if ($LASTEXITCODE -ne 0) {
        Write-Host "`nFAILED: $name (exit $LASTEXITCODE)" -ForegroundColor Red
        exit $LASTEXITCODE
    }
}

Step "pytest (model + pipeline)" { python -m pytest tests/ -q }
Step "vitest (site/src/lib)"     { npm --prefix site run test }
Step "astro build"               { npm --prefix site run build }

Write-Host "`nAll checks passed." -ForegroundColor Green
