# Prepare Experimental HEAD for EVM STRICT 48h re-soak (does NOT start 48h).
#
#   .\scripts\prepare_head_soak_evm_strict.ps1
#   .\scripts\prepare_head_soak_evm_strict.ps1 -SkipRebuild
#   .\scripts\prepare_head_soak_evm_strict.ps1 -SkipMidsoak
#
# Honesty: not soak PASS / not mainnet. After this PASS, operator starts:
#   .\scripts\start_soak_evm_mesh_48h_strict.ps1 -SkipRebuild
param(
    [switch]$SkipRebuild,
    [switch]$SkipMidsoak
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Root = Split-Path -Parent $ScriptDir
Set-Location $Root

Write-Host "HEAD EVM STRICT soak PREPARE (48h NOT started)" -ForegroundColor Cyan
Write-Host "  doc: docs/SOAK_HEAD_REVERIFY.md" -ForegroundColor DarkGray
Write-Host "  NOT claim PASS until start_soak_evm_mesh_48h_strict finishes 48h" -ForegroundColor DarkGray

$sha = "unknown"
try { $sha = (git rev-parse --short HEAD 2>$null).Trim() } catch { }
Write-Host "  tip=$sha" -ForegroundColor DarkGray

$dirty = git status --porcelain 2>$null
if ($dirty) {
    Write-Host "WARN: working tree dirty - soak tip claim should be clean commit" -ForegroundColor Yellow
    Write-Host $dirty
}

& (Join-Path $ScriptDir "stop_soak_monitors.ps1") -Force
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if (-not $SkipMidsoak) {
    Write-Host "=== midsoak honesty Quick ===" -ForegroundColor Cyan
    & (Join-Path $ScriptDir "verify_midsoak_honesty.ps1") -Quick
    if ($LASTEXITCODE -ne 0) {
        Write-Host "FAIL: midsoak honesty. Fix before soak." -ForegroundColor Red
        exit $LASTEXITCODE
    }
}

Write-Host "=== EVM STRICT PreflightOnly (docker + harness + prepare + probe) ===" -ForegroundColor Cyan
$pfArgs = @{
    PreflightOnly = $true
}
if ($SkipRebuild) { $pfArgs["SkipRebuild"] = $true }
& (Join-Path $ScriptDir "start_soak_evm_mesh_48h_strict.ps1") @pfArgs
if ($LASTEXITCODE -ne 0) {
    Write-Host "FAIL: EVM STRICT preflight. Do not start 48h." -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host ""
Write-Host "RESULT: PASS head soak PREPARE (48h NOT started)" -ForegroundColor Green
Write-Host "Next (operator):" -ForegroundColor Cyan
Write-Host "  .\scripts\start_soak_evm_mesh_48h_strict.ps1 -SkipRebuild" -ForegroundColor White
Write-Host "While ALIVE: no Max/full_audit/heavy pytest on this host (soak_guard)." -ForegroundColor Yellow
Write-Host "Doc: docs/SOAK_HEAD_REVERIFY.md" -ForegroundColor DarkGray
exit 0
