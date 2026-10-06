# Preflight prod mesh before 48h soak - does NOT start the soak.
param(
    [int]$Hours = 48,
    [int]$IntervalSec = 300,
    # ADR 0020: default mesh is rust-libp2p (Noise). Require TLS only for the
    # alternate TCP+TLS profile (-RequireP2pTls), or when mesh JSON still has TLS on.
    [switch]$RequireP2pTls,
    [switch]$SkipP2pTlsCheck,
    [switch]$SkipBakedNeedle
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Root = Split-Path -Parent $ScriptDir
Set-Location $Root

function Fail-Step([string]$msg) {
    Write-Host "FAIL: $msg" -ForegroundColor Red
    Write-Host "Soak NOT started." -ForegroundColor Yellow
    exit 1
}

$wantTls = $false
if ($RequireP2pTls) { $wantTls = $true }
if ($SkipP2pTlsCheck) { $wantTls = $false }
# Auto: if mesh JSON is exclusive libp2p, never require mTLS.
try {
    $mesh1 = Join-Path $Root "docker\node.prod.mesh1.json"
    if (Test-Path $mesh1) {
        $j = Get-Content $mesh1 -Raw | ConvertFrom-Json
        if ($j.feature_libp2p -eq $true) { $wantTls = $false }
        elseif ($j.p2p_tls_enabled -eq $true -and $RequireP2pTls) { $wantTls = $true }
    }
} catch { }

Write-Host "Soak preflight (${Hours}h planned) - mesh must be up on :18180-:18182" -ForegroundColor Cyan
if ($wantTls) {
    Write-Host "  TLS check: ON (alternate TCP+TLS profile)" -ForegroundColor DarkGray
} else {
    Write-Host "  TLS check: OFF (ADR 0020 libp2p Noise mesh)" -ForegroundColor DarkGray
}
Write-Host "  after soak PASS: python scripts/stamp_release_evidence.py --require-soak-hours $Hours" -ForegroundColor DarkGray

if (-not $SkipBakedNeedle) {
    Write-Host "1) baked committed state_root needle (docker image)" -ForegroundColor Cyan
    $needleSrc = Join-Path $Root "scripts\check_baked_state_root.py"
    if (-not (Test-Path $needleSrc)) {
        Fail-Step "scripts/check_baked_state_root.py missing"
    }
    docker cp $needleSrc abs-prod-mesh3-node1-1:/tmp/check_baked_state_root.py | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Fail-Step "docker cp check_baked_state_root.py into node1"
    }
    $needleOut = docker exec -w /app -e PYTHONPATH=/app abs-prod-mesh3-node1-1 python /tmp/check_baked_state_root.py 2>&1
    Write-Host "  get_state_root=$($needleOut.ToString().Trim())" -ForegroundColor DarkGray
    if ($LASTEXITCODE -ne 0 -or $needleOut.ToString().Trim() -ne "COMMITTED_STATE_ROOT_OK") {
        Fail-Step "image missing committed state_root fix; rebuild: .\scripts\docker_prod_3node.ps1 -KeepVolumes"
    }
}

Write-Host "2) soak_preflight.py" -ForegroundColor Cyan
$argsList = @("scripts/soak_preflight.py", "--hours", $Hours, "--interval-sec", $IntervalSec)
if ($wantTls) { $argsList += "--require-p2p-tls" }
# Prefer wire probe when mesh is up (fail-closed soak honesty).
$argsList += "--require-wire-probe"
python @argsList
if ($LASTEXITCODE -ne 0) { Fail-Step "soak_preflight" }
exit 0
