# Audit 90-day phase self-check (industrial pin).
# NOT soak / NOT mainnet / NOT industrial pin mesh by default.
#
# Usage (from repo root):
#   .\scripts\verify_audit_phase.ps1 -Phase A
#   .\scripts\verify_audit_phase.ps1 -Phase B
#   .\scripts\verify_audit_phase.ps1 -Phase C
#   .\scripts\verify_audit_phase.ps1 -Phase D
#   .\scripts\verify_audit_phase.ps1 -Phase E
#   .\scripts\verify_audit_phase.ps1 -Phase F
#   .\scripts\verify_audit_phase.ps1 -Phase G
#   .\scripts\verify_audit_phase.ps1 -Phase H
#   .\scripts\verify_audit_phase.ps1 -Phase All
#   .\scripts\verify_audit_phase.ps1 -Phase All -SkipGate
#
# Optional mesh (Phase E only, operator-owned):
#   .\scripts\verify_audit_phase.ps1 -Phase E -MeshProbe
param(
    [ValidateSet("A", "B", "C", "D", "E", "F", "G", "H", "All")]
    [string]$Phase = "All",
    [switch]$SkipGate,
    [switch]$MeshProbe
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root
$fail = 0

function Step([string]$Name) {
    Write-Host ""
    Write-Host "==> $Name" -ForegroundColor Cyan
}

function Run-Pytest([string]$Label, [string[]]$Paths) {
    Step $Label
    $existing = @()
    foreach ($p in $Paths) {
        if (Test-Path $p) {
            $existing += $p
        } else {
            Write-Host "SKIP missing: $p" -ForegroundColor Yellow
        }
    }
    if ($existing.Count -eq 0) {
        Write-Host "FAIL: no test paths for $Label" -ForegroundColor Red
        $script:fail++
        return
    }
    python -m pytest -q @existing --tb=line
    if ($LASTEXITCODE -ne 0) {
        Write-Host "FAIL: $Label" -ForegroundColor Red
        $script:fail++
    } else {
        Write-Host "OK: $Label" -ForegroundColor Green
    }
}

function Assert-FileContains([string]$Path, [string]$Needle, [string]$Label) {
    if (-not (Test-Path $Path)) {
        Write-Host "FAIL: missing file $Path ($Label)" -ForegroundColor Red
        $script:fail++
        return
    }
    $text = Get-Content -Raw -Path $Path
    if ($text -notlike ("*" + $Needle + "*")) {
        Write-Host "FAIL: $Label - needle not found in $Path" -ForegroundColor Red
        Write-Host "      expected: $Needle" -ForegroundColor DarkGray
        $script:fail++
    } else {
        Write-Host "OK: $Label" -ForegroundColor Green
    }
}

function Assert-FileExists([string]$Path, [string]$Label) {
    if (-not (Test-Path $Path)) {
        Write-Host "FAIL: $Label - missing $Path" -ForegroundColor Red
        $script:fail++
    } else {
        Write-Host "OK: $Label" -ForegroundColor Green
    }
}

function Invoke-IndustrialGate {
    if ($SkipGate) {
        Write-Host "SKIP: industrial_gate (-SkipGate)" -ForegroundColor Yellow
        return
    }
    Step "industrial_gate"
    # Mesh/docker scripts often leave TIP_SAFETY_ENFORCE / DEPLOYMENT_MODE in the
    # parent shell. Static gate must score JSON on disk, not ambient overrides.
    $savedGate = @{}
    foreach ($k in @(
            "TIP_SAFETY_ENFORCE", "TIP_SAFETY_SHADOW", "DEPLOYMENT_MODE",
            "ABS_REQUIRE_NATIVE_CRYPTO", "P2P_NATIVE_TRANSPORT",
            "FEATURE_LIBP2P", "FEATURE_LONG_RANGE",
            "EVM_CREATE2_EIP1014", "EVM_REQUIRE_DEPLOY_SALT", "BRIDGE_ENABLED"
        )) {
        $savedGate[$k] = [Environment]::GetEnvironmentVariable($k, "Process")
        Remove-Item "Env:$k" -ErrorAction SilentlyContinue
    }
    try {
        python scripts/industrial_gate.py
        if ($LASTEXITCODE -ne 0) {
            Write-Host "FAIL: industrial_gate" -ForegroundColor Red
            $script:fail++
        } else {
            Write-Host "OK: industrial_gate" -ForegroundColor Green
        }
    } finally {
        foreach ($k in $savedGate.Keys) {
            $old = $savedGate[$k]
            if ($null -eq $old) {
                Remove-Item "Env:$k" -ErrorAction SilentlyContinue
            } else {
                Set-Item -Path "Env:$k" -Value $old
            }
        }
    }
}

function Verify-PhaseA {
    Write-Host ""
    Write-Host "======== PHASE A - Honesty first ========" -ForegroundColor Magenta
    Run-Pytest "A unit: opcode map + ZK refuse + EVM runtime" @(
        "tests/unit/test_evm_opcode_map_honesty.py"
        "tests/unit/test_zk_proofs.py"
        "tests/unit/test_evm_runtime.py"
        "tests/unit/test_amount_units.py"
    )
    Step "A needles"
    Assert-FileContains "execution/evm_runtime.py" "opcode_map_honesty" "A1 opcode_map_honesty"
    Assert-FileContains "execution/evm_runtime.py" "yellow_paper_compatible" "A1 yellow_paper_compatible key"
    Assert-FileContains "features/zk.py" "zk_range_proof_not_implemented" "A2 ZK range refuse"
    Assert-FileContains "docs/sprouts/EVM_COMPAT_MATRIX.md" "Absolute-native" "A1 matrix Absolute-native"
}

function Verify-PhaseB {
    Write-Host ""
    Write-Host "======== PHASE B - Trust UX ========" -ForegroundColor Magenta
    Run-Pytest "B unit: admin JWT + auth honesty" @(
        "tests/unit/test_api_prod_auth.py"
    )
    Step "B needles"
    Assert-FileContains "api/http.py" "ABS_ALLOW_DEV_ADMIN_JWT" "B2 JWT mint env gate"
    Assert-FileContains "web/explorer/index.html" "DEMO" "B1 explorer DEMO badge surface"
    if (Test-Path "web/console/index.html") {
        Assert-FileContains "web/console/index.html" "DUP" "B console DUP brand"
    }
}

function Verify-PhaseC {
    Write-Host ""
    Write-Host "======== PHASE C - Money surface ========" -ForegroundColor Magenta
    Run-Pytest "C unit: satoshi ports (shard/bridge/wire)" @(
        "tests/unit/test_cross_shard_coordinator.py"
        "tests/unit/test_live_resharding.py"
        "tests/unit/test_bridge_adr0010.py"
        "tests/unit/test_adr0021_wire_satoshi_cutover.py"
        "tests/unit/test_amount_units.py"
        "tests/unit/test_p0_slash_satoshi_ledger.py"
    )
    Step "C needles"
    Assert-FileContains "consensus/cross_shard_coordinator.py" "balance_satoshi_required" "C2 balance_satoshi_required"
    Assert-FileContains "bridge/ports.py" "amount_satoshi" "C3 InboundEnvelope.amount_satoshi"
    Assert-FileContains "network/p2p_node.py" "stake_satoshi_required" "C4 stake_satoshi_required"
}

function Verify-PhaseD {
    Write-Host ""
    Write-Host "======== PHASE D - Harden ========" -ForegroundColor Magenta
    Run-Pytest "D unit: consensus/EVM/legacy quarantine/logging" @(
        "tests/unit/test_consensus_unified.py"
        "tests/unit/test_hybrid_network_consensus.py"
        "tests/unit/test_evm_runtime.py"
        "tests/unit/test_evm_prod_deploy_salt.py"
        "tests/unit/test_p2p_message_handler.py"
        "tests/unit/test_sync_manager_fail_closed.py"
        "tests/unit/test_silent_except_honesty.py"
        "tests/unit/test_wave34_cleanup.py"
        "tests/unit/test_wave35_p2p_bridge.py"
        "tests/unit/test_v1361_apply_writeback.py"
    )
    Step "D needles"
    Assert-FileContains "execution/evm_adapter.py" "evm_native_writeback_required" "D1 writeback refuse"
    Assert-FileContains "runtime/config.py" 'return "unified"' "D2 auto->unified"
    Assert-FileExists "network/legacy_test_p2p/message_handler.py" "D3 legacy_test_p2p"
    Assert-FileExists "network/sync/legacy_test_fast_sync.py" "D3 legacy_test_fast_sync"
    Assert-FileContains "execution/evm_runtime.py" '"status": "partial"' "D4 CREATE2 partial status present"
    Assert-FileContains "api/http.py" "prod without a P2P object is not ready" "D5 health/ready p2p None"
    $adapterPrints = Select-String -Path "consensus/adapter.py" -Pattern "print(" -SimpleMatch -ErrorAction SilentlyContinue
    $syncPrints = Select-String -Path "sync/sync_engine.py" -Pattern "print(" -SimpleMatch -ErrorAction SilentlyContinue
    if ($adapterPrints -or $syncPrints) {
        Write-Host "FAIL: D6 print() still present on consensus/sync hot paths" -ForegroundColor Red
        $script:fail++
    } else {
        Write-Host "OK: D6 no print() on consensus/adapter + sync/sync_engine" -ForegroundColor Green
    }
}

function Verify-PhaseE {
    Write-Host ""
    Write-Host "======== PHASE E - Org / show (docs + optional mesh) ========" -ForegroundColor Magenta
    Step "E docs exist"
    Assert-FileExists "docs/DEMO_RUNBOOK.md" "E1 DEMO_RUNBOOK"
    Assert-FileExists "docs/CEREMONY_DRY_RUN.md" "E2 CEREMONY_DRY_RUN"
    Assert-FileExists "docs/INVESTOR_DECK_SKELETON.md" "E3 INVESTOR_DECK_SKELETON"
    Assert-FileContains "docs/DEMO_RUNBOOK.md" "probe_prod_mesh" "E1 demo mentions probe"
    Assert-FileContains "docs/CEREMONY_DRY_RUN.md" "ceremony_evidence_suite" "E2 ceremony suite"
    Assert-FileContains "docs/INVESTOR_DECK_SKELETON.md" "DILIGENCE_BRIEF" "E3 deck cites diligence"
    if ($MeshProbe) {
        Step "E mesh probe (operator) - NOT soak"
        if (-not (Test-Path "scripts/probe_prod_mesh.ps1")) {
            Write-Host "FAIL: probe_prod_mesh.ps1 missing" -ForegroundColor Red
            $script:fail++
        } else {
            $probeOk = $false
            foreach ($attempt in 1..4) {
                Write-Host ("probe attempt {0}/4 ..." -f $attempt) -ForegroundColor DarkGray
                & ".\scripts\probe_prod_mesh.ps1" -Quick
                if ($LASTEXITCODE -eq 0) {
                    $probeOk = $true
                    break
                }
                if ($attempt -lt 4) {
                    Start-Sleep -Seconds 8
                }
            }
            if (-not $probeOk) {
                Write-Host "FAIL: mesh probe (node still unreachable after retries)" -ForegroundColor Red
                Write-Host "  Bring mesh up first:" -ForegroundColor DarkGray
                Write-Host "  .\scripts\docker_prod_3node.ps1 -SkipBuild -KeepVolumes" -ForegroundColor DarkGray
                $script:fail++
            } else {
                Write-Host "OK: mesh probe" -ForegroundColor Green
            }
        }
    } else {
        Write-Host "SKIP: mesh probe (pass -MeshProbe to run; soak stays shelf)" -ForegroundColor Yellow
    }
}

function Verify-PhaseF {
    Write-Host ""
    Write-Host "======== PHASE F1 - Absolute-VM ADR ========" -ForegroundColor Magenta
    Run-Pytest "F unit: opcode honesty still Absolute-native" @(
        "tests/unit/test_evm_opcode_map_honesty.py"
        "tests/unit/test_evm_runtime.py"
    )
    Step "F needles"
    Assert-FileExists "docs/adr/0023-absolute-vm-opcode-map.md" "F1 ADR 0023 file"
    Assert-FileContains "docs/adr/0023-absolute-vm-opcode-map.md" "Absolute-VM" "F1 Absolute-VM decision"
    Assert-FileContains "docs/adr/README.md" "0023-absolute-vm-opcode-map" "F1 ADR index"
    Assert-FileContains "execution/evm_runtime.py" "absolute_native" "F1 runtime absolute_native"
    Assert-FileContains "docs/sprouts/EVM_COMPAT_MATRIX.md" "Remap to Yellow Paper is a breaking Phase F ADR" "F1 matrix no silent remap"
}

function Verify-PhaseG {
    Write-Host ""
    Write-Host "======== PHASE G - Refuse float money fallback ========" -ForegroundColor Magenta
    Run-Pytest "G unit: satoshi refuse float (EVM/sprouts/apply)" @(
        "tests/unit/test_evm_satoshi_refuse_float.py"
        "tests/unit/test_apply_store_delta_satoshi.py"
        "tests/unit/test_nft_uow.py"
        "tests/unit/test_cross_shard_coordinator.py"
        "tests/unit/test_evm_host_value.py"
    )
    Step "G needles"
    Assert-FileContains "runtime/amount.py" "allow_float_fallback" "G apply_store_delta allow_float_fallback"
    Assert-FileContains "execution/evm_adapter.py" "allow_float_fallback=False" "G EVM refuse float"
    Assert-FileContains "execution/evm_adapter.py" "satoshi_store_required" "G EVM satoshi_store_required"
    Assert-FileContains "features/nft.py" "allow_float_fallback=False" "G NFT refuse float"
    Assert-FileContains "features/plasma.py" "allow_float_fallback=False" "G plasma refuse float"
    Assert-FileContains "features/lightning.py" "allow_float_fallback=False" "G lightning refuse float"
    Assert-FileContains "features/crypto_will.py" "allow_float_fallback=False" "G crypto_will refuse float"
    Assert-FileContains "dynamic_sharding.py" "allow_float_fallback=False" "G sharding refuse float"
    Assert-FileContains "api/http.py" "satoshi_store_required" "G faucet refuse float"
    Assert-FileContains "consensus/cross_shard_coordinator.py" "allow_float_fallback=False" "G cross-shard refuse float"
    Assert-FileContains "features/wasm_vm.py" "allow_float_fallback=False" "G wasm fee refuse float"
    Assert-FileContains "features/ai_manager.py" "allow_float_fallback=False" "G AI fee refuse float"
    Assert-FileContains "bridge/abs_bridge.py" "satoshi_store_required" "G bridge refuse float fallback"
    Assert-FileContains "runtime/devnet_validators.py" "allow_float_fallback=False" "G devnet validators satoshi fund"
    Assert-FileContains "core/components/state_service.py" "satoshi_store_required_credit" "G StateService credit refuse float"
    Assert-FileContains "main.py" "satoshi_store_required_dev_signer_fund" "G dev signer refuse float fund"
    Assert-FileContains "storage/database.py" "stake_satoshi" "G validators stake_satoshi"
    Assert-FileContains "storage/database.py" "_backfill_validator_stake_satoshi" "G validators stake backfill"
    Assert-FileContains "storage/database.py" "_backfill_bridge_amount_satoshi" "G bridge amount_satoshi backfill"
    Assert-FileContains "storage/database.py" "amount_satoshi" "G bridge amount_satoshi"
    Assert-FileContains "storage/database.py" "_backfill_feature_amount_satoshi" "G feature sprout satoshi backfill"
    Assert-FileContains "storage/database.py" "capacity_satoshi" "G lightning capacity_satoshi"
    Assert-FileContains "storage/database.py" "price_satoshi" "G NFT price_satoshi"
    Assert-FileContains "storage/database.py" "balance1_satoshi" "G lightning channel_state balance1_satoshi"
    Assert-FileContains "storage/database.py" "total_profit_satoshi" "G AI total_profit_satoshi"
    Assert-FileContains "storage/database.py" "profit_satoshi" "G MEV profit_satoshi"
    Assert-FileContains "storage/rocks_store.py" "price_satoshi" "G rocks NFT price_satoshi"
    Assert-FileContains "storage/database.py" "_backfill_burn_satoshi" "G burn satoshi backfill"
    Assert-FileContains "storage/database.py" "burned_amount_satoshi" "G burn burned_amount_satoshi"
    Assert-FileContains "storage/database.py" '("blocks", "total_burned_satoshi"' "G blocks total_burned_satoshi"
    Assert-FileContains "storage/database.py" '("block_proposer_audit", "total_burned_satoshi"' "G proposer_audit total_burned_satoshi"
    Assert-FileContains "storage/database.py" "_backfill_tx_money_satoshi" "G tx money satoshi backfill"
    Assert-FileContains "storage/database.py" '("transactions", "value_satoshi"' "G transactions value_satoshi"
    Assert-FileContains "storage/database.py" '("tx_receipts", "fee_satoshi"' "G tx_receipts fee_satoshi"
    Assert-FileContains "storage/rocks_store.py" "total_burned_satoshi" "G rocks burn total_burned_satoshi"
    Assert-FileContains "storage/rocks_store.py" "total_burned_scope" "G rocks proposer_detail burn scope honesty"
    Run-Pytest "G unit: pool spend + wasm fee + state credit + stake/bridge/feature satoshi" @(
        "tests/unit/test_devnet_pool_spend.py"
        "tests/unit/test_wave42_wasm_relayer.py"
        "tests/unit/test_state_service_satoshi_credit.py"
        "tests/unit/test_validator_stake_satoshi.py"
        "tests/unit/test_bridge_amount_satoshi.py"
        "tests/unit/test_feature_amount_satoshi.py"
        "tests/unit/test_burn_satoshi.py"
        "tests/unit/test_tx_money_satoshi.py"
        "tests/unit/test_prod_bridge_lock.py"
        "tests/unit/test_bridge_confirm_pending.py"
    )
}

function Verify-PhaseH {
    Write-Host ""
    Write-Host "======== PHASE H - External audit engagement prep ========" -ForegroundColor Magenta
    Write-Host "  NOT firm audit PASS / NOT soak" -ForegroundColor DarkGray
    Step "H engagement prep script"
    if (-not (Test-Path "scripts/verify_audit_engagement_prep.ps1")) {
        Write-Host "FAIL: verify_audit_engagement_prep.ps1 missing" -ForegroundColor Red
        $script:fail++
        return
    }
    & ".\scripts\verify_audit_engagement_prep.ps1"
    if ($LASTEXITCODE -ne 0) {
        Write-Host "FAIL: engagement prep" -ForegroundColor Red
        $script:fail++
    } else {
        Write-Host "OK: engagement prep" -ForegroundColor Green
    }
}

Write-Host "AUDIT 90D phase self-check (dup-protocol-experimental)" -ForegroundColor Cyan
Write-Host "  Phase=$Phase  SkipGate=$SkipGate  MeshProbe=$MeshProbe" -ForegroundColor DarkGray
Write-Host "  NOT soak / NOT mainnet claim" -ForegroundColor DarkGray

$phases = if ($Phase -eq "All") { @("A", "B", "C", "D", "E", "F", "G", "H") } else { @($Phase) }
foreach ($p in $phases) {
    switch ($p) {
        "A" { Verify-PhaseA }
        "B" { Verify-PhaseB }
        "C" { Verify-PhaseC }
        "D" { Verify-PhaseD }
        "E" { Verify-PhaseE }
        "F" { Verify-PhaseF }
        "G" { Verify-PhaseG }
        "H" { Verify-PhaseH }
    }
}

Invoke-IndustrialGate

Write-Host ""
if ($fail -gt 0) {
    Write-Host ("RESULT: FAIL ({0} checks)" -f $fail) -ForegroundColor Red
    exit 1
}
Write-Host "RESULT: PASS" -ForegroundColor Green
Write-Host "  Soak not claimed. Mesh only if -MeshProbe was used." -ForegroundColor DarkGray
exit 0
