# Industrial pin — Phase 5 sprout / aux lab operator self-check (non-LR).
# Does NOT start soak. Does NOT flip prod feature_* flags. Does NOT enable bridge.
#
# Chains:
#   bridge OFF audit · oracle_lab · cross_shard_lab · nft_lab · ai_lab · ai_ops offline
#
# Usage (repo root):
#   .\scripts\verify_sprout_labs.ps1
#   .\scripts\verify_sprout_labs.ps1 -SkipGate
#   .\scripts\verify_sprout_labs.ps1 -SkipNft -SkipAi
param(
    [switch]$SkipGate,
    [switch]$SkipBridgeOff,
    [switch]$SkipOracle,
    [switch]$SkipCrossShard,
    [switch]$SkipNft,
    [switch]$SkipAi
)

$ErrorActionPreference = "Continue"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root
$fail = 0
$started = Get-Date
$steps = @()

function Invoke-Check([string]$Name, [scriptblock]$Command) {
    Write-Host ""
    Write-Host (">>> " + $Name) -ForegroundColor Yellow
    $global:LASTEXITCODE = 0
    & $Command
    $rc = $LASTEXITCODE
    if ($null -eq $rc) { $rc = 0 }
    $ok = ($rc -eq 0)
    $script:steps += @{ name = $Name; ok = $ok; exit_code = $rc }
    if ($ok) {
        Write-Host ("OK: " + $Name) -ForegroundColor Green
    } else {
        Write-Host ("FAIL: " + $Name + " (exit " + $rc + ")") -ForegroundColor Red
        $script:fail++
    }
}

Write-Host "SPROUT LABS verify (industrial pin)" -ForegroundColor Cyan
Write-Host "  NOT soak / NOT mainnet / NOT Long-Range / prod feature sprouts stay false" -ForegroundColor DarkGray

if (-not $SkipBridgeOff) {
    Invoke-Check "verify_bridge_off_lab" {
        & (Join-Path $Root "scripts\verify_bridge_off_lab.ps1")
    }
}

if (-not $SkipOracle) {
    $oracleArgs = @()
    if ($SkipGate) { $oracleArgs += "-SkipGate" }
    Invoke-Check "verify_oracle_lab" {
        & (Join-Path $Root "scripts\verify_oracle_lab.ps1") @oracleArgs
    }
}

if (-not $SkipCrossShard) {
    $csArgs = @()
    if ($SkipGate) { $csArgs += "-SkipGate" }
    Invoke-Check "verify_cross_shard_lab" {
        & (Join-Path $Root "scripts\verify_cross_shard_lab.ps1") @csArgs
    }
}

if (-not $SkipNft) {
    Invoke-Check "verify_nft_marketplace" {
        & (Join-Path $Root "scripts\verify_nft_marketplace.ps1") -SkipStaging
    }
}

if (-not $SkipAi) {
    Invoke-Check "ai_lab.py" {
        python scripts/ai_lab.py
    }
    Invoke-Check "ai_ops_anomaly offline" {
        python scripts/ai_ops_anomaly.py --offline-only
    }
}

if (-not $SkipGate) {
    Invoke-Check "industrial_gate sprout needles" {
        python -c @"
from pathlib import Path
t = (Path('scripts') / 'industrial_gate.py').read_text(encoding='utf-8')
for needle in ('oracle_lab.py', 'cross_shard_lab.py', 'nft_lab.py', 'ai_lab.py', 'verify_bridge_off_lab'):
    assert needle in t, needle
print('sprout_gate_needles_ok')
"@
    }
}

$elapsed = [math]::Round(((Get-Date) - $started).TotalSeconds, 1)
$passed = @($steps | Where-Object { $_.ok }).Count
$report = @{
    ok = ($fail -eq 0)
    phase = "pin-sprout-labs"
    passed = $passed
    total = $steps.Count
    fail_count = $fail
    elapsed_sec = $elapsed
    started = $started.ToString("o")
    steps = $steps
    honesty = @(
        "NOT soak",
        "NOT Long-Range",
        "NOT prod feature_* flip",
        "NOT bridge ON / NOT L1 cutover",
        "aux / ADR 0016 sprout labs only"
    )
}

$logDir = Join-Path $Root "logs"
if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir | Out-Null }
$reportPath = Join-Path $logDir "verify_sprout_labs.json"
($report | ConvertTo-Json -Depth 6) | Set-Content -Path $reportPath -Encoding utf8

Write-Host ""
if ($fail -eq 0) {
    Write-Host ("RESULT: PASS sprout labs verify (" + $passed + "/" + $steps.Count + ", " + $elapsed + "s)") -ForegroundColor Green
} else {
    Write-Host ("RESULT: FAIL sprout labs verify (" + $fail + " fail(s))") -ForegroundColor Red
}
Write-Host ("  report: " + $reportPath) -ForegroundColor DarkGray
if ($fail -gt 0) { exit 1 }
exit 0
