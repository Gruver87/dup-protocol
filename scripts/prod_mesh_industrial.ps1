# Industrial prod mesh gate: health -> failover -> signed tx -> optional soak.
param(
    [switch]$SkipFailover,
    [switch]$SkipTx,
    [switch]$RunSoak,
    [int]$SoakHours = 24,
    [int]$SoakIntervalSec = 300,
    [switch]$AllowNonStrictSoak
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Root = Split-Path -Parent $ScriptDir
Set-Location $Root

function Step([string]$Name, [scriptblock]$Action) {
    Write-Host "`n=== $Name ===" -ForegroundColor Cyan
    & $Action
    if (-not $?) {
        Write-Host "FAIL: $Name" -ForegroundColor Red
        exit 1
    }
    Write-Host "OK: $Name" -ForegroundColor Green
}

Step "health_watch (1 min)" {
    & (Join-Path $ScriptDir "health_watch.ps1") -ProdMesh -DurationMin 1 -IntervalSec 15
}

if (-not $SkipFailover) {
    Step "failover drill" {
        & (Join-Path $ScriptDir "prod_mesh_failover.ps1")
    }
}

if (-not $SkipTx) {
    Step "signed tx smoke" {
        python (Join-Path $ScriptDir "prod_signed_tx_smoke.py")
    }
}

if ($RunSoak) {
    if (-not $AllowNonStrictSoak) {
        Write-Host "REFUSE: -RunSoak starts soak_monitor at interval $SoakIntervalSec without -Strict." -ForegroundColor Red
        Write-Host "Pin libp2p STRICT is .\scripts\start_soak_prod_mesh_48h_strict.ps1 (interval 60)." -ForegroundColor Yellow
        Write-Host "Pass -AllowNonStrictSoak only for the old non-strict monitor." -ForegroundColor Yellow
        exit 1
    }
    Write-Host "`n=== soak monitor (${SoakHours}h) ===" -ForegroundColor Cyan
    Write-Host "  Running in foreground; use Ctrl+C to stop early." -ForegroundColor DarkGray
    Write-Host "  This is not the STRICT 48h pack." -ForegroundColor Yellow
    & (Join-Path $ScriptDir "soak_monitor.ps1") -ProdMesh -Hours $SoakHours -IntervalSec $SoakIntervalSec
    if (-not $?) { exit 1 }
    exit 0
}

Write-Host "`nOK: industrial prod mesh gate passed" -ForegroundColor Green
Write-Host "  48h STRICT, only if ordered: .\scripts\start_soak_prod_mesh_48h_strict.ps1" -ForegroundColor DarkGray
exit 0
