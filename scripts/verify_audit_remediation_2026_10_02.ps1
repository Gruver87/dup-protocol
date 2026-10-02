#Requires -Version 5.1
# Operator verify for 2026-10-02 audit/honesty remediation.
# Unit + optional labs/probe. Does NOT restart Docker mesh / soak.
#
# Usage (Experimental or pin — run from that repo root):
#   .\scripts\verify_audit_remediation_2026_10_02.ps1
#   .\scripts\verify_audit_remediation_2026_10_02.ps1 -WithMeshProbe
#   .\scripts\verify_audit_remediation_2026_10_02.ps1 -WithPipAudit -WithNftLab -WithGateNeedles
#   .\scripts\verify_audit_remediation_2026_10_02.ps1 -Quick
#
# -Quick = core honesty units only (fast local check)

[CmdletBinding()]
param(
    [switch]$Quick,
    [switch]$WithMeshProbe,
    [switch]$WithPipAudit,
    [switch]$WithGateNeedles,
    [switch]$WithNftLab
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

function Step([string]$Name) {
    Write-Host ""
    Write-Host ("=== " + $Name + " ===") -ForegroundColor Cyan
}

function Fail([string]$Msg) {
    Write-Host ("FAIL: " + $Msg) -ForegroundColor Red
    exit 1
}

Write-Host "dup-protocol audit remediation verify 2026-10-02" -ForegroundColor Green
Write-Host ("Root: " + $Root)
Write-Host "NOTE: unit/lab only - soak untouched unless -WithMeshProbe" -ForegroundColor Yellow

$CoreHonesty = @(
    "tests/unit/test_honesty_satoshi_epoch_bridge.py",
    "tests/unit/test_bridge_inbound_amount_satoshi.py",
    "tests/unit/test_validator_loader.py",
    "tests/unit/test_ws_events.py",
    "tests/unit/test_tx_sender_identity_binding.py",
    "tests/unit/test_tx_identity_binding.py",
    "tests/unit/test_http_stake_satoshi.py",
    "tests/unit/test_jwt_secret_manager.py",
    "tests/unit/test_wallet_keystore.py",
    "tests/unit/test_wave_n_rpc_honesty.py"
)

$UnitFiles = @(
    "tests/unit/test_tx_sender_identity_binding.py",
    "tests/unit/test_wallet_keystore.py",
    "tests/unit/test_tx_identity_binding.py",
    "tests/unit/test_http_concurrency_and_mempool_identity.py",
    "tests/unit/test_http_stake_satoshi.py",
    "tests/unit/test_jwt_secret_manager.py",
    "tests/unit/test_chain_integrity.py",
    "tests/unit/test_mempool_batch_signatures.py",
    "tests/unit/test_eth_filters.py",
    "tests/unit/test_api_prod_auth.py",
    "tests/unit/test_wave_q_honesty_fixes.py",
    "tests/unit/test_honesty_satoshi_epoch_bridge.py",
    "tests/unit/test_validator_loader.py",
    "tests/unit/test_ws_events.py",
    "tests/unit/test_wave_n_rpc_honesty.py",
    "tests/unit/test_bridge_inbound_amount_satoshi.py"
)

$OptionalUnit = @(
    "tests/unit/test_adr0021_phase2_store.py",
    "tests/unit/test_wave46_nft_persistence.py",
    "tests/unit/test_mempool_get_for_block.py",
    "tests/unit/test_industrial_high_honesty.py",
    "tests/unit/test_v1354_evm_mempool_load.py",
    "tests/unit/test_evm_on_chain.py",
    "tests/unit/test_consensus_ports.py",
    "tests/unit/test_validator_stake_satoshi.py",
    "tests/unit/test_bridge_adr0010.py"
)

if ($Quick) {
    $Wanted = $CoreHonesty
} else {
    $Wanted = $UnitFiles + $OptionalUnit
}

$Present = @()
foreach ($f in $Wanted) {
    $full = Join-Path $Root $f
    if (Test-Path $full) {
        $Present += $f
    } else {
        Write-Host ("skip missing: " + $f) -ForegroundColor DarkYellow
    }
}

$n = $Present.Count
Step ("pytest audit remediation units - count " + $n)
& python -m pytest -q --tb=line @Present
if ($LASTEXITCODE -ne 0) { Fail ("pytest units exit=" + $LASTEXITCODE) }
Write-Host "OK: pytest units" -ForegroundColor Green

if ($WithNftLab) {
    $nft = Join-Path $Root "scripts/nft_lab.py"
    if (Test-Path $nft) {
        Step "nft_lab.py"
        & python scripts/nft_lab.py
        if ($LASTEXITCODE -ne 0) { Fail ("nft_lab exit=" + $LASTEXITCODE) }
        Write-Host "OK: nft_lab" -ForegroundColor Green
    }
}

if ($WithPipAudit) {
    Step "pip-audit requirements-runtime.txt"
    $req = Join-Path $Root "requirements-runtime.txt"
    if (-not (Test-Path $req)) { Fail "requirements-runtime.txt missing" }
    & python -m pip install -q pip-audit
    & pip-audit -r requirements-runtime.txt --desc off
    if ($LASTEXITCODE -ne 0) { Fail ("pip-audit exit=" + $LASTEXITCODE) }
    Write-Host "OK: pip-audit clean" -ForegroundColor Green

    Step "lock header sanity"
    $lock = Join-Path $Root "requirements-runtime.lock"
    if (-not (Test-Path $lock)) { Fail "requirements-runtime.lock missing" }
    $lockText = Get-Content $lock -Raw
    foreach ($needle in @("cryptography==", "PyJWT==", "--hash=sha256:")) {
        if ($lockText -notmatch [regex]::Escape($needle)) {
            Fail ("lock missing " + $needle)
        }
    }
    Write-Host "OK: hashed lock present" -ForegroundColor Green
}

if ($WithGateNeedles) {
    Step "industrial_gate"
    & python scripts/industrial_gate.py
    if ($LASTEXITCODE -ne 0) {
        Write-Host ""
        Write-Host "HINT: genesis_ceremony_hash_mismatch usually means a STALE shell pin." -ForegroundColor Yellow
        Write-Host "  Remove-Item Env:GENESIS_CEREMONY_HASH -ErrorAction SilentlyContinue" -ForegroundColor Yellow
        Write-Host "  .\scripts\pin_ceremony_hash.ps1" -ForegroundColor Yellow
        Write-Host "  # or trust data/ceremony_deploy.json (gate now prefers it when auto-detected)" -ForegroundColor Yellow
        Fail ("industrial_gate exit=" + $LASTEXITCODE)
    }
    Write-Host "OK: industrial_gate" -ForegroundColor Green
}

if ($WithMeshProbe) {
    Step "probe_prod_mesh Quick read-only"
    $probe = Join-Path $Root "scripts/probe_prod_mesh.ps1"
    if (-not (Test-Path $probe)) { Fail "probe_prod_mesh.ps1 missing" }
    & $probe -Quick
    if ($LASTEXITCODE -ne 0) { Fail ("mesh probe exit=" + $LASTEXITCODE) }
    Write-Host "OK: mesh probe" -ForegroundColor Green
}

Write-Host ""
Write-Host "RESULT: PASS audit remediation verify units" -ForegroundColor Green
Write-Host "Soak claim: NOT asserted by this script." -ForegroundColor Yellow
exit 0
