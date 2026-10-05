# Preflight prod mesh before 48h soak - does NOT start the soak.
param(
    [int]$Hours = 48,
    [int]$IntervalSec = 300,
    # ADR 0020: default mesh is rust-libp2p (Noise). Require TLS only for the
    # alternate TCP+TLS profile (-RequireP2pTls), or when mesh JSON still has TLS on.
    [switch]$RequireP2pTls,
    [switch]$SkipP2pTlsCheck
)

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Root = Split-Path -Parent $ScriptDir
Set-Location $Root

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
$argsList = @("scripts/soak_preflight.py", "--hours", $Hours, "--interval-sec", $IntervalSec)
if ($wantTls) { $argsList += "--require-p2p-tls" }
python @argsList
exit $LASTEXITCODE
