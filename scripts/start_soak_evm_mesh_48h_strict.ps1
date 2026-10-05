# STRICT 48h pin prod mesh AFTER EVM preflight.
# Runs docker → evm_pre_48h_harness → prepare_48h_soak → start_soak_prod_mesh_48h_strict.
# Distinct evidence from default 48h (IntervalSec=300, non-Strict).
#
#   .\scripts\start_soak_evm_mesh_48h_strict.ps1
#   .\scripts\start_soak_evm_mesh_48h_strict.ps1 -SkipRebuild
#   .\scripts\start_soak_evm_mesh_48h_strict.ps1 -PreflightOnly
#
# Honesty: NOT EVM-only 48h / not geth / not EIP-4844 / not mainnet.
param(
    [int]$Hours = 48,
    [int]$IntervalSec = 60,
    [int]$TipStagnantFailAfterSec = 3600,
    [string]$LogFile = "logs/soak_48h_evm_strict.log",
    [string]$ReportFile = "logs/soak_report_48h_evm_strict.json",
    [switch]$SkipRebuild,
    [switch]$SkipEvmHarness,
    [switch]$SkipPreflight,
    [switch]$PreflightOnly,
    [switch]$Force,
    [switch]$Foreground
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Root = Split-Path -Parent $ScriptDir
Set-Location $Root

Write-Host "STRICT 48h post-EVM pin prod mesh soak" -ForegroundColor Cyan
Write-Host "  hours=$Hours interval=${IntervalSec}s Strict + FullHarnessEvery=6 tip_stagnant=${TipStagnantFailAfterSec}s" -ForegroundColor DarkGray
Write-Host "  NOT default 48h / NOT EVM-only / NOT mainnet" -ForegroundColor DarkGray
Write-Host "  log=$LogFile report=$ReportFile" -ForegroundColor DarkGray

if ($SkipEvmHarness -and $SkipPreflight -and -not $Force) {
    Write-Host "FAIL: SkipEvmHarness+SkipPreflight requires -Force (refuse blind STRICT start)." -ForegroundColor Red
    exit 2
}

if (-not $SkipPreflight) {
    if ($SkipRebuild) {
        & (Join-Path $ScriptDir "docker_prod_3node.ps1") -SkipBuild -KeepVolumes
    } else {
        & (Join-Path $ScriptDir "docker_prod_3node.ps1") -KeepVolumes
    }
    if ($LASTEXITCODE -ne 0) {
        Write-Host "FAIL: docker_prod_3node. Do not start EVM STRICT soak." -ForegroundColor Red
        exit $LASTEXITCODE
    }
}

if (-not $SkipEvmHarness) {
    Write-Host "EVM pre-48h harness (labs + gate + probe + prod_evm_smoke)..." -ForegroundColor Cyan
    python scripts/evm_pre_48h_harness.py
    if ($LASTEXITCODE -ne 0) {
        Write-Host "FAIL: evm_pre_48h_harness. Do not start EVM STRICT soak." -ForegroundColor Red
        exit $LASTEXITCODE
    }
}

if (-not $SkipPreflight) {
    Write-Host "48h prepare (disk + healthy + miner harness)..." -ForegroundColor Cyan
    & (Join-Path $ScriptDir "prepare_48h_soak.ps1") -Hours $Hours -IntervalSec $IntervalSec
    if ($LASTEXITCODE -ne 0) {
        Write-Host "FAIL: prepare_48h_soak. Do not start EVM STRICT soak." -ForegroundColor Red
        exit $LASTEXITCODE
    }
}

if ($PreflightOnly) {
    Write-Host "RESULT: PASS preflight-only (EVM STRICT soak NOT started)" -ForegroundColor Green
    exit 0
}

$strictArgs = @{
    Hours = $Hours
    IntervalSec = $IntervalSec
    TipStagnantFailAfterSec = $TipStagnantFailAfterSec
    LogFile = $LogFile
    ReportFile = $ReportFile
    SkipRebuild = $true
    SkipPreflight = $true
    Foreground = $Foreground
}

& (Join-Path $ScriptDir "start_soak_prod_mesh_48h_strict.ps1") @strictArgs
exit $LASTEXITCODE
