#Requires -Version 5.1
<#
.SYNOPSIS
  Operator checks for Experimental mid-soak honesty work (disk units + optional probe).

.DESCRIPTION
  Does NOT restart Docker / soak / rebuild images.
  Soak PASS is NEVER asserted by this script.

.EXAMPLE
  .\scripts\verify_midsoak_honesty.ps1
  .\scripts\verify_midsoak_honesty.ps1 -Quick
  .\scripts\verify_midsoak_honesty.ps1 -WithSoakStatus
  .\scripts\verify_midsoak_honesty.ps1 -WithMeshProbe
  .\scripts\verify_midsoak_honesty.ps1 -WithGate
  .\scripts\verify_midsoak_honesty.ps1 -All
#>

[CmdletBinding()]
param(
    [switch]$Quick,
    [switch]$WithSoakStatus,
    [switch]$WithMeshProbe,
    [switch]$WithGate,
    [switch]$All
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

if ($All) {
    $WithSoakStatus = $true
    $WithMeshProbe = $true
    $WithGate = $true
}

function Step([string]$Name) {
    Write-Host ""
    Write-Host ("=== " + $Name + " ===") -ForegroundColor Cyan
}

function Fail([string]$Msg) {
    Write-Host ("FAIL: " + $Msg) -ForegroundColor Red
    exit 1
}

Write-Host "DUP Protocol pin - mid-soak honesty verify" -ForegroundColor Green
Write-Host ("Root: " + $Root)
Write-Host "NOTE: units/needles only - soak containers NOT restarted" -ForegroundColor Yellow

# --- 1) Soak status (read-only) ------------------------------------------------
if ($WithSoakStatus -or $All) {
    Step "soak status (read-only)"
    $active = Join-Path $Root "logs\soak_active.json"
    if (Test-Path $active) {
        try {
            $j = Get-Content $active -Raw | ConvertFrom-Json
            Write-Host ("  pid:        " + $j.pid)
            Write-Host ("  started:    " + $j.started_at)
            Write-Host ("  hours:      " + $j.hours)
            Write-Host ("  strict:     " + $j.strict)
            Write-Host ("  image:      " + $j.image_id)
            Write-Host ("  report:     " + $j.report_file)
            $pidNum = [int]$j.pid
            $proc = Get-Process -Id $pidNum -ErrorAction SilentlyContinue
            if ($proc) {
                Write-Host ("  process:    ALIVE (" + $proc.ProcessName + ")") -ForegroundColor Green
            } else {
                Write-Host "  process:    NOT RUNNING (active json may be stale)" -ForegroundColor Yellow
            }
        } catch {
            Write-Host ("  warn: could not parse soak_active.json: " + $_) -ForegroundColor Yellow
        }
    } else {
        Write-Host "  no logs/soak_active.json (soak not marked active)" -ForegroundColor DarkGray
    }
    $log = Join-Path $Root "logs\soak_48h_evm_strict.log"
    if (Test-Path $log) {
        Write-Host "  last log lines:"
        Get-Content $log -Tail 4 | ForEach-Object { Write-Host ("    " + $_) }
    }
    Write-Host "  Soak claim: NOT asserted here." -ForegroundColor Yellow
}

# --- 2) Source needles (fast) --------------------------------------------------
Step "source needles (no invent gas/fee)"
$p2p = Get-Content -Raw (Join-Path $Root "network\p2p_node.py")
$http = Get-Content -Raw (Join-Path $Root "api\http.py")
$wire = Get-Content -Raw (Join-Path $Root "blockchain\mempool_wire.py")
$wallet = Get-Content -Raw (Join-Path $Root "crypto\wallet.py")

$needlesOk = $true
if ($p2p -notmatch "p2p_mempool_require_explicit_gas") {
    Write-Host "FAIL: p2p missing require_explicit_gas" -ForegroundColor Red
    $needlesOk = $false
}
if ($p2p -match 'int\(data\.get\("gas", 0\) or 0\) or 21_000') {
    Write-Host "FAIL: p2p still invents gas=21000" -ForegroundColor Red
    $needlesOk = $false
}
if ($http -notmatch "def _http_amount_abs") {
    Write-Host "FAIL: http missing _http_amount_abs" -ForegroundColor Red
    $needlesOk = $false
}
if ($http -notmatch "fee_gas_price_unset") {
    Write-Host "FAIL: http send missing fee_gas_price_unset" -ForegroundColor Red
    $needlesOk = $false
}
if ($http -notmatch "gas or gas_limit required for auto_sign") {
    Write-Host "FAIL: auto_sign missing explicit gas refuse" -ForegroundColor Red
    $needlesOk = $false
}
if ($wire -match "or 21_000") {
    Write-Host "FAIL: mempool_wire invents gas 21000" -ForegroundColor Red
    $needlesOk = $false
}
if ($wallet -match "int\(gas_limit\) != 21000") {
    Write-Host "FAIL: wallet still omits gas_limit=21000 from hash" -ForegroundColor Red
    $needlesOk = $false
}
if (-not $needlesOk) { Fail "source needles" }
Write-Host "OK: source needles" -ForegroundColor Green

# --- 3) Honesty units ----------------------------------------------------------
$Core = @(
    "tests/unit/test_exp_send_gas_amount_honesty.py",
    "tests/unit/test_exp_rest_amount_honesty.py",
    "tests/unit/test_no_invent_gas_21000.py",
    "tests/unit/test_exp_status_paint_honesty.py",
    "tests/unit/test_exp_hasher_zk_post_honesty.py",
    "tests/unit/test_exp_sqlite_gas_stake_honesty.py",
    "tests/unit/test_exp_consensus_stake_required.py",
    "tests/unit/test_exp_proposer_mev_zk_honesty.py",
    "tests/unit/test_exp_tx_from_dict_fee_honesty.py",
    "tests/unit/test_exp_p2p_builder_schema_honesty.py",
    "tests/unit/test_wallet_tx_gas_required.py",
    "tests/unit/test_ai_nft_marketplace_wave.py",
    "tests/unit/test_ai_sprout_harden.py",
    "tests/unit/test_exp_list_and_wallet_honesty.py",
    "tests/unit/test_wave_o_honesty_fixes.py",
    "tests/unit/test_wave_q_honesty_fixes.py",
    "tests/unit/test_wave_n_honesty_fixes.py",
    "tests/unit/test_wave_i_honesty_fixes.py",
    "tests/unit/test_tx_sender_identity_binding.py",
    "tests/unit/test_http_stake_satoshi.py",
    "tests/unit/test_honesty_satoshi_epoch_bridge.py"
)

$Extra = @(
    "tests/unit/test_wave_n_rpc_honesty.py",
    "tests/unit/test_tx_identity_binding.py",
    "tests/unit/test_bridge_inbound_amount_satoshi.py",
    "tests/unit/test_wallet_keystore.py",
    "tests/unit/test_jwt_secret_manager.py",
    "tests/unit/test_ws_events.py",
    "tests/unit/test_validator_loader.py"
)

$Wanted = if ($Quick) { $Core } else { $Core + $Extra }
$Present = @()
foreach ($f in $Wanted) {
    $full = Join-Path $Root $f
    if (Test-Path $full) { $Present += $f }
    else { Write-Host ("skip missing: " + $f) -ForegroundColor DarkYellow }
}

Step ("pytest honesty units (" + $Present.Count + ")")
& python -m pytest -q --tb=line @Present
if ($LASTEXITCODE -ne 0) { Fail ("pytest exit=" + $LASTEXITCODE) }
Write-Host "OK: pytest honesty units" -ForegroundColor Green

# --- 4) Optional gate / probe --------------------------------------------------
if ($WithGate) {
    Step "industrial_gate"
    & python scripts/industrial_gate.py
    if ($LASTEXITCODE -ne 0) {
        Write-Host "HINT: stale GENESIS_CEREMONY_HASH -> Remove-Item Env:GENESIS_CEREMONY_HASH" -ForegroundColor Yellow
        Fail ("industrial_gate exit=" + $LASTEXITCODE)
    }
    Write-Host "OK: industrial_gate" -ForegroundColor Green
}

if ($WithMeshProbe) {
    Step "probe_prod_mesh -Quick (read-only)"
    $probe = Join-Path $Root "scripts\probe_prod_mesh.ps1"
    if (-not (Test-Path $probe)) { Fail "probe_prod_mesh.ps1 missing" }
    & $probe -Quick
    if ($LASTEXITCODE -ne 0) { Fail ("mesh probe exit=" + $LASTEXITCODE) }
    Write-Host "OK: mesh probe" -ForegroundColor Green
}

Write-Host ""
Write-Host "RESULT: PASS mid-soak honesty verify" -ForegroundColor Green
Write-Host "Soak claim: NOT asserted. Mesh not restarted." -ForegroundColor Yellow
Write-Host ""
Write-Host "Shortcuts:" -ForegroundColor DarkGray
Write-Host "  .\scripts\verify_midsoak_honesty.ps1 -Quick" -ForegroundColor DarkGray
Write-Host "  .\scripts\verify_midsoak_honesty.ps1 -WithSoakStatus" -ForegroundColor DarkGray
Write-Host "  .\scripts\verify_midsoak_honesty.ps1 -All" -ForegroundColor DarkGray
Write-Host "  .\scripts\verify_audit_remediation_2026_10_02.ps1 -Quick" -ForegroundColor DarkGray
exit 0
