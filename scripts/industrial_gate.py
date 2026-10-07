#!/usr/bin/env python3
"""Industrial readiness gate — code-level checks without external audit blockers."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def _check_p2p_hardening() -> tuple[list[str], list[str]]:
    """Static P2P industrial surface checks (no live mesh required)."""
    errors: list[str] = []
    warnings: list[str] = []
    from network.p2p_node import (
        ALLOWED_WIRE_TYPES,
        DEFAULT_MAX_P2P_LINE_BYTES,
        P2PNode,
        RATE_LIMIT_EXEMPT_TYPES,
    )
    from runtime.config import Config

    required_types = {
        "handshake",
        "handshake_ack",
        "new_block",
        "block",
        "blocks",
        "status",
        "state_root_request",
        "state_root_response",
    }
    missing = required_types - ALLOWED_WIRE_TYPES
    if missing:
        errors.append(f"P2P allowlist missing types: {sorted(missing)}")
    required_exempt = {
        "new_block",
        "get_block",
        "get_blocks",
        "block",
        "blocks",
        "status",
        "get_mempool",
        "mempool",
    }
    missing_exempt = required_exempt - RATE_LIMIT_EXEMPT_TYPES
    if missing_exempt:
        errors.append(f"P2P rate-limit exempt set missing sync types: {sorted(missing_exempt)}")
    # v1.3.143: gossip new_tx must use primary rate budget (not sync exempt).
    if "new_tx" in RATE_LIMIT_EXEMPT_TYPES:
        errors.append("P2P RATE_LIMIT_EXEMPT_TYPES must not include new_tx (v1.3.143)")

    cfg = Config()
    if int(getattr(cfg, "p2p_max_message_bytes", 0) or 0) < DEFAULT_MAX_P2P_LINE_BYTES // 2:
        warnings.append("p2p_max_message_bytes lower than industrial default")
    if int(getattr(cfg, "p2p_max_messages_per_sec", 0) or 0) <= 0:
        warnings.append("p2p_max_messages_per_sec disabled (0)")
    for attr in ("get_p2p_security_status", "_maintenance_loop", "_strike_peer_sync"):
        if not hasattr(P2PNode, attr):
            errors.append(f"P2PNode missing {attr}")
    import inspect

    p2p_src = inspect.getsource(P2PNode)
    for needle in ("shape_rejects_total", "_shape_reject_counts", "WireReject"):
        if needle not in p2p_src:
            errors.append(f"P2PNode missing industrial observability: {needle}")
    p2p_mod = (ROOT / "network" / "p2p_node.py").read_text(encoding="utf-8")
    for needle in (
        "class WireReject",
        "bad_wire_line",
        "p2p_line_too_large",
        "rate_limit_exceeded",
        "recv_error",
        "_housekeeping_payload_ok",
        "peer_send_fail",
        "mid_session_handshake",
        "_start_libp2p_listen",
        "_libp2p_admit_raw_frame",
        "send_abs_wire",
        "ADR0020_experimental_libp2p_industrial_mesh",
        "no TCP+TLS fallback",
    ):
        if needle not in p2p_mod:
            errors.append(f"p2p_node.py missing wire-reject surface: {needle}")
    http_src = (ROOT / "api" / "http.py").read_text(encoding="utf-8")
    for needle in (
        "shape_rejects_total",
        "rate_limit_drops",
        "_status_p2p_hardening_snapshot",
        "libp2p_rust_backend",
    ):
        if needle not in http_src:
            errors.append(f"api/http.py missing status honesty surface: {needle}")
    metrics_src = (ROOT / "observability" / "metrics.py").read_text(encoding="utf-8")
    for needle in (
        "abs_p2p_shape_rejects_total",
        "abs_p2p_shape_rejects",
        "abs_p2p_handshake_rejects_total",
        "abs_p2p_active_bans",
        "abs_p2p_rate_limit_drops_total",
        "abs_p2p_peer_send_fail_total",
        "abs_p2p_ops_errors",
        "abs_p2p_attestation_local_fail_total",
        "abs_p2p_peer_tx_reject_total",
        "abs_rocksdb_column_families",
        "abs_db_engine",
        "abs_state_consistent",
        "abs_sync_wire_probe_ok",
        "abs_sync_wire_probe_probed",
        "abs_p2p_under_mesh",
        "abs_p2p_sync_status",
    ):
        if needle not in metrics_src:
            errors.append(f"metrics.py missing Prometheus series: {needle}")
    p2p_mod = (ROOT / "network" / "p2p_node.py").read_text(encoding="utf-8")
    peer_mgr_mod = ""
    peer_mgr_path = ROOT / "network" / "peer_manager.py"
    if peer_mgr_path.is_file():
        peer_mgr_mod = peer_mgr_path.read_text(encoding="utf-8")
    p2p_surface = p2p_mod + "\n" + peer_mgr_mod
    for needle in (
        "maintenance_loop_fail",
        "catch_up_loop_fail",
        "strike %s/%s",
        "peer_tx_reject",
        "bad_peer_tx",
        "import_block_fail",
        "sync_fail",
        "discovery_loop_fail",
    ):
        if needle not in p2p_surface:
            errors.append(f"p2p_node.py missing industrial surface: {needle}")
    alerts_src = (ROOT / "deploy" / "prometheus" / "alerts.yml").read_text(encoding="utf-8")
    for needle in (
        "abs_p2p_shape_rejects_total",
        "abs_p2p_rate_limit_drops_total",
        "abs_p2p_peer_send_fail_total",
        "abs_p2p_handshake_rejects_total",
        "abs_p2p_ops_errors",
        "abs_p2p_attestation_local_fail_total",
        "abs_p2p_peer_tx_reject_total",
        "abs_rocksdb_block_cache_mb",
        "abs_state_consistent",
        "abs_sync_wire_probe_ok",
        "abs_p2p_under_mesh",
        "AbsoluteP2PUnderMesh",
    ):
        if needle not in alerts_src:
            errors.append(f"prometheus alerts.yml missing rule surface: {needle}")
    dash_src = (ROOT / "deploy" / "grafana" / "dashboard.json").read_text(encoding="utf-8")
    for needle in (
        "abs_p2p_peer_send_fail_total",
        "abs_p2p_ops_errors",
        "mid_session_handshake",
        "abs_p2p_attestation_local_fail_total",
        "abs_p2p_peer_tx_reject_total",
        "abs_state_consistent",
        "abs_sync_wire_probe_ok",
        # Exp→pin ops: RocksDB live gauges + under-mesh + mempool demote panels
        "abs_rocksdb_running_compactions",
        "abs_rocksdb_running_flushes",
        "abs_rocksdb_estimate_num_keys",
        "abs_p2p_under_mesh",
        "abs_rocksdb_native_pack_fallbacks",
        "abs_mempool_store_demoted",
        "abs_mempool_store_demote_count",
        "abs_mempool_store_backend",
    ):
        if needle not in dash_src:
            errors.append(f"grafana dashboard.json missing panel surface: {needle}")
    http_proposer = (ROOT / "api" / "http.py").read_text(encoding="utf-8")
    if "hasattr(db, \"count_proposer_audit\")" not in http_proposer:
        errors.append(
            "proposers stats/history must hasattr-guard count_proposer_audit"
        )
    try:
        from network import p2p_tls  # noqa: F401
    except ImportError as exc:
        errors.append(f"network.p2p_tls import failed: {exc}")
    # Exp→pin ops: market snapshot (TLS allowlist) + secure UI static + soak needles.
    if not (ROOT / "api" / "market_feed.py").is_file():
        errors.append("api/market_feed.py missing (ops market snapshot)")
    else:
        mf = (ROOT / "api" / "market_feed.py").read_text(encoding="utf-8")
        if "api.coingecko.com" not in mf or "create_default_context" not in mf:
            errors.append("market_feed must allowlist CoinGecko and verify TLS")
    http_static = (ROOT / "api" / "http.py").read_text(encoding="utf-8")
    if "/market/snapshot" not in http_static:
        errors.append("http.py must expose GET /market/snapshot")
    if "_resolve_web_static" not in http_static:
        errors.append("http.py must resolve web/console static safely")
    if "Content-Security-Policy" not in http_static or "_WEB_CSP" not in http_static:
        errors.append("http.py must emit CSP for UI static")
    if not (ROOT / "scripts" / "check_mesh_catchup.py").is_file():
        errors.append("scripts/check_mesh_catchup.py missing (live catch-up honesty)")
    else:
        catchup_py = (ROOT / "scripts" / "check_mesh_catchup.py").read_text(
            encoding="utf-8"
        )
        if "/p2p/topology" not in catchup_py or 'p2p.get("topology_healthy")' in catchup_py:
            errors.append(
                "check_mesh_catchup must read topology_healthy from GET /p2p/topology, not /status"
            )
    if not (ROOT / "scripts" / "check_baked_state_root.py").is_file():
        errors.append("scripts/check_baked_state_root.py missing")
    else:
        baked_py = (ROOT / "scripts" / "check_baked_state_root.py").read_text(
            encoding="utf-8"
        )
        if "Last committed canonical root" not in baked_py:
            errors.append(
                "check_baked_state_root.py must inspect get_state_root committed-root docstring"
            )
    prep48 = (ROOT / "scripts" / "prepare_48h_soak.ps1").read_text(encoding="utf-8")
    if "COMMITTED_STATE_ROOT_OK" not in prep48:
        errors.append(
            "prepare_48h_soak must exact-match COMMITTED_STATE_ROOT_OK (not substring OK)"
        )
    if "docker cp" not in prep48 or "check_baked_state_root.py" not in prep48:
        errors.append(
            "prepare_48h_soak must docker-cp check_baked_state_root.py into the running image"
        )
    if "--require-wire-probe" not in prep48:
        errors.append("prepare_48h_soak must pass --require-wire-probe to soak_preflight")
    if "--require-libp2p" not in prep48:
        errors.append(
            "prepare_48h_soak must pass --require-libp2p for ADR 0020 libp2p mesh"
        )
    if "check_mesh_catchup" not in prep48 or "soak_48h_prep.json" not in prep48:
        errors.append(
            "prepare_48h_soak must run check_mesh_catchup and write logs/soak_48h_prep.json"
        )
    if "MinFreeGb" not in prep48 or "stop_soak_monitors" not in prep48:
        errors.append(
            "prepare_48h_soak must check disk free and stop leftover soak monitors"
        )
    stop_sm = (ROOT / "scripts" / "stop_soak_monitors.ps1").read_text(encoding="utf-8")
    if "mempool_validation_sidecar" not in stop_sm or "health_watch" not in stop_sm:
        errors.append(
            "stop_soak_monitors must also kill health_watch + mempool_validation_sidecar"
        )
    if "selfPid" not in stop_sm and "ProcessId=$selfPid" not in stop_sm:
        errors.append("stop_soak_monitors must exclude self/parent PID (no self-kill)")
    cs_py = (ROOT / "scripts" / "check_secrets.py").read_text(encoding="utf-8")
    if 'startswith("<")' not in cs_py or 'endswith(">")' not in cs_py:
        errors.append("check_secrets must treat <angle-bracket> tokens as placeholders")
    soak_st = (ROOT / "scripts" / "soak_status.ps1").read_text(encoding="utf-8")
    if "ALIVE pid=" not in soak_st or "soak_*h*.log" not in soak_st:
        errors.append("soak_status must report monitor ALIVE and glob soak_*h*.log")
    shard_ps1 = (ROOT / "scripts" / "start_shard_devnet.ps1").read_text(encoding="utf-8")
    if "Restore-LabEnvPin" not in shard_ps1 or "DEPLOYMENT_MODE" not in shard_ps1:
        errors.append(
            "start_shard_devnet must pin DEPLOYMENT_MODE=dev and restore ambient env"
        )
    for rel in (
        "scripts/verify_audit_phase.ps1",
        "scripts/verify_audit_90d_all.ps1",
        "scripts/verify_audit_engagement_prep.ps1",
        "scripts/start_pre48h_maxload_2h.ps1",
        "docs/DILIGENCE_BRIEF.md",
        "docs/EXTERNAL_AUDIT_ENGAGEMENT.md",
        "docs/adr/0023-absolute-vm-opcode-map.md",
    ):
        if not (ROOT / rel).is_file():
            errors.append(f"missing firm/ops surface: {rel}")
    dil = (ROOT / "docs" / "DILIGENCE_BRIEF.md").read_text(encoding="utf-8")
    if "3c801b87" in dil or "lp2pstrict1" in dil:
        errors.append(
            "pin DILIGENCE_BRIEF must not cite Experimental soak packs as pin evidence"
        )
    p2p_honest = (ROOT / "network" / "p2p_node.py").read_text(encoding="utf-8")
    if "get_block failed during head-height bind" not in p2p_honest:
        errors.append(
            "p2p_node head-height bind must treat get_block failure as mismatch"
        )
    if "native p2p_native_clamp_batch failed" not in p2p_honest:
        errors.append("p2p_node clamp helpers must log native clamp failures")
    path_a_py = (ROOT / "sync" / "catchup" / "path_a.py").read_text(encoding="utf-8")
    if "[PathA] needs_genesis check failed" not in path_a_py:
        errors.append("PathA must log and fail-closed on needs_genesis errors")
    catchup_ad = (ROOT / "network" / "catchup_adapters.py").read_text(encoding="utf-8")
    if "[CatchUpChain] head failed" not in catchup_ad:
        errors.append("catchup_adapters must log head() failures")
    if "[CatchUpFetch] wait failed" not in catchup_ad:
        errors.append("catchup_adapters must log fetch wait failures")
    peer_mgr_py = (ROOT / "network" / "peer_manager.py").read_text(encoding="utf-8")
    if "[PeerManager] strike_count native failed" not in peer_mgr_py:
        errors.append("peer_manager must log native strike_count failures")
    if "[PeerManager] eclipse subnet probe failed" not in peer_mgr_py:
        errors.append("peer_manager must log eclipse subnet probe failures")
    fork_ad = (ROOT / "network" / "fork_adapters.py").read_text(encoding="utf-8")
    if "[ForkSide] note_reorg_risk failed" not in fork_ad:
        errors.append("fork_adapters must log note_reorg_risk failures")
    if "[ForkSide] bump_counter failed" not in fork_ad:
        errors.append("fork_adapters must log bump_counter failures")
    rocks_store_py = (ROOT / "storage" / "rocks_store.py").read_text(encoding="utf-8")
    if "[RocksStore] prefix_last chain tip failed" not in rocks_store_py:
        errors.append("rocks_store get_chain_tip must log prefix_last failures")
    if "[P2P] restore native timeout failed" not in p2p_honest:
        errors.append("p2p_node must log native timeout restore failures")
    if "get_block_by_hash failed for attestation gossip" not in p2p_honest:
        errors.append("p2p_node must refuse attestation gossip without observed header")
    finality_py = (ROOT / "finality_engine.py").read_text(encoding="utf-8")
    if "native fe_epoch failed; Python path" not in finality_py:
        errors.append("finality_engine must log native fe_epoch failures")
    rocks_ad_py = (ROOT / "storage" / "adapters" / "rocks_adapter.py").read_text(
        encoding="utf-8"
    )
    if "treat as no open batch" not in rocks_ad_py:
        errors.append(
            "rocks_adapter in_transaction probe fail must not assume open batch"
        )
    if "assume open batch" in rocks_ad_py:
        errors.append("rocks_adapter must not assume open batch on probe failure")
    http_bridge = (ROOT / "api" / "http.py").read_text(encoding="utf-8")
    if "bridge get_stats failed" not in http_bridge:
        errors.append("http._bridge_for_request must log get_stats failures")
    if "bridge_result_normalize_failed" not in http_bridge:
        errors.append(
            "_bridge_http_result must refuse truthy non-bool on normalize failure"
        )
    if "peer heights from get_peers_info failed" not in http_bridge:
        errors.append("http.py must log peer-height scrape failures (readiness honesty)")
    rpc_py = (ROOT / "api" / "rpc_service.py").read_text(encoding="utf-8")
    if "self.query is not None" not in rpc_py:
        errors.append("RpcService.get_stats enabled must track query port presence")
    adapter_py = (ROOT / "consensus" / "adapter.py").read_text(encoding="utf-8")
    if "arm_quorum_live failed" not in adapter_py:
        errors.append("consensus adapter must log arm_quorum_live failures")
    bc_py = (ROOT / "core" / "blockchain.py").read_text(encoding="utf-8")
    if "UoW abort failed after StorageError" not in bc_py:
        errors.append("blockchain must log UoW abort failures after StorageError")
    rocks_ad = (ROOT / "storage" / "adapters" / "rocks_adapter.py").read_text(
        encoding="utf-8"
    )
    if "storage ping failed" not in rocks_ad:
        errors.append("rocks_adapter.ping must log failures")
    if "P2PLineFramer construct failed" not in p2p_honest:
        errors.append("p2p_node must log P2PLineFramer construct failures")
    soak_pf = (ROOT / "scripts" / "soak_preflight.py").read_text(encoding="utf-8")
    if "require_wire_probe" not in soak_pf or "--require-wire-probe" not in soak_pf:
        errors.append("soak_preflight must accept --require-wire-probe")
    if "require_libp2p" not in soak_pf or "--require-libp2p" not in soak_pf:
        errors.append("soak_preflight must accept --require-libp2p (ADR 0020)")
    if "quick=False" not in soak_pf or "peer_timeout=8.0" not in soak_pf:
        errors.append(
            "soak_preflight require_wire_probe must use full harness (not quick/3s)"
        )
    vps = (ROOT / "scripts" / "verify_prod_stack.py").read_text(encoding="utf-8")
    if "isolate_keys" not in vps or "FEATURE_LIBP2P" not in vps:
        errors.append(
            "verify_prod_stack must isolate ambient FEATURE_LIBP2P/TIP_SAFETY from JSON validate"
        )
    pma = (ROOT / "scripts" / "pre_mainnet_audit.py").read_text(encoding="utf-8")
    if "live_automated=True" not in pma or "evaluate_external_audit" not in pma:
        errors.append(
            "pre_mainnet_audit must call evaluate_external_audit(live_automated=True)"
        )
    if '"external_audit"' not in pma and "'external_audit'" not in pma:
        errors.append("pre_mainnet_audit report must embed external_audit summary")
    vp2p = (ROOT / "scripts" / "verify_p2p_ci.py").read_text(encoding="utf-8")
    if "def _default_prod_smoke_wallet" not in vp2p:
        errors.append("verify_p2p_ci must default PROD_SMOKE_WALLET_PATH to validator-1 wallet")
    if "max_attempts = max(need * 12, need + 8)" not in vp2p:
        errors.append("verify_p2p_ci ready settle must allow longer KeepVolumes flaps")
    if "exc2" not in vp2p or "Surface body" not in vp2p:
        errors.append("verify_p2p_ci _post_json must surface HTTP body on non-auth errors")
    if not (ROOT / "scripts" / "mempool_validation_sidecar.py").is_file():
        errors.append("scripts/mempool_validation_sidecar.py missing (soak companion)")
    else:
        mvs = (ROOT / "scripts" / "mempool_validation_sidecar.py").read_text(
            encoding="utf-8"
        )
        if "_refuse_empty_tx" not in mvs or "NOT 48h" not in mvs:
            errors.append("mempool_validation_sidecar must refuse-smoke and honesty-label")
    if not (ROOT / "scripts" / "start_mempool_validation_soak.ps1").is_file():
        errors.append("scripts/start_mempool_validation_soak.ps1 missing")
    # Exp→pin ops tooling: Strict parallel worker + cargo honesty + soak FAIL pack.
    if not (ROOT / "scripts" / "health_watch_node.ps1").is_file():
        errors.append(
            "scripts/health_watch_node.ps1 missing (Strict parallel health_watch worker)"
        )
    hw_core_ops = (ROOT / "scripts" / "health_watch_core.ps1").read_text(encoding="utf-8")
    if "health_watch_node.ps1" not in hw_core_ops:
        errors.append("health_watch_core must invoke health_watch_node.ps1 worker")
    if not (ROOT / "scripts" / "cargo_test_abs_native.py").is_file():
        errors.append("scripts/cargo_test_abs_native.py missing (CPython-linked cargo test)")
    else:
        cta = (ROOT / "scripts" / "cargo_test_abs_native.py").read_text(encoding="utf-8")
        if "no-default-features" not in cta or "extension-module" not in cta:
            errors.append(
                "cargo_test_abs_native must disable extension-module for cargo test link"
            )
    if not (ROOT / "scripts" / "cargo_test_rust_bridge_smoke.py").is_file():
        errors.append("scripts/cargo_test_rust_bridge_smoke.py missing (0-test honesty)")
    else:
        cts = (ROOT / "scripts" / "cargo_test_rust_bridge_smoke.py").read_text(
            encoding="utf-8"
        )
        if "running 0 tests" not in cts:
            errors.append(
                "cargo_test_rust_bridge_smoke must label 0-test compile smoke (not verification)"
            )
    if not (ROOT / "scripts" / "summarize_soak_fail.py").is_file():
        errors.append("scripts/summarize_soak_fail.py missing (honest FAIL pack)")
    else:
        sum_py = (ROOT / "scripts" / "summarize_soak_fail.py").read_text(encoding="utf-8")
        if '"passed": False' not in sum_py:
            errors.append("summarize_soak_fail must hardcode passed=False")
    if not (ROOT / "scripts" / "soak_guard.py").is_file():
        errors.append("scripts/soak_guard.py missing (refuse mesh hammer during soak)")
    if not (ROOT / "scripts" / "open_ops_console.ps1").is_file():
        errors.append("scripts/open_ops_console.ps1 missing (ops console launcher)")
    if not (ROOT / "scripts" / "verify_adr0021_phase1.ps1").is_file():
        errors.append("scripts/verify_adr0021_phase1.ps1 missing (operator self-check wrapper)")
    if not (ROOT / "scripts" / "audit_critical_paths.py").is_file():
        errors.append("scripts/audit_critical_paths.py missing (honesty pattern scan)")
    # Exp→pin industrial verify/check surface.
    for rel, msg in (
        ("scripts/verify_full_blockchain.py", "verify_full_blockchain.py missing"),
        ("scripts/verify_hard_all.ps1", "verify_hard_all.ps1 missing"),
        ("scripts/check_blockchain.py", "check_blockchain.py missing"),
        ("scripts/check_harness_probe.py", "check_harness_probe.py missing"),
        ("scripts/check_soak.ps1", "check_soak.ps1 missing"),
        ("scripts/verify_industrial_high_honesty.ps1", "verify_industrial_high_honesty.ps1 missing"),
        ("scripts/libp2p_lab_smoke.py", "libp2p_lab_smoke.py missing"),
        ("scripts/run_all_tests.ps1", "run_all_tests.ps1 missing"),
    ):
        if not (ROOT / rel).is_file():
            errors.append(msg)
    full_py = (ROOT / "scripts" / "verify_full_blockchain.py").read_text(encoding="utf-8")
    if "PROD_SMOKE_WALLET_PATH" not in full_py:
        errors.append(
            "verify_full_blockchain must bind PROD_SMOKE_WALLET_PATH before live p2p_ci"
        )
    if "verify_industrial_high_honesty.ps1" not in full_py:
        errors.append(
            "verify_full_blockchain --hard must run industrial HIGH honesty (not Exp R&D suite)"
        )
    if "start_soak" in full_py.lower():
        errors.append("verify_full_blockchain must not start soak")
    # Exp→pin honesty unit surface (ops soak helpers + money/gas refuse + CSP UI).
    for rel, msg in (
        ("tests/unit/test_soak_guard.py", "test_soak_guard.py missing"),
        ("tests/unit/test_soak_ready_only_rescore.py", "test_soak_ready_only_rescore.py missing"),
        ("tests/unit/test_status_probe_soak.py", "test_status_probe_soak.py missing"),
        ("tests/unit/test_native_f64_unwrap_hygiene.py", "test_native_f64_unwrap_hygiene.py missing"),
        ("tests/unit/test_mempool_get_for_block.py", "test_mempool_get_for_block.py missing"),
        ("tests/unit/test_mesh_tip_catchup_helpers.py", "test_mesh_tip_catchup_helpers.py missing"),
        ("tests/unit/test_transaction_from_dict.py", "test_transaction_from_dict.py missing"),
        ("tests/unit/test_web_console_static.py", "test_web_console_static.py missing"),
        ("tests/unit/test_bridge_decision_off_sealed.py", "test_bridge_decision_off_sealed.py missing"),
        ("tests/unit/test_wallet_tx_gas_required.py", "test_wallet_tx_gas_required.py missing"),
        ("tests/unit/test_no_invent_gas_21000.py", "test_no_invent_gas_21000.py missing"),
        (
            "docs/evidence/runs/bridgeoff1/bridge_decision_off.json",
            "sealed bridgeoff1/bridge_decision_off.json missing",
        ),
    ):
        if not (ROOT / rel).is_file():
            errors.append(msg)
    bog = (ROOT / "scripts" / "bridge_off_audit_gate.py").read_text(encoding="utf-8")
    if "sealed bridgeoff1 pack" not in bog:
        errors.append(
            "bridge_off_audit_gate must accept sealed bridgeoff1 pack (not only local evidence_run)"
        )
    vci = (ROOT / "scripts" / "verify_p2p_ci.py").read_text(encoding="utf-8")
    if "def _mesh_tips_aligned" not in vci:
        errors.append(
            "verify_p2p_ci must define _mesh_tips_aligned (tip+1 / BehindOpen unit surface)"
        )
    if "def _force_prod_mesh_catchup" not in vci:
        errors.append(
            "verify_p2p_ci must define _force_prod_mesh_catchup (tip+1 heal for EVM evidence)"
        )
    if "ok-nofreeze" not in vci or "release .resume + force catch-up" not in vci:
        errors.append(
            "prod-mesh3 EVM evidence must release .resume without Rocks freeze + force catch-up"
        )
    wire = (ROOT / "native" / "abs_native" / "src" / "p2p_wire.rs").read_text(encoding="utf-8")
    if "always bind gas when present" not in wire:
        errors.append(
            "p2p_wire must always bind gas_limit when present (including 21000)"
        )
    if "if g != 21000" in wire:
        errors.append(
            "p2p_wire must not skip gas_limit bind when gas==21000 (signature parity)"
        )
    # Exp→pin EVM nested honesty (RETURNDATACOPY live buffer + STATICCALL no writeback).
    for rel, msg in (
        ("tests/unit/test_evm_empty_account_call.py", "test_evm_empty_account_call.py missing"),
        ("tests/unit/test_evm_nested_returndata.py", "test_evm_nested_returndata.py missing"),
        ("tests/unit/test_evm_nested_staticcall.py", "test_evm_nested_staticcall.py missing"),
        ("tests/unit/test_nft_marketplace_harden.py", "test_nft_marketplace_harden.py missing"),
    ):
        if not (ROOT / rel).is_file():
            errors.append(msg)
    pure = (ROOT / "native" / "abs_native" / "src" / "evm_pure_runner.rs").read_text(
        encoding="utf-8"
    )
    if "Live buffer: CALL/CREATE update" not in pure:
        errors.append(
            "evm_pure_runner RETURNDATACOPY must use live return_data (not inbound snapshot)"
        )
    if "if success && !frame.static_call" not in pure:
        errors.append(
            "evm_pure_runner must not commit inline storage after successful STATICCALL"
        )
    # Exp→pin ops metrics + catchup honesty.
    if "def observe_status_ms" not in (
        ROOT / "observability" / "metrics.py"
    ).read_text(encoding="utf-8"):
        errors.append("metrics must expose observe_status_ms (GET /status histogram)")
    met = (ROOT / "observability" / "metrics.py").read_text(encoding="utf-8")
    if "abs_rocksdb_estimate_num_keys" not in met:
        errors.append("metrics must export abs_rocksdb_estimate_num_keys")
    http_py = (ROOT / "api" / "http.py").read_text(encoding="utf-8")
    if "rocksdb.estimate-num-keys" not in http_py:
        errors.append("/metrics must scrape rocksdb.estimate-num-keys into rocksdb_tuning")
    se = (ROOT / "sync" / "sync_engine.py").read_text(encoding="utf-8")
    if "_wire_sticky_empty_max" not in se:
        errors.append("sync_engine must keep sticky-green empty/timeout streak before lockdown")
    eio = (ROOT / "sync" / "catchup" / "engine_io.py").read_text(encoding="utf-8")
    if "needs_genesis checker failed" not in eio:
        errors.append("engine_io needs_genesis must log + fall back (not silent False)")
    if not (ROOT / "tests" / "unit" / "test_status_metrics_histogram.py").is_file():
        errors.append("test_status_metrics_histogram.py missing")
    # Exp→pin status ceremony cache + mempool_store honesty + pyo3 link test.
    http_src = (ROOT / "api" / "http.py").read_text(encoding="utf-8")
    if "def _genesis_ceremony_status" not in http_src:
        errors.append("api/http must cache genesis ceremony via _genesis_ceremony_status")
    if '"mempool_store":' not in http_src or "min_fee_satoshi" not in http_src:
        errors.append("GET /status must expose mempool_store demote/min_fee_satoshi honesty")
    met2 = (ROOT / "observability" / "metrics.py").read_text(encoding="utf-8")
    if "append_libp2p_prometheus_lines" not in met2:
        errors.append("metrics must optionally export libp2p prometheus series (ADR 0020)")
    librs = (ROOT / "native" / "abs_native" / "src" / "lib.rs").read_text(encoding="utf-8")
    if "mod pyo3_link_tests" not in librs:
        errors.append("abs_native lib.rs must include pyo3_link_tests (cargo test CPython link)")
    if "pub(crate) fn evm_opcode_supported" not in librs:
        errors.append("evm_opcode_supported must be pub(crate) for native test visibility")
    if not (ROOT / "tests" / "unit" / "test_genesis_ceremony_status_cache.py").is_file():
        errors.append("test_genesis_ceremony_status_cache.py missing")
    # Exp→pin state_root solicit + EVM API honesty.
    p2p_src = (ROOT / "network" / "p2p_node.py").read_text(encoding="utf-8")
    if "def _state_root_solicit_height" not in p2p_src:
        errors.append("p2p_node must define _state_root_solicit_height (no stale peer.height cap)")
    if "_state_root_solicit_height(peer, height)" not in p2p_src:
        errors.append("request_peer_state_root must call _state_root_solicit_height")
    http_src2 = (ROOT / "api" / "http.py").read_text(encoding="utf-8")
    if "bytecode validation unavailable" not in http_src2:
        errors.append("/evm/validate-bytecode must 503 on probe/import failure (not valid=false)")
    if "merge_compat_summary(supported_opcodes_summary())" not in http_src2:
        errors.append("/evm/supported-opcodes must merge_compat_summary honesty")
    if not (ROOT / "tests" / "unit" / "test_state_root_solicit_evm_honesty.py").is_file():
        errors.append("test_state_root_solicit_evm_honesty.py missing")
    # Load real prod mesh JSON (bare Config() is always deployment_mode=dev).
    prod_tls_enabled = False
    prod_json_files = (
        "docker/node.prod.mesh1.json",
        "docker/node.prod.mesh2.json",
        "docker/node.prod.mesh3.json",
        "docker/node.prod.json",
        "deploy/k8s/node.prod.k8s.json",
        "node.prod.example.json",
        "node.prod.mainnet-v1.example.json",
        "node.prod.mainnet-v1.bridge.example.json",
    )
    shared_keys = (
        "p2p_max_messages_per_sec",
        "p2p_attest_messages_per_sec",
        "p2p_tx_messages_per_sec",
        "p2p_block_announce_messages_per_sec",
        "p2p_max_message_bytes",
        "p2p_ban_seconds",
        "p2p_rate_limit_strikes",
        "p2p_evict_min_score",
        "rocksdb_sync",
        "rocksdb_block_cache_mb",
        "rocksdb_write_buffer_mb",
        "rocksdb_column_families",
        "bridge_enabled",
        "require_native_crypto",
        "state_root_legacy_cutoff_height",
        "rust_bridge_path",
        "bridge_auto_confirm_sec",
    )
    mesh_json_cfgs: list[tuple[str, dict]] = []
    for rel in prod_json_files:
        path = ROOT / rel
        if not path.is_file():
            continue
        try:
            prod_cfg = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if str(prod_cfg.get("deployment_mode", "")).lower() != "prod":
            continue
        for key in shared_keys:
            if key not in prod_cfg:
                errors.append(f"{rel}: missing industrial key {key}")
        rate = int(prod_cfg.get("p2p_max_messages_per_sec", 0) or 0)
        if rate <= 0:
            errors.append(f"{rel}: p2p_max_messages_per_sec must be > 0")
        for class_key in (
            "p2p_attest_messages_per_sec",
            "p2p_tx_messages_per_sec",
            "p2p_block_announce_messages_per_sec",
        ):
            cap = int(prod_cfg.get(class_key, 0) or 0)
            if cap <= 0:
                errors.append(f"{rel}: {class_key} must be > 0")
        max_bytes = int(prod_cfg.get("p2p_max_message_bytes", 0) or 0)
        if max_bytes and max_bytes < DEFAULT_MAX_P2P_LINE_BYTES // 2:
            errors.append(
                f"{rel}: p2p_max_message_bytes below industrial floor "
                f"({DEFAULT_MAX_P2P_LINE_BYTES // 2})"
            )
        if prod_cfg.get("bridge_enabled") is True:
            if "bridge" in Path(rel).name.lower():
                warnings.append(
                    f"{rel}: bridge_enabled=true (cutover example only; keep OFF on live mesh)"
                )
            else:
                errors.append(f"{rel}: bridge_enabled must be false until L1 audit")
        if prod_cfg.get("p2p_tls_enabled") is True:
            prod_tls_enabled = True
        mesh_min = int(prod_cfg.get("mesh_min_peers_before_mine", 0) or 0)
        needs_redis = mesh_min >= 1 or "k8s" in Path(rel).name.lower()
        if needs_redis:
            if "redis_rate_limit_enabled" not in prod_cfg or "redis_url" not in prod_cfg:
                errors.append(f"{rel}: mesh/k8s requires redis_rate_limit_enabled + redis_url")
            elif prod_cfg.get("redis_rate_limit_enabled") is not True:
                errors.append(f"{rel}: redis_rate_limit_enabled must be true for mesh/k8s")
            elif not str(prod_cfg.get("redis_url") or "").strip():
                errors.append(f"{rel}: redis_url must be non-empty for mesh/k8s")
        # ADR 0016: explicit true is refuse. Missing sprout key is overlay-off
        # (prod apply_env still fail-closes). Mesh JSON pins the sprout set.
        # ADR 0020: feature_libp2p is the industrial mesh transport (explicit bool,
        # exclusive with p2p_tls_enabled). long_range must stay explicit false (ADR 0017).
        _feature_keys = (
            "feature_zk",
            "feature_minivm",
            "feature_sharding",
            "feature_oracles",
            "feature_wasm",
            "feature_plasma",
            "feature_lightning",
            "feature_pq",
            "feature_nft",
            "feature_mev",
            "feature_ai_agents",
            "feature_ai_validator",
            "feature_smart_accounts",
            "feature_validator_selection",
            "feature_long_range",
        )
        for fk in _feature_keys:
            if prod_cfg.get(fk) is True:
                errors.append(f"{rel}: ADR 0016 forbids {fk}=true on prod JSON")
        if prod_cfg.get("feature_long_range") is not False:
            errors.append(
                f"{rel}: feature_long_range must be explicit false "
                "(ADR 0017 lab-only; not in industrial mesh)"
            )
        if not isinstance(prod_cfg.get("feature_libp2p"), bool):
            errors.append(
                f"{rel}: feature_libp2p must be an explicit bool (ADR 0020 transport selector)"
            )
        if prod_cfg.get("feature_libp2p") is True and prod_cfg.get("p2p_tls_enabled") is True:
            errors.append(
                f"{rel}: ADR 0020 forbids p2p_tls_enabled=true with feature_libp2p=true "
                "(Noise replaces mTLS; transports are mutually exclusive)"
            )
        if prod_cfg.get("allow_state_root_rewrite") is True:
            errors.append(
                f"{rel}: allow_state_root_rewrite must be false on prod JSON"
            )
        if int(prod_cfg.get("chain_id", 0) or 0) == 778888:
            if prod_cfg.get("feature_nft") is True:
                errors.append(f"{rel}: FEATURE_NFT forbidden on chain_id 778888")
        if "mesh" in Path(rel).name.lower():
            mesh_json_cfgs.append((rel, prod_cfg))
            for fk in _feature_keys:
                if fk == "feature_long_range":
                    continue
                if fk in prod_cfg and prod_cfg.get(fk) is not False:
                    errors.append(
                        f"{rel}: ADR 0016 requires {fk}=false on prod mesh "
                        f"(got {prod_cfg.get(fk)!r})"
                    )
            # ADR 0020 pin industrial mesh cutover: libp2p true, native p2p_tls off.
            if prod_cfg.get("feature_libp2p") is not True:
                errors.append(
                    f"{rel}: ADR 0020 requires feature_libp2p=true on pin industrial "
                    f"prod mesh (got {prod_cfg.get('feature_libp2p')!r})"
                )
            if prod_cfg.get("p2p_tls_enabled") is not False:
                errors.append(
                    f"{rel}: ADR 0020 libp2p mesh requires p2p_tls_enabled=false "
                    f"(got {prod_cfg.get('p2p_tls_enabled')!r})"
                )
    # Compose env freeze vs prod JSON (3-node mesh + single-node).
    import re

    def _compose_default(compose_text: str, env_key: str) -> str | None:
        m = re.search(
            rf"(?m)^\s*{re.escape(env_key)}:\s*(.+?)\s*$",
            compose_text,
        )
        if not m:
            return None
        raw = m.group(1).strip().strip('"').strip("'")
        dm = re.match(r"^\$\{[^:]+:-([^}]+)\}$", raw)
        if dm:
            return dm.group(1).strip().strip('"').strip("'")
        return raw

    def _freeze_compose_json(
        compose_rel: str,
        json_cfgs: list[tuple[str, dict]],
        env_map: dict[str, str],
    ) -> None:
        compose_path = ROOT / compose_rel
        if not compose_path.is_file() or not json_cfgs:
            return
        compose_text = compose_path.read_text(encoding="utf-8")
        for env_key, json_key in env_map.items():
            compose_val = _compose_default(compose_text, env_key)
            if compose_val is None:
                errors.append(f"{compose_rel} missing {env_key}")
                continue
            for rel, prod_cfg in json_cfgs:
                if json_key not in prod_cfg:
                    continue
                raw = prod_cfg.get(json_key)
                if isinstance(raw, bool):
                    json_val = "true" if raw else "false"
                else:
                    json_val = str(raw).strip()
                if compose_val.lower() != json_val.lower():
                    errors.append(
                        f"compose↔JSON mismatch {compose_rel} {env_key}={compose_val} vs "
                        f"{rel}.{json_key}={json_val}"
                    )

    shared_compose_env = {
        "ROCKSDB_SYNC": "rocksdb_sync",
        "ROCKSDB_BLOCK_CACHE_MB": "rocksdb_block_cache_mb",
        "ROCKSDB_WRITE_BUFFER_MB": "rocksdb_write_buffer_mb",
        "ROCKSDB_COLUMN_FAMILIES": "rocksdb_column_families",
        "P2P_MAX_MESSAGE_BYTES": "p2p_max_message_bytes",
        "P2P_MAX_MESSAGES_PER_SEC": "p2p_max_messages_per_sec",
        "P2P_BAN_SECONDS": "p2p_ban_seconds",
        "P2P_RATE_LIMIT_STRIKES": "p2p_rate_limit_strikes",
        "P2P_EVICT_MIN_SCORE": "p2p_evict_min_score",
        "BRIDGE_ENABLED": "bridge_enabled",
        "DB_ENGINE": "db_engine",
        "JWT_ENFORCE_ADMIN": "jwt_enforce_admin",
    }
    mesh_env = dict(shared_compose_env)
    mesh_env["REDIS_RATE_LIMIT"] = "redis_rate_limit_enabled"
    mesh_env["REDIS_URL"] = "redis_url"
    mesh_env["FEATURE_LIBP2P"] = "feature_libp2p"
    _freeze_compose_json("docker-compose.prod.3node.yml", mesh_json_cfgs, mesh_env)

    single_json: list[tuple[str, dict]] = []
    single_path = ROOT / "docker" / "node.prod.json"
    if single_path.is_file():
        try:
            single_cfg = json.loads(single_path.read_text(encoding="utf-8"))
            if str(single_cfg.get("deployment_mode", "")).lower() == "prod":
                single_json.append(("docker/node.prod.json", single_cfg))
        except (OSError, json.JSONDecodeError):
            pass
    _freeze_compose_json("docker-compose.prod.yml", single_json, shared_compose_env)

    for overlay in (
        "docker-compose.prod.p2ptls.yml",
        "docker-compose.prod.3node.p2ptls.yml",
    ):
        overlay_path = ROOT / overlay
        if not overlay_path.is_file():
            errors.append(f"missing {overlay}")
            continue
        overlay_txt = overlay_path.read_text(encoding="utf-8")
        for needle in (
            "P2P_TLS_ENABLED",
            "P2P_TLS_FAIL_CLOSED",
            "P2P_TLS_BIND_IDENTITY",
            "P2P_TLS_REQUIRE_CLIENT_CERT",
        ):
            if needle not in overlay_txt:
                errors.append(f"{overlay} missing {needle}")

    env_ex = ROOT / ".env.example"
    if env_ex.is_file():
        env_txt = env_ex.read_text(encoding="utf-8")
        if "778888" not in env_txt:
            errors.append(".env.example must document mainnet CHAIN_ID 778888")
        if "CHAIN_ID=77777" not in env_txt and "CHAIN_ID=778888" not in env_txt:
            errors.append(".env.example missing CHAIN_ID example value")
        if "ENABLE_CORS_RPC_PROXY=false" not in env_txt:
            errors.append(".env.example must default ENABLE_CORS_RPC_PROXY=false")
        if "CORS_ORIGINS=*" in env_txt:
            errors.append(".env.example must not default CORS_ORIGINS=*")
    main_py = (ROOT / "main.py").read_text(encoding="utf-8")
    if 'Access-Control-Allow-Origin", "*"' in main_py or "Access-Control-Allow-Origin', '*'" in main_py:
        errors.append("main.py CORS RPC proxy must not hardcode Allow-Origin *")
    if "prod CORS RPC proxy requires explicit CORS_ORIGINS" not in main_py:
        errors.append("main.py must refuse prod CORS proxy with wildcard origins")
    rocks_py = (ROOT / "storage" / "rocks_store.py").read_text(encoding="utf-8")
    if "reorg_truncate_above: corrupt block JSON" not in rocks_py:
        errors.append("rocks_store.reorg_truncate_above must log corrupt block JSON")
    if "corrupt tx JSON" not in rocks_py:
        errors.append("rocks_store.reorg must log corrupt tx JSON")
    if "corrupt tx_propagation JSON" not in rocks_py:
        errors.append("rocks_store.reorg purge must log corrupt tx_propagation JSON")
    if "rocksdb_properties_error" not in rocks_py:
        errors.append("rocks_store.get_stats must surface rocksdb_properties_error")
    if "def get_rocks_runtime_stats" not in rocks_py:
        errors.append("rocks_store must expose get_rocks_runtime_stats (no prefix scan)")
    runtime_core_fn = rocks_py.split("def _rocks_runtime_core", 1)[-1].split(
        "def get_rocks_runtime_stats", 1
    )[0]
    if "_cached_prefix_len" in runtime_core_fn or "_scan_prefix" in runtime_core_fn:
        errors.append("_rocks_runtime_core must not prefix-scan or call _cached_prefix_len")
    db_py = (ROOT / "storage" / "database.py").read_text(encoding="utf-8")
    if "DELETE FROM evm_logs WHERE block_height" not in db_py:
        errors.append("SQLite reorg_truncate_above must delete evm_logs")
    if "DELETE FROM tx_propagation_events WHERE block_height" not in db_py:
        errors.append("SQLite reorg_truncate_above must delete tx_propagation_events")
    if "def truncate_blocks_above" in db_py and "truncate_chain_state(height)" not in db_py:
        errors.append("SQLite truncate_blocks_above must call truncate_chain_state")
    if "def _normalize_tx_status" not in db_py:
        errors.append("SQLite must define _normalize_tx_status")
    if "Missing/unknown → 0 (fail-closed)" not in db_py:
        errors.append("SQLite _normalize_tx_status must fail-closed on missing/unknown")
    http_py = (ROOT / "api" / "http.py").read_text(encoding="utf-8")
    if 'origins else "*"' in http_py:
        errors.append("api/http.py REST CORS must not fall back to *")
    if "get_rocks_runtime_stats" not in http_py:
        errors.append("/metrics must use get_rocks_runtime_stats (no prefix scan)")
    health_py = (ROOT / "bridge" / "health.py").read_text(encoding="utf-8")
    if "probe_skipped" not in health_py:
        errors.append("bridge.health must mark unprobed L1 as probe_skipped")
    metrics_py = (ROOT / "observability" / "metrics.py").read_text(encoding="utf-8")
    if "abs_l1_rpc_probed" not in metrics_py:
        errors.append("metrics.py missing abs_l1_rpc_probed")
    libp2p_mesh = any(c.get("feature_libp2p") is True for _, c in mesh_json_cfgs)
    if not prod_tls_enabled and not libp2p_mesh:
        warnings.append(
            "prod mesh JSON: p2p_tls_enabled is not true "
            "(enable TLS overlay / -P2pTls for public mainnet wire)"
        )
    if not (ROOT / "docs" / "adr" / "0020-libp2p-industrial-mesh.md").is_file():
        errors.append("missing ADR 0020 libp2p industrial mesh")
    else:
        adr20_txt = (ROOT / "docs" / "adr" / "0020-libp2p-industrial-mesh.md").read_text(
            encoding="utf-8"
        )
        if "Does not apply to Hybrid" in adr20_txt:
            errors.append(
                "ADR 0020 must be rebound to pin industrial mesh cutover "
                "(stale 'Does not apply to Hybrid / audit-pin')"
            )
    cfg_src_20 = (ROOT / "runtime" / "config.py").read_text(encoding="utf-8")
    if "FEATURE_LIBP2P" not in cfg_src_20:
        errors.append("runtime/config.py must include FEATURE_LIBP2P (ADR 0020 mesh)")
    if not (ROOT / "network" / "transport" / "libp2p_adapter" / "adapter.py").is_file():
        errors.append("missing network/transport/libp2p_adapter/adapter.py (ADR 0020)")
    # ADR 0003 — sync consistency boundary + solicit hub
    p2p_src = (ROOT / "network" / "p2p_node.py").read_text(encoding="utf-8")
    sync_src = (ROOT / "sync" / "sync_engine.py").read_text(encoding="utf-8")
    if not (ROOT / "docs" / "adr" / "0003-sync-consistency.md").is_file():
        errors.append("missing ADR 0003 sync consistency")
    if not (ROOT / "sync" / "ports.py").is_file():
        errors.append("missing sync/ports.py (ADR 0003)")
    if not (ROOT / "sync" / "solicit.py").is_file():
        errors.append("missing sync/solicit.py SyncSolicitHub (ADR 0003)")
    if "solicit_hub.fulfill_or_reject" not in p2p_src:
        errors.append("p2p_node must route waiters via solicit_hub.fulfill_or_reject")
    if "from sync.solicit import SyncSolicitHub" not in p2p_src:
        errors.append("p2p_node must import SyncSolicitHub")
    solicit_src = (ROOT / "sync" / "solicit.py").read_text(encoding="utf-8")
    if "_kind_waiters" not in solicit_src:
        errors.append(
            "solicit hub must park per-kind waiters so state_root is not blocked by mempool"
        )
    if "Park even when kinds match" not in solicit_src:
        errors.append("solicit hub must park a second same-kind state_root waiter")
    if "_collect_state_root_waiters" not in solicit_src:
        errors.append("solicit hub must fan state_root replies to primary + parked waiters")
    if "self._solicit_lock_for(pid, kind)" not in p2p_src:
        errors.append("state_root solicit lock must be per-kind, not per-peer")
    if "Wait outside the lock" not in p2p_src:
        errors.append("solicit wait must not hold per-kind lock for the full timeout")
    if "if pid and self.peers.get(pid) is not peer" not in p2p_src:
        errors.append("solicit wait must fail-fast when the peer has already dropped")
    if "hub.timeout(pid, result=None, kind=kind, fut=fut)" not in p2p_src:
        errors.append("solicit timeout must be fut-scoped so it cannot steal a parked waiter")
    if "hub.clear(peer.peer_id, kind=kind, fut=fut)" not in p2p_src:
        errors.append("solicit clear must be fut-scoped so it cannot steal a parked waiter")
    path_a_src = (ROOT / "sync" / "catchup" / "path_a.py").read_text(encoding="utf-8")
    if "already canonical, skip reorg" not in path_a_src:
        errors.append("PathA _import_one must skip reorg for an already-canonical duplicate")
    if "Failed +1 extend (parent is the current tip) is not a fork" not in path_a_src:
        errors.append("PathA _import_one must not reorg when parent==tip (failed extend)")
    if "ConsistencyService" not in sync_src:
        errors.append("SyncEngine must use ConsistencyService")
    if "def force_inconsistent" not in p2p_src:
        errors.append("P2PNode must expose force_inconsistent (single-writer lockdown)")
    if "async def refresh_consistency" not in p2p_src:
        errors.append("P2PNode must expose refresh_consistency")
    if "CatchUpOrchestrator" not in p2p_src:
        errors.append("P2PNode must wire CatchUpOrchestrator")
    if "abs_sync_consistency_state" not in metrics_py:
        errors.append("metrics must export abs_sync_consistency_state")
    if "import_block" not in (ROOT / "main.py").read_text(encoding="utf-8"):
        errors.append("AbsoluteNode.import_block tip-safety path missing")
    return errors, warnings


def _check_fail_loud_surfaces() -> tuple[list[str], list[str]]:
    """Static inspect: prod-critical paths must not silent-pass probe/meta failures."""
    import inspect

    errors: list[str] = []
    warnings: list[str] = []
    http_py = (ROOT / "api" / "http.py").read_text(encoding="utf-8")
    try:
        from sync.sync_engine import SyncEngine

        src = inspect.getsource(SyncEngine.sync_state)
        if "peer state_root wire probe failed" not in src:
            errors.append("SyncEngine.sync_state must log wire probe failures")
        if "wire probe empty" not in src and "empty with" not in src:
            errors.append("SyncEngine.sync_state must fail-closed on empty probe with peers")
        if "missing get_state_root" not in src:
            errors.append("SyncEngine.sync_state must fail-closed when get_state_root missing")
        status_src = inspect.getsource(SyncEngine.get_status)
        if "wire_probe_ok" not in status_src:
            errors.append("SyncEngine.get_status missing wire_probe_ok")
        if "wire_probe_probed" not in status_src:
            errors.append("SyncEngine.get_status missing wire_probe_probed")
    except Exception as exc:
        errors.append(f"fail-loud sync inspect failed: {exc}")
    try:
        from blockchain.immutable_state import ImmutableStateManager

        src = inspect.getsource(ImmutableStateManager.reconcile_from_store)
        if "fail_loud" not in src:
            errors.append("IMS reconcile_from_store missing fail_loud")
        if "except Exception:\n                        pass" in src or "except Exception:\n                            pass" in src:
            errors.append("IMS reconcile_from_store still has silent except pass")
    except Exception as exc:
        errors.append(f"fail-loud IMS inspect failed: {exc}")
    try:
        main_py = (ROOT / "main.py").read_text(encoding="utf-8")
        if "sync_state probe failed" not in main_py:
            errors.append("main.py mining loop must log sync_state probe failures")
        try:
            src = inspect.getsource(SyncEngine.fast_sync)
            if "return bool(self.sync_state())" not in src and "self.sync_state()" not in src:
                errors.append("SyncEngine.fast_sync must re-check consistency via sync_state()")
        except Exception as exc:
            errors.append(f"SyncEngine.fast_sync inspect failed: {exc}")
        if "db_probe_error" not in http_py or "/health/ready" not in http_py:
            errors.append("/health/ready must probe database and surface db_probe_error")
        if (
            "self.p2p._state_consistent = False" not in main_py
            and "force_inconsistent" not in main_py
        ):
            errors.append(
                "main.py must clear consistency on sync probe failure "
                "(force_inconsistent or _state_consistent=False)"
            )
        for needle in (
            "[Mining] PBS auction failed",
            "[Mining] cross-shard processing failed",
            "[Mining] epoch pool unlock failed",
        ):
            if needle not in main_py:
                errors.append(f"main.py mining loop must log: {needle}")
        if "p2p.sync_engine = self.sync_engine" not in main_py:
            errors.append("main.py must share AbsoluteNode SyncEngine with P2P")
        if "shared with P2P" not in main_py:
            errors.append("main.py must log SyncEngine shared with P2P")
    except Exception as exc:
        errors.append(f"fail-loud main.py inspect failed: {exc}")
    try:
        http_py = (ROOT / "api" / "http.py").read_text(encoding="utf-8")
        if 'checks["p2p_running"]' not in http_py and "p2p_running" not in http_py:
            errors.append("/health/ready must check p2p_running in prod")
        if "prod without a P2P object is not ready" not in http_py:
            errors.append(
                "/health/ready must fail-closed when p2p is None in prod (Phase D5)"
            )
        if "tip_skew" not in http_py or "tip_lagging" not in http_py:
            errors.append(
                "p2p_sync_status must use tip_skew/tip_lagging (not false inconsistent)"
            )
        if "get_cached_account_count" not in http_py:
            errors.append(
                "consistency harness must use get_cached_account_count (no invent/prefix-scan)"
            )
        if 'after.get("state_consistent", False)' not in http_py:
            errors.append("fork recovery must default state_consistent=False (fail-closed)")
        if "never echo first allowlist entry" not in http_py:
            errors.append("CORS must never echo first allowlist entry on miss")
        if "empty cors_origins must not promote to *" not in http_py:
            errors.append("CORS empty allowlist must not promote to *")
        if 'success = bool(repaired) and harness_ok and consistent' not in http_py:
            errors.append(
                "/chain/consistency/repair success must require repair+harness+consistent"
            )
        if 'if peer_count > 0:' not in http_py or 'checks["state_consistent"]' not in http_py:
            errors.append("/health/ready with peers must require state_consistent")
        if 'checks["peer_count_probe"] = False' not in http_py:
            errors.append("/health/ready peer_count probe failure must fail-closed")
        if 'p2p_fallback' not in http_py or "SyncEngine missing" not in http_py:
            errors.append("p2p_fallback sync status must fail-closed when SyncEngine missing")
        if '"enabled": False' not in http_py or '"sync_engine_missing": True' not in http_py:
            errors.append("p2p_fallback must set enabled=false and sync_engine_missing=true")
        native_py = (ROOT / "crypto" / "native.py").read_text(encoding="utf-8", errors="replace")
        if "Exceptions must not paint as invalid signature" not in native_py:
            errors.append("native secp verify must return None on probe failure (not False)")
        txv_py = (ROOT / "blockchain" / "tx_validator.py").read_text(
            encoding="utf-8", errors="replace"
        )
        if "signature verify unavailable" not in txv_py:
            errors.append("tx_validator must not paint probe failure as Invalid signature")
        if "do not invent demo 42" not in http_py:
            errors.append("ZK prove/range must not invent demo value=42")
        if '"valid": True' in http_py and 'path == "/zk/prove/range"' in http_py:
            # Force-valid paint on educational ZK is dishonest when prove_range returns no bool.
            chunk = http_py.split('path == "/zk/prove/range"')[1].split("elif path")[0]
            if '"valid": True' in chunk:
                errors.append("ZK prove/range must not force valid:true")
        zk_src = (ROOT / "features" / "zk.py").read_text(
            encoding="utf-8", errors="replace"
        )
        if "zk_range_proof_not_implemented" not in zk_src:
            errors.append("features/zk.py must refuse educational range hash theater")
        nft_ports_py = (ROOT / "features" / "nft_ports.py").read_text(
            encoding="utf-8", errors="replace"
        )
        if 'stats.setdefault("enabled", True)' in nft_ports_py:
            errors.append("NFT get_stats must not invent enabled=True")
        if '"enabled": False' not in nft_ports_py:
            errors.append("NFT get_stats fallback must default enabled=false")
        rocks_py_sat = (ROOT / "storage" / "rocks_store.py").read_text(
            encoding="utf-8", errors="replace"
        )
        if "tx_money_satoshi" not in rocks_py_sat:
            errors.append("rocks_store txs/receipts must dual-write via tx_money_satoshi")
        if 'tx.get("value", tx.get("amount", 0.0))' in rocks_py_sat:
            errors.append("rocks_store must not invent tx value=0.0 on insert")
        if '"receipts_enabled": True' in rocks_py_sat:
            errors.append("rocks metrics receipts_enabled must reflect observed backend")
        db_py_sat = (ROOT / "storage" / "database.py").read_text(
            encoding="utf-8", errors="replace"
        )
        if "def _backfill_tx_money_satoshi" not in db_py_sat:
            errors.append("SQLite must backfill transactions/tx_receipts satoshi twins")
        if "def _backfill_burn_satoshi" not in db_py_sat:
            errors.append("SQLite must backfill burn_stats/blocks satoshi twins")
        if 'tx.get("value", tx.get("amount", 0.0))' in db_py_sat:
            errors.append("SQLite must not invent tx value=0.0 on insert")
        if '("transactions", "value_satoshi", "INTEGER")' not in db_py_sat:
            errors.append("SQLite migration must add transactions.value_satoshi")
        if "burned_amount_satoshi" not in db_py_sat:
            errors.append("SQLite burn_stats must dual-write burned_amount_satoshi")
        if "burn_last_window_satoshi" not in db_py_sat:
            errors.append("SQLite get_chain_metrics must expose burn_last_window_satoshi")
        if "SUM(total_burned_satoshi)" not in db_py_sat:
            errors.append("SQLite proposer stats must SUM(total_burned_satoshi)")
        if "burned_amount_satoshi" not in rocks_py_sat:
            errors.append("rocks_store burn must dual-write burned_amount_satoshi")
        if "burn_last_window_satoshi" not in rocks_py_sat:
            errors.append("rocks_store get_chain_metrics must expose burn_last_window_satoshi")
        if "def get_proposer_stats" not in rocks_py_sat:
            errors.append("RocksChainStore must implement get_proposer_stats")
        if "def get_proposer_detail" not in rocks_py_sat:
            errors.append("RocksChainStore must implement get_proposer_detail")
        if "def _adjust_total_supply_abs" not in rocks_py_sat:
            errors.append("rocks_store must maintain total_supply_abs on balance deltas")
        if "def get_cached_total_supply" not in rocks_py_sat:
            errors.append("rocks_store must expose get_cached_total_supply (O(1) poll)")
        if "def get_cached_total_burned" not in rocks_py_sat:
            errors.append("rocks_store must expose get_cached_total_burned (O(1) poll)")
        if "get_cached_total_supply" not in http_py:
            errors.append("/status must use get_cached_total_supply (not full supply scan)")
        if "def _status_cached_metric" not in http_py:
            errors.append("api/http.py must define _status_cached_metric for poll honesty")
        mempool_py = (ROOT / "blockchain" / "mempool.py").read_text(
            encoding="utf-8", errors="replace"
        )
        if "def _tx_to_store_dict" not in mempool_py:
            errors.append("mempool must expose _tx_to_store_dict (satoshi store roundtrip)")
        if "def _tx_from_store_dict" not in mempool_py:
            errors.append("mempool must expose _tx_from_store_dict (satoshi store roundtrip)")
        if 'gas or 21000' in mempool_py or 'gas, 21000)' in mempool_py:
            errors.append("mempool must not invent gas=21000 on store reload")
        if 'raw_gas is not None and str(raw_gas).strip() != "" else 0' not in mempool_py:
            errors.append("mempool _tx_from_store_dict must default missing gas to 0")
        if "min_fee_satoshi" not in mempool_py:
            errors.append("mempool must gate/order fees via min_fee_satoshi")
        if "fee_too_low (min_satoshi=" not in mempool_py:
            errors.append("mempool fee gate must refuse with min_satoshi (not float ABS)")
        if '"amount_satoshi"' not in mempool_py or '"fee_satoshi"' not in mempool_py:
            errors.append("mempool get_sorted_transactions must export amount/fee_satoshi")
        wallet_py = (ROOT / "crypto" / "wallet.py").read_text(
            encoding="utf-8", errors="replace"
        )
        if "int(gas_limit) != 21000" in wallet_py:
            errors.append("wallet canonical hash must not omit gas_limit=21000")
        if "Always bind gas into the digest when present" not in wallet_py:
            errors.append("wallet must bind present gas_limit into signing digest")
        p2p_py = (ROOT / "network" / "p2p_node.py").read_text(
            encoding="utf-8", errors="replace"
        )
        if "p2p_mempool_require_explicit_gas" not in p2p_py:
            errors.append("p2p must document/refuse invent gas (explicit gas required)")
        if 'int(data.get("gas", 0) or 0) or 21_000' in p2p_py:
            errors.append("p2p must not invent gas=21000 on mempool ingest")
        types_py = (ROOT / "storage" / "types.py").read_text(
            encoding="utf-8", errors="replace"
        )
        if "SATOSHI_PER_COIN: int = 100_000_000" in types_py:
            errors.append("AccountRecord SATOSHI_PER_COIN must be protocol 1e6, not Bitcoin 1e8")
        if "to_satoshi(d.get(\"balance\"))" not in types_py:
            errors.append("AccountRecord.from_mapping must convert float balance via to_satoshi")
        state_svc_py = (ROOT / "core" / "components" / "state_service.py").read_text(
            encoding="utf-8", errors="replace"
        )
        if "satoshi_store_required_credit" not in state_svc_py:
            errors.append("StateService._credit_sat must refuse float store fallback")
        exec_mp = (ROOT / "execution" / "mempool.py").read_text(
            encoding="utf-8", errors="replace"
        )
        if 'tx.get("fee", 1)' in exec_mp or "gas_price: float = 1.0" in exec_mp:
            errors.append("execution mempool must not invent gas_price/fee=1")
        if "gas_price_required" not in exec_mp:
            errors.append("execution create_transaction must require explicit gas_price")
        sec_mp = (ROOT / "execution" / "secure_mempool.py").read_text(
            encoding="utf-8", errors="replace"
        )
        if "fee_required" not in sec_mp:
            errors.append("secure_mempool must refuse omitted fee (no invent 1)")
        txv_sat = (ROOT / "blockchain" / "tx_validator.py").read_text(
            encoding="utf-8", errors="replace"
        )
        if "value_satoshi_mismatch" not in txv_sat:
            errors.append("tx_validator must refuse value_satoshi_mismatch")
        if 'v.get("stake", 100)' in (ROOT / "main.py").read_text(
            encoding="utf-8", errors="replace"
        ):
            errors.append("main.py must not invent stake=100 for proposer selection")
        if "Refuse invent stake=100" not in (ROOT / "main.py").read_text(
            encoding="utf-8", errors="replace"
        ):
            errors.append("main.py must skip validators with missing stake")
        mev_py = (ROOT / "features" / "mev_analyzer.py").read_text(
            encoding="utf-8", errors="replace"
        )
        if "21000 * 2" in mev_py or "21000*2" in mev_py:
            errors.append("MEV simulate_frontrun must not invent gas_used=21000*2")
        if '"simulation_only": True' not in mev_py:
            errors.append("MEV get_statistics must declare simulation_only=true")
        if 'path == "/mev/history"' in http_py:
            hist_chunk = http_py.split('path == "/mev/history"', 1)[1].split(
                "elif path", 1
            )[0]
            if '"simulation_only": True' not in hist_chunk:
                errors.append("/mev/history must stamp simulation_only=true")
        if "ai_validator.update_performance" in (
            ROOT / "main.py"
        ).read_text(encoding="utf-8", errors="replace"):
            errors.append("main forge path must not feed AI validator update_performance")
        if "get_last_block failed in state_root_response" not in (
            ROOT / "network" / "p2p_node.py"
        ).read_text(encoding="utf-8", errors="replace"):
            errors.append(
                "P2P state_root_response must refuse when get_last_block fails"
            )
        if "get_last_block failed in _local_needs_genesis" not in (
            ROOT / "sync" / "sync_engine.py"
        ).read_text(encoding="utf-8", errors="replace"):
            errors.append(
                "SyncEngine._local_needs_genesis must fail-closed on store error"
            )
        oracle_reg = (ROOT / "features" / "oracle_registry.py").read_text(
            encoding="utf-8", errors="replace"
        )
        if "parse_finite_number" not in oracle_reg:
            errors.append("oracle_registry must refuse NaN/Inf/bool via parse_finite_number")
        if "parse_finite_number" not in (
            ROOT / "storage" / "database.py"
        ).read_text(encoding="utf-8", errors="replace"):
            errors.append("Database oracle save paths must use parse_finite_number")
        if "balances_satoshi" not in (
            ROOT / "api" / "fake_rpc.py"
        ).read_text(encoding="utf-8", errors="replace"):
            errors.append("FakeQueryFacade must expose balances_satoshi twin")
        rocks_meta = (ROOT / "storage" / "rocks_store.py").read_text(
            encoding="utf-8", errors="replace"
        )
        if "def _cached_prefix_len" not in rocks_meta:
            errors.append("rocks_store must seed obs counts via _cached_prefix_len")
        if 'self._bump_plain_meta_int("stats_account_count"' not in rocks_meta:
            errors.append("rocks_store must bump stats_account_count on new accounts")
        if "def _invalidate_obs_meta" not in rocks_meta:
            errors.append("rocks_store must invalidate obs meta on alloc reset")
        db_finite = (ROOT / "storage" / "database.py").read_text(
            encoding="utf-8", errors="replace"
        )
        if 'field="fee_rate"' not in db_finite:
            errors.append("Database lightning channels must parse_finite_number fee_rate")
        if 'field="performance_score"' not in db_finite:
            errors.append("Database AI agents must parse_finite_number performance_score")
        bridge_py = (ROOT / "bridge" / "abs_bridge.py").read_text(
            encoding="utf-8", errors="replace"
        )
        lock_fn = bridge_py.split("def lock_and_bridge", 1)[-1].split(
            "def ", 1
        )[0]
        if "burn_sats <= 0" not in lock_fn or "satoshi_store_required" not in lock_fn:
            errors.append(
                "bridge lock must require debit+burn satoshi deltas (fail-closed)"
            )
        if "Database._normalize_tx_status(tx.get(\"status\"))" not in http_py:
            eth_fmt_py = (ROOT / "api" / "eth_format.py").read_text(
                encoding="utf-8", errors="replace"
            )
            if "def observed_receipt_status" not in eth_fmt_py:
                errors.append(
                    "receipt format must use observed_receipt_status (null if unobserved)"
                )
            if "def observed_block_hash" not in eth_fmt_py:
                errors.append("eth_format must expose observed_block_hash (no zero stub)")
            if "def observed_parent_hash" not in eth_fmt_py:
                errors.append("eth_format must expose observed_parent_hash (genesis zero only)")
            if "def observed_state_root" not in eth_fmt_py:
                errors.append("eth_format must not stub missing stateRoot as the zero digest")
            if "def observed_miner" not in eth_fmt_py:
                errors.append("eth_format must not default miner to empty string")
            if "def observed_block_nonce" not in eth_fmt_py:
                errors.append("eth_format must not stub block nonce as 8 zero bytes")
            if "def observed_block_size" not in eth_fmt_py:
                errors.append("eth_format must not invent block size from tx count")
            if "def observed_block_timestamp" not in eth_fmt_py:
                errors.append("eth_format must not default missing timestamp to epoch 0")
            if '"parentHash": blk.get("parent_hash", "")' in eth_fmt_py:
                errors.append("format_block must not default parentHash to empty string")
            if '"hash": blk.get("hash", blk.get("block_hash", ""))' in eth_fmt_py:
                errors.append("format_block hash must not default to empty string")
            if '"nonce": "0x0000000000000000"' in eth_fmt_py:
                errors.append("format_block must not hardcode ethash-shaped nonce")
            if "256 + len(tx_hashes)" in eth_fmt_py:
                errors.append("format_block size must not use the 256+32*n heuristic")
            if 'hex(int(row.get("log_index", 0)))' in eth_fmt_py:
                errors.append("format_eth_log must not default missing logIndex to 0")
            if 'int(row.get("block_height", 0))' in eth_fmt_py:
                errors.append("format_eth_log must not default missing blockNumber to height 0")
            if '"address": row.get("contract_address", "")' in eth_fmt_py:
                errors.append("format_eth_log must not default address to empty string")
            if "def block_sha3_uncles" not in eth_fmt_py:
                errors.append("eth_format must expose block_sha3_uncles (keccak rlp empty list)")
            if '"sha3Uncles": "0x" + "0" * 64' in eth_fmt_py:
                errors.append("eth_format must not stub sha3Uncles as zero")
            if "keccak256_digest(b\"\\xc0\")" not in eth_fmt_py:
                errors.append("empty sha3Uncles must be keccak256 of RLP empty list (0xc0)")
            if "def receipt_cumulative_gas_used" not in eth_fmt_py:
                errors.append("eth_format must compute cumulativeGasUsed from block tx order")
            if '"cumulativeGasUsed": hex(gas_used)' in eth_fmt_py:
                errors.append("receipt cumulativeGasUsed must not copy gasUsed")
            if '"transactionIndex": hex(int(tx_index)),' in eth_fmt_py:
                errors.append("receipt transactionIndex must be null when unobserved")
            if "def burned_satoshi" not in eth_fmt_py:
                errors.append("eth_format must emit burn as satoshi integers")
            if "def block_gas_used" not in eth_fmt_py:
                errors.append("block_gas_used must not invent 0 when header gas is missing")
            if "def block_logs_bloom" not in eth_fmt_py:
                errors.append("eth_format must expose block_logs_bloom from stored/reconstructed logs")
            if "def format_uncle_by_index" not in eth_fmt_py:
                errors.append("eth_format must not invent uncle headers from bare hashes")
            if '"totalBurned": blk.get("total_burned", 0.0)' in eth_fmt_py:
                errors.append("format_block totalBurned must not be an IEEE float default")
        if '"bridge_relayer_live": bool(cfg.bridge_enabled)' in http_py:
            errors.append("bridge_relayer_live must not equal bridge_enabled alone")
        if '"bridge_rust_binary_healthy"' not in http_py:
            errors.append("core_real must expose bridge_rust_binary_healthy separately from relayer_live")
        if '"relayer_observed"' not in http_py:
            errors.append("core_real must expose relayer_observed honesty flag")
        if 'and bool(bridge_health.get("ok"))' not in http_py:
            errors.append("bridge_rust_binary_healthy must require rust bridge health ok")
        if '"bridge_relayer_live": False' not in http_py:
            errors.append("bridge_relayer_live must stay false until relayer heartbeat observed")
        if 'out["error"] = "bridge_disabled"' not in http_py:
            errors.append("_rust_bridge_health must fail-closed when bridge disabled")
        if "json_decode_failures" not in (
            ROOT / "storage" / "rocks_store.py"
        ).read_text(encoding="utf-8"):
            errors.append("rocks_store must expose json_decode_failures for /metrics")
        if "Config-on ≠ actively forging under mesh gate" not in http_py:
            errors.append("eth_mining must gate on mesh_min_peers / state_consistent")
        if 'checks["wire_probe_probed"]' not in http_py or 'checks["wire_probe_ok"]' not in http_py:
            errors.append("/health/ready with peers must require wire_probe_probed/ok")
        if '"degraded"' not in http_py or "peer_count > 0 and not state_consistent" not in http_py:
            errors.append("/status must report degraded when peers + inconsistent")
        if "peer_count > 0 and not wire_probe_probed" not in http_py:
            errors.append("/status must report degraded when peers + never wire-probed")
        if 'checks["state_engine"]' not in http_py or 'checks["finality_engine"]' not in http_py:
            errors.append("/health/ready prod must check state_engine and finality_engine")
        if 'checks["immutable_state"]' not in http_py:
            errors.append("/health/ready prod must check immutable_state")
        if '"ims_available": False' not in http_py:
            errors.append("abs-balance/total-supply must not claim canonical without IMS")
        if '"finality_quorum_live": False' not in http_py:
            errors.append("core_real must not invent finality_quorum_live from local attest count")
        if '"local_attestations_present"' not in http_py:
            errors.append("core_real must expose local_attestations_present separately from quorum")
        # ADR 0007 — consensus ports + round SM (fail-closed; quorum_live stays false)
        consensus_ports = (ROOT / "consensus" / "ports.py").read_text(encoding="utf-8")
        if "class ConsensusPort" not in consensus_ports:
            errors.append("consensus/ports.py must define ConsensusPort (ADR 0007)")
        if "class ValidatorRegistryPort" not in consensus_ports:
            errors.append("consensus/ports.py must define ValidatorRegistryPort (ADR 0007)")
        round_sm_py = (ROOT / "consensus" / "bft" / "service.py").read_text(
            encoding="utf-8"
        )
        if "class RoundStateMachine" not in round_sm_py:
            errors.append("consensus/bft must expose RoundStateMachine (ADR 0007)")
        adapter_py = (ROOT / "consensus" / "adapter.py").read_text(encoding="utf-8")
        if "RoundStateMachine" not in adapter_py:
            errors.append("ConsensusAdapter must wire RoundStateMachine (ADR 0007)")
        if (
            "round_sm" not in adapter_py
            and "_round_state" not in adapter_py
            and "round_state" not in adapter_py
        ):
            errors.append(
                "ConsensusAdapter must expose round_state / round_sm (ADR 0007)"
            )
        if (
            "_init_round_state" not in adapter_py
            and "_init_round_state_machine" not in adapter_py
        ):
            errors.append(
                "ConsensusAdapter must init round state machine (ADR 0007)"
            )
        # ADR 0007 honesty: never invent live quorum from local attests alone.
        # Wave C: True only when config `finality_quorum_live` is armed AND QC reached.
        if "never claim live mesh quorum unless config arms it" not in adapter_py:
            errors.append(
                "ConsensusAdapter must gate finality_quorum_live on config arm + QC "
                "(ADR 0007 honesty)"
            )
        if "allow_live and getattr(view, \"quorum_live\"" not in adapter_py:
            errors.append(
                "ConsensusAdapter finality_status must AND config arm with view.quorum_live"
            )
        if not (ROOT / "docs" / "adr" / "0007-consensus-boundary.md").is_file():
            errors.append("docs/adr/0007-consensus-boundary.md missing")
        if not (ROOT / "docs" / "adr" / "0009-optional-native-fallback.md").is_file():
            errors.append("docs/adr/0009-optional-native-fallback.md missing")
        if not (ROOT / "docs" / "adr" / "0010-evm-bridge-boundary.md").is_file():
            errors.append("docs/adr/0010-evm-bridge-boundary.md missing")
        if not (ROOT / "docs" / "adr" / "0011-rpc-api-boundary.md").is_file():
            errors.append("docs/adr/0011-rpc-api-boundary.md missing")
        if not (ROOT / "docs" / "adr" / "0012-chaos-injection.md").is_file():
            errors.append("docs/adr/0012-chaos-injection.md missing")
        if not (ROOT / "docs" / "adr" / "0014-graceful-shutdown-deep-health.md").is_file():
            errors.append("docs/adr/0014-graceful-shutdown-deep-health.md missing")
        if not (ROOT / "docs" / "adr" / "0015-observability-secret-management.md").is_file():
            errors.append("docs/adr/0015-observability-secret-management.md missing")
        if not (ROOT / "docs" / "adr" / "0016-feature-sprouts-profiles.md").is_file():
            errors.append("docs/adr/0016-feature-sprouts-profiles.md missing")
        if not (ROOT / "consensus" / "tip_safety" / "ancestry_window.py").is_file():
            errors.append("consensus/tip_safety/ancestry_window.py missing (ADR 0016 stage-1.5)")
        anc_py = (ROOT / "consensus" / "tip_safety" / "ancestry_window.py").read_text(
            encoding="utf-8", errors="replace"
        )
        if "class AncestryWindow" not in anc_py:
            errors.append("AncestryWindow missing (ADR 0016)")
        if not (ROOT / "tests" / "unit" / "test_prod_mesh_feature_freeze.py").is_file():
            errors.append("tests/unit/test_prod_mesh_feature_freeze.py missing (ADR 0016)")
        if not (ROOT / "docs" / "sprouts" / "README.md").is_file():
            errors.append("docs/sprouts/README.md missing (ADR 0016 profiles)")
        for sprout_doc in (
            "EVM_DEPTH.md",
            "BRIDGE_CUTOVER_PROFILE.md",
            "APP_STAGING_PROFILE.md",
            "L2_SANDBOX_PROFILE.md",
            "SHARD_LAB_PROFILE.md",
            "CEREMONY_AND_SECRETS.md",
        ):
            if not (ROOT / "docs" / "sprouts" / sprout_doc).is_file():
                errors.append(f"docs/sprouts/{sprout_doc} missing (ADR 0016)")
        if not (ROOT / "docker" / "node.staging.app.json").is_file():
            errors.append("docker/node.staging.app.json missing (ADR 0016 Profile C)")
        if not (ROOT / "docker-compose.staging.app.yml").is_file():
            errors.append("docker-compose.staging.app.yml missing (ADR 0016 Profile C)")
        if not (ROOT / "docker" / "node.sandbox.l2.json").is_file():
            errors.append("docker/node.sandbox.l2.json missing (ADR 0016 Profile D)")
        if "sprout_ready_independent" not in (
            ROOT / "api" / "http.py"
        ).read_text(encoding="utf-8", errors="replace"):
            errors.append("api/http.py must keep ready independent of L2 sprouts (ADR 0016)")
        if "_uow" not in (ROOT / "features" / "nft.py").read_text(
            encoding="utf-8", errors="replace"
        ):
            errors.append("features/nft.py must use atomic UoW helper _uow (ADR 0016)")
        if not (ROOT / "tests" / "unit" / "test_nft_uow.py").is_file():
            errors.append("tests/unit/test_nft_uow.py missing (ADR 0016)")
        if not (ROOT / "scripts" / "prod_evm_smoke.py").is_file():
            errors.append("scripts/prod_evm_smoke.py missing (EVM depth evidence)")
        if not (ROOT / "docs" / "sprouts" / "EVM_DEPTH.md").is_file():
            errors.append("docs/sprouts/EVM_DEPTH.md missing")
        if not (ROOT / "docker-compose.sandbox.l2.yml").is_file():
            errors.append("docker-compose.sandbox.l2.yml missing (ADR 0016 Profile D)")
        if not (ROOT / "docker-compose.shard.lab.yml").is_file():
            errors.append("docker-compose.shard.lab.yml missing (ADR 0016 Profile E)")
        if not (ROOT / "features" / "nft_ports.py").is_file():
            errors.append("features/nft_ports.py missing (ADR 0016 NftMarketplacePort)")
        nft_ports_py = (ROOT / "features" / "nft_ports.py").read_text(
            encoding="utf-8", errors="replace"
        )
        if "class NftMarketplacePort" not in nft_ports_py:
            errors.append("NftMarketplacePort missing (ADR 0016)")
        if "class NullNftMarketplacePort" not in nft_ports_py:
            errors.append("NullNftMarketplacePort missing (ADR 0016)")
        feat_init = (ROOT / "features" / "__init__.py").read_text(
            encoding="utf-8", errors="replace"
        )
        if '"nft": "app-profile"' not in feat_init and "'nft': 'app-profile'" not in feat_init:
            errors.append("MODULE_TIERS nft must be app-profile (ADR 0016 honesty)")
        if not (ROOT / "observability" / "ports.py").is_file():
            errors.append("observability/ports.py missing (ADR 0015 MetricsExporterPort)")
        obs_ports = (ROOT / "observability" / "ports.py").read_text(
            encoding="utf-8", errors="replace"
        )
        if "class MetricsExporterPort" not in obs_ports:
            errors.append("observability/ports.py must define MetricsExporterPort (ADR 0015)")
        if "class MetricsSnapshot" not in obs_ports:
            errors.append("observability/ports.py must define MetricsSnapshot (ADR 0015)")
        metrics_py_adr15 = (ROOT / "observability" / "metrics.py").read_text(
            encoding="utf-8", errors="replace"
        )
        if "abs_tps" not in metrics_py_adr15:
            errors.append("observability/metrics.py must export abs_tps (ADR 0015)")
        if "abs_p2p_security_ok" not in metrics_py_adr15:
            errors.append("observability/metrics.py must export abs_p2p_security_ok (ADR 0015)")
        if not (ROOT / "secret_mgmt" / "ports.py").is_file():
            errors.append("secret_mgmt/ports.py missing (ADR 0015 SecretManagerPort)")
        sm_ports = (ROOT / "secret_mgmt" / "ports.py").read_text(
            encoding="utf-8", errors="replace"
        )
        if "class SecretManagerPort" not in sm_ports:
            errors.append("secret_mgmt/ports.py must define SecretManagerPort (ADR 0015)")
        if not (ROOT / "secret_mgmt" / "vault_adapter.py").is_file():
            errors.append("secret_mgmt/vault_adapter.py missing (ADR 0015)")
        vault_py = (ROOT / "secret_mgmt" / "vault_adapter.py").read_text(
            encoding="utf-8", errors="replace"
        )
        if "class VaultKvSecretAdapter" not in vault_py:
            errors.append("VaultKvSecretAdapter missing (ADR 0015)")
        if not (ROOT / "secret_mgmt" / "env_adapter.py").is_file():
            errors.append("secret_mgmt/env_adapter.py missing (ADR 0015)")
        factory_py = (ROOT / "secret_mgmt" / "factory.py").read_text(
            encoding="utf-8", errors="replace"
        )
        if "SECRET_BACKEND" not in factory_py and "secret_backend" not in factory_py:
            errors.append("secret_mgmt factory must honor SECRET_BACKEND (ADR 0015)")
        if "SECRET_BACKEND=file refused in production" not in factory_py:
            errors.append("factory must refuse SECRET_BACKEND=file in prod (ADR 0015)")
        if "SECRET_BACKEND=null/off refused in production" not in factory_py:
            errors.append("factory must refuse SECRET_BACKEND=null in prod (ADR 0015)")
        file_adapter_py = (ROOT / "secret_mgmt" / "file_adapter.py").read_text(
            encoding="utf-8", errors="replace"
        )
        if "allow_prod" in file_adapter_py:
            errors.append("FileSecretAdapter must not expose allow_prod break-glass")
        if "refused in production" not in file_adapter_py:
            errors.append("FileSecretAdapter must refuse production (ADR 0015)")
        if not (ROOT / "tests" / "unit" / "test_prometheus_export_format.py").is_file():
            errors.append("tests/unit/test_prometheus_export_format.py missing (ADR 0015)")
        if not (ROOT / "tests" / "unit" / "test_secrets_isolation.py").is_file():
            errors.append("tests/unit/test_secrets_isolation.py missing (ADR 0015)")
        main_py_adr15 = (ROOT / "main.py").read_text(encoding="utf-8", errors="replace")
        if "build_secret_manager" not in main_py_adr15:
            errors.append("main.py must wire build_secret_manager (ADR 0015)")
        if "prod SecretManager init failed" not in main_py_adr15:
            errors.append(
                "main.py must fail-closed if SecretManager init fails in prod (ADR 0015)"
            )
        http_py_adr15 = (ROOT / "api" / "http.py").read_text(encoding="utf-8", errors="replace")
        if "metrics_exporter" not in http_py_adr15:
            errors.append("api/http.py must wire metrics_exporter (ADR 0015)")
        if not (ROOT / "chaos" / "ports.py").is_file():
            errors.append("chaos/ports.py missing (ADR 0012)")
        if not (ROOT / "chaos" / "engine.py").is_file():
            errors.append("chaos/engine.py missing (ADR 0012 TotalChaosEngine)")
        chaos_engine_py = (ROOT / "chaos" / "engine.py").read_text(
            encoding="utf-8", errors="replace"
        )
        if "class TotalChaosEngine" not in chaos_engine_py:
            errors.append("chaos/engine.py must define TotalChaosEngine (ADR 0012)")
        if "refuse_prod_arming" not in chaos_engine_py:
            errors.append("chaos/engine.py must refuse prod arming (ADR 0012)")
        if not (ROOT / "tests" / "chaos" / "test_total_chaos_bombardment.py").is_file():
            errors.append("tests/chaos/test_total_chaos_bombardment.py missing (ADR 0012)")
        main_py_chaos = (ROOT / "main.py").read_text(encoding="utf-8", errors="replace")
        if "TotalChaosEngine" in main_py_chaos or "from chaos" in main_py_chaos or "import chaos" in main_py_chaos:
            errors.append("main.py must not arm/import chaos (ADR 0012)")
        if "set_accepting_requests" not in main_py_chaos:
            errors.append("main.py must drain RPC via set_accepting_requests (ADR 0014)")
        if "_shutting_down" not in main_py_chaos:
            errors.append("NodeOrchestrator must track _shutting_down (ADR 0014)")
        http_py_adr14 = (ROOT / "api" / "http.py").read_text(encoding="utf-8", errors="replace")
        if "def set_accepting_requests" not in http_py_adr14:
            errors.append("api/http.py must define set_accepting_requests (ADR 0014)")
        if "_deep_ready_mesh_checks" not in http_py_adr14:
            errors.append("api/http.py must define _deep_ready_mesh_checks (ADR 0014)")
        if "peers_alive" not in http_py_adr14 or "sync_not_stalled" not in http_py_adr14:
            errors.append("api/http.py /health/ready must expose deep mesh checks (ADR 0014)")
        rocks_py = (ROOT / "storage" / "rocks_store.py").read_text(
            encoding="utf-8", errors="replace"
        )
        if "clean close" not in rocks_py:
            errors.append("RocksChainStore.close must log clean close (ADR 0014)")
        if not (ROOT / "tests" / "e2e" / "test_runtime_signals.py").is_file():
            errors.append("tests/e2e/test_runtime_signals.py missing (ADR 0014)")
        if not (ROOT / "api" / "ports.py").is_file():
            errors.append("api/ports.py missing (ADR 0011 RpcPort)")
        api_ports_py = (ROOT / "api" / "ports.py").read_text(encoding="utf-8", errors="replace")
        if "class RpcPort" not in api_ports_py:
            errors.append("api/ports.py must define RpcPort (ADR 0011)")
        if "class QueryFacadePort" not in api_ports_py:
            errors.append("api/ports.py must define QueryFacadePort (ADR 0011)")
        if "def get_evm_logs_by_block" not in api_ports_py:
            errors.append("QueryFacadePort must expose get_evm_logs_by_block (block logsBloom)")
        eth_fmt_py_adr = (ROOT / "api" / "eth_format.py").read_text(
            encoding="utf-8", errors="replace"
        )
        if "def block_logs_bloom" not in eth_fmt_py_adr:
            errors.append("api/eth_format.py must compute block logsBloom (not a zero stub)")
        if "def block_transactions_root" not in eth_fmt_py_adr:
            errors.append("eth_format must expose block_transactions_root (Absolute merkle)")
        if "def block_receipts_root" not in eth_fmt_py_adr:
            errors.append("eth_format must expose block_receipts_root (Absolute merkle)")
        if "def format_uncle_by_index" not in eth_fmt_py_adr:
            errors.append("eth_format must expose format_uncle_by_index (null, not invented header)")
        if "def format_uncle_count" not in eth_fmt_py_adr:
            errors.append("eth_format must return null uncle-count when the block is missing")
        if "def observed_receipt_status" not in eth_fmt_py_adr:
            errors.append("receipt status must not treat omitted status as reverted 0x0")
        if "def block_gas_used" not in eth_fmt_py_adr:
            errors.append("eth_format must reconstruct block gasUsed from observed txs")
        rpc_svc_py_adr = (ROOT / "api" / "rpc_service.py").read_text(
            encoding="utf-8", errors="replace"
        )
        if "eth_getUncleByBlockNumberAndIndex" not in rpc_svc_py_adr:
            errors.append("rpc_service must implement eth_getUncleByBlockNumberAndIndex")
        if 'return hex(0)' in rpc_svc_py_adr and "eth_getUncleCountByBlockNumber" in rpc_svc_py_adr:
            # Still allow other hex(0) uses; refuse invent uncle-count when block missing.
            if "format_uncle_count" not in rpc_svc_py_adr:
                errors.append("rpc_service uncle-count must use format_uncle_count (null if missing)")
        http_py_uncle = (ROOT / "api" / "http.py").read_text(encoding="utf-8", errors="replace")
        if "eth_getUncleByBlockNumberAndIndex" not in http_py_uncle:
            errors.append("http.py must implement eth_getUncleByBlockNumberAndIndex")
        if "format_uncle_count" not in http_py_uncle:
            errors.append("http.py uncle-count must use format_uncle_count (null if missing)")
        if not (ROOT / "api" / "eth_format.py").is_file():
            errors.append("api/eth_format.py missing (ADR 0011)")
        if not (ROOT / "api" / "fake_rpc.py").is_file():
            errors.append("api/fake_rpc.py missing (ADR 0011)")
        bc_py = (ROOT / "core" / "blockchain.py").read_text(encoding="utf-8", errors="replace")
        if "def attach_query_facade" not in bc_py:
            errors.append("Blockchain must expose attach_query_facade (ADR 0011)")
        http_py_adr = (ROOT / "api" / "http.py").read_text(encoding="utf-8", errors="replace")
        if "bc.db.get_block_by_hash" in http_py_adr:
            errors.append("api/http.py must not call bc.db.get_block_by_hash (ADR 0011)")
        if "bc.db.query_evm_logs" in http_py_adr:
            errors.append("api/http.py must not call bc.db.query_evm_logs (ADR 0011)")
        ws_py = (ROOT / "network" / "websocket.py").read_text(encoding="utf-8", errors="replace")
        if "from api.http import" in ws_py:
            errors.append("network/websocket.py must not import from api.http (ADR 0011)")

        if not (ROOT / "bridge" / "ports.py").is_file():
            errors.append("bridge/ports.py missing (ADR 0010 BridgePort)")
        ports_py = (ROOT / "bridge" / "ports.py").read_text(encoding="utf-8", errors="replace")
        if "class BridgePort" not in ports_py:
            errors.append("bridge/ports.py must define BridgePort (ADR 0010)")
        if "class InboundMessageValidatorPort" not in ports_py:
            errors.append("bridge/ports.py must define InboundMessageValidatorPort")
        if "class NullBridgePort" not in ports_py:
            errors.append("bridge/ports.py must define NullBridgePort")
        storage_ports_py = (ROOT / "storage" / "ports.py").read_text(
            encoding="utf-8", errors="replace"
        )
        if "class BridgeStorePort" not in storage_ports_py:
            errors.append("storage/ports.py must define BridgeStorePort (ADR 0010)")
        if "def attach_bridge" not in bc_py:
            errors.append("Blockchain must expose attach_bridge (ADR 0010)")
        if "def claim_and_credit_bridge_event" in bc_py or "def lock_and_bridge" in bc_py:
            errors.append(
                "blockchain.py must not own claim_and_credit / lock_and_bridge bodies (ADR 0010)"
            )
        if not (ROOT / "bridge" / "fake_evm_bridge.py").is_file():
            errors.append("bridge/fake_evm_bridge.py missing (ADR 0010)")
        if not (ROOT / "runtime" / "native_capabilities.py").is_file():
            errors.append("runtime/native_capabilities.py missing (ADR 0009)")
        if not (ROOT / "core" / "components" / "tx_pipeline.py").is_file():
            errors.append("core/components/tx_pipeline.py missing (facade)")
        if not (ROOT / "crypto" / "kernels" / "python" / "wire_borsh.py").is_file():
            errors.append("crypto/kernels/python/wire_borsh.py missing (ADR 0009)")
        if not (ROOT / "network" / "peer_manager.py").is_file():
            errors.append("network/peer_manager.py missing (P2P PeerManager)")
        p2p_py = (ROOT / "network" / "p2p_node.py").read_text(encoding="utf-8", errors="replace")
        if "self.peer_manager = PeerManager" not in p2p_py:
            errors.append("P2PNode must wire PeerManager (peer mesh decomposition)")
        if '"state_engine": self.__class__.state_engine is not None' not in http_py:
            errors.append("core_real must expose state_engine availability")
        if "finality_engine_missing" not in http_py:
            errors.append("/finality/stats must surface finality_engine_missing error")
        if "state_engine_missing" not in http_py:
            errors.append("/state/engine must surface state_engine_missing error")
        if "DB-only is never IMS-canonical when shadow state is absent/unusable" not in http_py:
            errors.append("/state/supply must not claim DB-only canonical")
        if "Peers present with mesh_min=0" not in http_py:
            errors.append("eth_mining must refuse when peers present and inconsistent (mesh_min=0)")
        if 'getattr(p2p, "_server", None) is not None' not in http_py:
            errors.append("/health/ready p2p_running must require bound _server")
        if 'getattr(p2p, "_native_listener", None) is not None' not in http_py:
            errors.append(
                "/health/ready p2p_running must accept native _native_listener "
                "(v1.3.114+ prod transport)"
            )
    except Exception as exc:
        errors.append(f"fail-loud http inspect failed: {exc}")
    try:
        rocks_py = (ROOT / "storage" / "rocks_store.py").read_text(encoding="utf-8")
        if rocks_py.count("self._json_decode_failures += 1") < 15:
            errors.append("rocks_store scan/reorg/list/meta/tx paths must bump json_decode_failures")
        if "corrupt meta" not in rocks_py:
            errors.append("rocks_store get_meta must warn on corrupt decode")
        if "corrupt address_tx row skipped" not in rocks_py:
            errors.append("rocks_store address tx list must warn on corrupt decode")
        if "corrupt recent_tx row skipped" not in rocks_py:
            errors.append("rocks_store recent tx list must warn on corrupt decode")
        if "corrupt latest_block row skipped" not in rocks_py:
            errors.append("rocks_store get_latest_blocks must warn on corrupt decode")
        if "corrupt account row skipped" not in rocks_py:
            errors.append("rocks_store get_all_accounts must warn on corrupt decode")
        if "corrupt validator row skipped" not in rocks_py:
            errors.append("rocks_store get_validators must warn on corrupt decode")
        if (
            "corrupt proposer_audit row skipped" not in rocks_py
            and "corrupt proposer_audit list row skipped" not in rocks_py
        ):
            errors.append("rocks_store proposer_audit must warn on corrupt decode")
        if "corrupt bridge_lock row skipped" not in rocks_py:
            errors.append("rocks_store bridge_locks must warn on corrupt decode")
        if "corrupt state_root_mismatch row skipped" not in rocks_py:
            errors.append("rocks_store state_root mismatches must warn on corrupt decode")
    except Exception as exc:
        errors.append(f"fail-loud rocks_store inspect failed: {exc}")
    try:
        metrics_py = (ROOT / "observability" / "metrics.py").read_text(encoding="utf-8")
        if "abs_rocksdb_json_decode_failures" not in metrics_py:
            errors.append("metrics.py must emit abs_rocksdb_json_decode_failures")
        alerts = (ROOT / "deploy" / "prometheus" / "alerts.yml").read_text(encoding="utf-8")
        if "AbsoluteRocksJsonDecodeFailures" not in alerts:
            errors.append("alerts.yml missing AbsoluteRocksJsonDecodeFailures")
        if "AbsoluteProdCoreEngineMissing" not in alerts:
            errors.append("alerts.yml missing AbsoluteProdCoreEngineMissing")
        if "abs_state_engine_available" not in metrics_py:
            errors.append("metrics.py must emit abs_state_engine_available")
        if "abs_finality_engine_available" not in metrics_py:
            errors.append("metrics.py must emit abs_finality_engine_available")
        if "abs_ims_available" not in metrics_py:
            errors.append("metrics.py must emit abs_ims_available")
    except Exception as exc:
        errors.append(f"fail-loud rocks metrics/alerts inspect failed: {exc}")
    try:
        sync_py = (ROOT / "sync" / "sync_engine.py").read_text(encoding="utf-8")
        if "Solo / no peers — wire probe deferred (never-probed), fail-closed" not in sync_py:
            errors.append("sync_state solo must fail-closed and clear consistency")
        if "No same-height peer root match — fail-closed" not in sync_py:
            errors.append("sync_state must require same-height peer root match before True")
    except Exception as exc:
        errors.append(f"fail-loud sync_engine inspect failed: {exc}")
    try:
        mesh_py = (ROOT / "runtime" / "mesh_mining.py").read_text(encoding="utf-8")
        if "if state_consistent:" not in mesh_py:
            errors.append("mesh_ready_for_mining peer_heights path must gate on state_consistent")
        if "wire_soft_fail and not wire_roots" not in mesh_py:
            errors.append(
                "mesh_ready_for_mining wire_soft_fail must only relax when no wire_roots "
                "(real root mismatch still refuses)"
            )
        if "state_consistent: bool = False" not in mesh_py:
            errors.append("mesh_ready_for_mining state_consistent default must be False")
    except Exception as exc:
        errors.append(f"fail-loud mesh_mining inspect failed: {exc}")
    try:
        bridge_health_py = (ROOT / "bridge" / "health.py").read_text(encoding="utf-8")
        if '"ok": False' not in bridge_health_py or "no L1 RPC URLs configured" not in bridge_health_py:
            errors.append("L1 health must default ok=False when unconfigured")
    except Exception as exc:
        errors.append(f"fail-loud bridge health inspect failed: {exc}")
    try:
        main_py = (ROOT / "main.py").read_text(encoding="utf-8")
        if "never echo first allowlist entry" not in main_py:
            errors.append("RPC CORS proxy must never echo first allowlist entry on miss")
        if "Production mode requires SyncEngine" not in main_py:
            errors.append("main.py must hard-fail SyncEngine init in production")
        if "Production mode requires StateEngine" not in main_py:
            errors.append("main.py must hard-fail StateEngine init in production")
        if "Production mode requires FinalityEngine" not in main_py:
            errors.append("main.py must hard-fail FinalityEngine init in production")
        if "Production mode requires ImmutableStateManager" not in main_py:
            errors.append("main.py must hard-fail ImmutableStateManager missing in production")
        if "Production mode requires block signature" not in main_py:
            errors.append("main.py must hard-fail block signing failures in production")
        if "Peers present require consistency even when mesh_min_peers_before_mine=0" not in main_py:
            errors.append("mining loop must gate consistency when peers present (mesh_min=0)")
    except Exception as exc:
        errors.append(f"fail-loud main CORS inspect failed: {exc}")
    try:
        p2p_py = (ROOT / "network" / "p2p_node.py").read_text(encoding="utf-8")
        solicit_py = (ROOT / "sync" / "solicit.py").read_text(encoding="utf-8")
        dispatch_handlers = (
            ROOT / "network" / "p2p_dispatch" / "handlers.py"
        ).read_text(encoding="utf-8")
        solicit_surface = p2p_py + "\n" + solicit_py + "\n" + dispatch_handlers
        if "self._state_consistent = False" not in p2p_py:
            errors.append("P2PNode must boot with _state_consistent=False")
        # v1.3.138: solicit-only supersedes the older match/mismatch log path.
        # ADR 0003: strike strings may live in SyncSolicitHub / dispatcher.
        if "unsolicited_state_root_response" not in solicit_surface and (
            "Unsolicited state_root match" not in p2p_py
        ):
            errors.append(
                "P2P unsolicited state_root must be solicit-only "
                "(or legacy match must not flip consistent=True)"
            )
        if "unsolicited_state_root_response" not in solicit_surface and (
            "State root mismatch vs" not in p2p_py
        ):
            errors.append(
                "P2P unsolicited state_root must be solicit-only "
                "(or legacy mismatch must clear consistent)"
            )
        # ADR 0004: "Sync incomplete" honesty may live in CatchUpPathAService.
        catchup_path_a = (
            ROOT / "sync" / "catchup" / "path_a.py"
        ).read_text(encoding="utf-8")
        if "Sync incomplete" not in p2p_py and "Sync incomplete" not in catchup_path_a:
            errors.append(
                "P2P sync must log Sync incomplete (not claim complete on stall)"
            )
        if "reached_target" not in p2p_py:
            errors.append("P2P sync must gate state_root baseline on reached_target")
        if "consistent_ok = bool(self._state_consistent) if peers else True" not in p2p_py:
            errors.append("topology_healthy must require state_consistent when peers present")
        if "Reconcile \"ok\" without a SyncEngine must not leave stale mesh-green" not in p2p_py:
            errors.append("reconcile_peers without SyncEngine must clear _state_consistent")
        if "_record_broadcast_results" not in p2p_py or "broadcast_fail" not in p2p_py:
            errors.append("P2P broadcast gather must record False/Exception as broadcast_fail")
        for kind in (
            'kind="cross_shard_ack"',
            'kind="cross_shard_tx"',
            'kind="shard_migration"',
            'kind="validator_register"',
            'kind="catch_up_sync"',
        ):
            if kind not in p2p_py:
                errors.append(f"P2P must record broadcast results for {kind}")
        bind_idx = p2p_py.find("Could not bind port")
        if bind_idx < 0:
            errors.append("P2P start must log Could not bind port")
        else:
            bind_snip = p2p_py[bind_idx : bind_idx + 320]
            if "self._running = False" not in bind_snip or "return" not in bind_snip:
                errors.append("P2P bind failure must set _running=False and return")
    except Exception as exc:
        errors.append(f"fail-loud p2p inspect failed: {exc}")
    try:
        rocks_py = (ROOT / "storage" / "rocks_store.py").read_text(encoding="utf-8")
        if "_loads_json_or_none" not in rocks_py:
            errors.append("rocks_store must use _loads_json_or_none for point-get honesty")
        if (
            'return self._loads_json_or_none(raw, context=f"tx' not in rocks_py
            and 'return self._loads_tx_blob_or_none(raw, context=f"tx' not in rocks_py
        ):
            errors.append("rocks_store get_transaction must use fail-closed JSON decode")
        if (
            'return self._loads_json_or_none(raw, context=f"receipt' not in rocks_py
            and 'return self._loads_receipt_blob_or_none(raw, context=f"receipt'
            not in rocks_py
        ):
            errors.append("rocks_store get_tx_receipt must use fail-closed JSON decode")
        if (
            'return self._loads_json_or_none(raw, context=f"block' not in rocks_py
            and 'return self._loads_block_blob_or_none(raw, context=f"block' not in rocks_py
        ):
            errors.append("rocks_store get_block must use fail-closed JSON decode")
        if 'context=f"slash_validator' not in rocks_py:
            errors.append("rocks_store slash_validator must use fail-closed JSON decode")
        if 'context=f"bridge_lock' not in rocks_py:
            errors.append("rocks_store confirm_bridge_lock must use fail-closed JSON decode")
        if 'context="burn_total"' not in rocks_py:
            errors.append("rocks_store get_total_burned must use fail-closed JSON decode")
        if 'context="tx_propagation"' not in rocks_py:
            errors.append("rocks_store tx_propagation decode must use fail-closed JSON decode")
        if 'context="evm_log"' not in rocks_py:
            errors.append("rocks_store evm_log decode must use fail-closed JSON decode")
        if 'context="nft_token"' not in rocks_py:
            errors.append("rocks_store nft_token decode must use fail-closed JSON decode")
        # get_meta corrupt path must return default, not garbage string
        if "Fail-closed: never return a garbage string as valid meta" not in rocks_py:
            errors.append("rocks_store get_meta must return default on corrupt decode")
    except Exception as exc:
        errors.append(f"fail-loud rocks point-get inspect failed: {exc}")
    try:
        alerts = (ROOT / "deploy" / "prometheus" / "alerts.yml").read_text(encoding="utf-8")
        if "AbsoluteP2PBroadcastFailBurst" not in alerts:
            errors.append("alerts.yml missing AbsoluteP2PBroadcastFailBurst")
        if "AbsoluteP2PPeerSyncFailBurst" not in alerts:
            errors.append("alerts.yml missing AbsoluteP2PPeerSyncFailBurst")
        if "AbsoluteP2PCatchUpLoopFailBurst" not in alerts:
            errors.append("alerts.yml missing AbsoluteP2PCatchUpLoopFailBurst")
    except Exception as exc:
        errors.append(f"fail-loud broadcast alert inspect failed: {exc}")
    try:
        main_py = (ROOT / "main.py").read_text(encoding="utf-8")
        if "forge still uses blockchain.create_block — not wired" not in main_py:
            errors.append("BlockBuilder must not advertise enabled when forge path is unwired")
    except Exception as exc:
        errors.append(f"fail-loud BlockBuilder honesty inspect failed: {exc}")
    try:
        http_py = (ROOT / "api" / "http.py").read_text(encoding="utf-8")
        if "consensus_adapter_missing" not in http_py:
            errors.append("/consensus/attestations must surface consensus_adapter_missing")
        if "slashing_engine_missing" not in http_py:
            errors.append("/slashing/status must surface slashing_engine_missing")
        if "sharding_missing" not in http_py:
            errors.append("/sharding/pending must surface sharding_missing")
        if "immutable_state_missing" not in http_py:
            errors.append("/state/stats|/state/all must surface immutable_state_missing")
        if "smart_accounts_missing" not in http_py:
            errors.append("unbound smart-account endpoints must surface smart_accounts_missing")
        if "sync_engine_missing" not in http_py:
            errors.append("/sync/peers must surface sync_engine_missing")
        if "contract_manager_missing" not in http_py:
            errors.append("/contracts must surface contract_manager_missing")
        if "peer_count > 0 and not sync_engine_bound" not in http_py:
            errors.append("/status must degrade when peers present without SyncEngine")
        if 'mode in ("prod", "production", "staging")' not in http_py:
            errors.append("eth_mining must refuse prod claim without P2P")
        if 'raise ValueError("eth filters unavailable")' not in http_py:
            errors.append("eth_getFilterChanges/Logs must raise when filters unbound")
        if '"websocket_send_failures"' not in http_py:
            errors.append("/status subsystems must expose websocket_send_failures")
    except Exception as exc:
        errors.append(f"fail-loud api missing-error inspect failed: {exc}")
    try:
        ws_py = (ROOT / "network" / "websocket.py").read_text(encoding="utf-8")
        if "broadcast send failed" not in ws_py:
            errors.append("WebSocket _broadcast must count/log send failures")
        if "Fail-closed: bind/runtime failure must not leave a live flag" not in ws_py:
            errors.append("WebSocket start must clear _running on bind/runtime failure")
        mh_py = (ROOT / "network" / "p2p" / "message_handler.py").read_text(encoding="utf-8")
        if "_send_failures" not in mh_py or "_send_unbound" not in mh_py:
            errors.append("legacy MessageHandler._send must count unbound/send failures")
        clone_py = (ROOT / "storage" / "chain_clone.py").read_text(encoding="utf-8")
        if "Fail-closed: when RocksEngine is available" not in clone_py:
            errors.append("chain_clone must fail-closed on Rocks checkpoint when native present")
        db_py = (ROOT / "storage" / "database.py").read_text(encoding="utf-8")
        if "_loads_json_or_none" not in db_py or "json_decode_failures" not in db_py:
            errors.append("SQLite Database must fail-closed JSON decode with counter")
        if 'context="plasma_txs"' not in db_py or 'context="nft_token_meta"' not in db_py:
            errors.append("SQLite feature tables must use counted JSON decode")
        amount_py = (ROOT / "runtime" / "amount.py").read_text(encoding="utf-8")
        if "_native_fallback" not in amount_py or "REQUIRE_NATIVE_CRYPTO" not in amount_py:
            errors.append("amount.py must fail-closed when REQUIRE_NATIVE_CRYPTO is set")
        p2p_py = (ROOT / "network" / "p2p_node.py").read_text(encoding="utf-8")
        if "expected = max(1, mesh_min)" not in p2p_py:
            errors.append("topology_healthy must require peers in prod/staging")
        hyb_py = (ROOT / "storage" / "hybrid_database.py").read_text(encoding="utf-8")
        if "skipped_corrupt" not in hyb_py:
            errors.append("hybrid aux migrate must skip corrupt JSON without inventing empties")
        if "aux_json_decode_failures" not in hyb_py:
            errors.append("hybrid get_stats must expose aux_json_decode_failures")
        backup_py = (ROOT / "storage" / "chain_backup.py").read_text(encoding="utf-8")
        if "never invent tip 0 as success" not in backup_py:
            errors.append("read_chain_tip must fail-closed on corrupt/missing storage")
        metrics_py = (ROOT / "observability" / "metrics.py").read_text(encoding="utf-8")
        if "abs_sqlite_json_decode_failures" not in metrics_py:
            errors.append("metrics must export abs_sqlite_json_decode_failures")
        if "abs_ws_send_failures_total" not in metrics_py:
            errors.append("metrics must export abs_ws_send_failures_total")
        alerts = (ROOT / "deploy" / "prometheus" / "alerts.yml").read_text(encoding="utf-8")
        if "AbsoluteSqliteJsonDecodeFailures" not in alerts:
            errors.append("alerts.yml missing AbsoluteSqliteJsonDecodeFailures")
        if "AbsoluteWSSendFailBurst" not in alerts:
            errors.append("alerts.yml missing AbsoluteWSSendFailBurst")
        if 'checks["websocket_running"]' not in (
            (ROOT / "api" / "http.py").read_text(encoding="utf-8")
        ):
            errors.append("/health/ready prod must check websocket_running")
        http_py2 = (ROOT / "api" / "http.py").read_text(encoding="utf-8")
        if "lightning_missing" not in http_py2 or "plasma_missing" not in http_py2:
            errors.append("L2 unbound endpoints must surface lightning_missing/plasma_missing")
        if "wasm_missing" not in http_py2:
            errors.append("WASM unbound endpoints must surface wasm_missing")
        if "p2p_missing" not in http_py2:
            errors.append("/network/stats must surface p2p_missing")
        if "proof_ok = bridge_on and oracle_on and rust_path and rpc_on" not in http_py2:
            errors.append("bridge relayer proof_ok must require eth RPC configured")
        if 'raise ValueError("corrupt account storage")' not in http_py2:
            errors.append("eth_getStorageAt must fail on corrupt account storage")
        if "feature_degraded" not in http_py2:
            errors.append("/status must degrade when feature_init_errors present")
        main_py2 = (ROOT / "main.py").read_text(encoding="utf-8")
        if "feature_init_errors" not in main_py2:
            errors.append("main.py must track feature_init_errors on optional module init fail")
        adapter_py = (ROOT / "consensus" / "adapter.py").read_text(encoding="utf-8")
        if "_casper_ingest_fail" not in adapter_py or "casper_ingest_fail" not in adapter_py:
            errors.append("consensus adapter must count casper/beacon ingest failures")
        if '"healthy": ingest_fail == 0' not in adapter_py:
            errors.append("casper/beacon healthy must require zero ingest_fail")
        sync_py = (ROOT / "sync" / "sync_engine.py").read_text(encoding="utf-8")
        if "never leave is_syncing stuck" not in sync_py:
            errors.append("SyncEngine.fast_sync must clear is_syncing in finally")
        if "sync_fail" not in sync_py or "last_sync_error" not in sync_py:
            errors.append("SyncEngine status must expose sync_fail/last_sync_error")
        p2p_py2 = (ROOT / "network" / "p2p_node.py").read_text(encoding="utf-8")
        if "chain_compatible" not in p2p_py2 or "transport_healthy" not in p2p_py2:
            errors.append("P2P topology must separate transport_healthy and chain_compatible")
        oracle_py = (ROOT / "features" / "oracle_registry.py").read_text(encoding="utf-8")
        if "oracle signature required" not in oracle_py:
            errors.append("oracle submit_report must require signature when secret set")
        if "One vote per reporter" not in oracle_py:
            errors.append("oracle aggregate must dedupe reporters")
        bridge_py = (ROOT / "bridge" / "abs_bridge.py").read_text(encoding="utf-8")
        if "_rust_decode_fail" not in bridge_py or "get_ops_errors" not in bridge_py:
            errors.append("RustBridge must expose decode/timeout ops error counters")
        mev_py = (ROOT / "features" / "mev_analyzer.py").read_text(encoding="utf-8")
        if "heuristic_signals" not in mev_py:
            errors.append("MEV stats must expose heuristic_signals honesty labels")
        ai_py = (ROOT / "features" / "ai_manager.py").read_text(encoding="utf-8")
        if "model_bound" not in ai_py or "executor_bound" not in ai_py:
            errors.append("AI manager must expose model_bound/executor_bound")
        will_py = (ROOT / "features" / "crypto_will.py").read_text(encoding="utf-8")
        if "create persist failed, refunded" not in will_py:
            errors.append("CryptoWill create must refund on persist failure")
        l1_rpc_py = (ROOT / "bridge" / "l1_rpc.py").read_text(encoding="utf-8")
        if "_receipt_status_ok" not in l1_rpc_py or "status-less" not in l1_rpc_py:
            errors.append("L1 RPC confirmations must require successful receipt status")
        evm_ad = (ROOT / "execution" / "evm_adapter.py").read_text(encoding="utf-8")
        if "_loads_contract_storage" not in evm_ad or "corrupt_storage" not in evm_ad:
            errors.append("EVM adapter must fail-closed on corrupt contract storage")
        if "static_create_rejected" not in evm_ad or "read_only=True" not in evm_ad:
            errors.append("EVM static_call must reject nested CREATE and use read_only")
        if "force will execute forbidden in prod" not in http_py2:
            errors.append("/will/execute must reject force in prod")
        if '"execution_bound": False' not in http_py2 or "in_memory_registry" not in http_py2:
            errors.append("multisig list must expose execution_bound/persistent honesty")
        nft_py = (ROOT / "features" / "nft.py").read_text(encoding="utf-8")
        if "on_chain_standard" not in nft_py or "execution_bound" not in nft_py:
            errors.append("NFT get_stats must expose execution_bound honesty labels")
        if "feature_nft" not in main_py2 or "NFT Marketplace: disabled" not in main_py2:
            errors.append("main.py must gate NFT on feature_nft")
        pq_py = (ROOT / "features" / "postquantum.py").read_text(encoding="utf-8")
        if "educational_only" not in pq_py or "nist_ml_dsa" not in pq_py:
            errors.append("PQ get_stats must expose educational capability matrix")
        if "FEATURE_NFT" not in (ROOT / "runtime" / "config.py").read_text(encoding="utf-8"):
            errors.append("config must include FEATURE_NFT prod block")
        if "force plasma finalize forbidden in prod" not in http_py2:
            errors.append("/plasma/finalize-exit must reject force in prod")
        if "claim_and_credit_bridge_event" not in (
            ROOT / "storage" / "database.py"
        ).read_text(encoding="utf-8"):
            errors.append("SQLite must provide claim_and_credit_bridge_event")
        bridge_py2 = (ROOT / "bridge" / "abs_bridge.py").read_text(encoding="utf-8")
        if "l1_event_bound" not in bridge_py2 or "replay_key" not in bridge_py2:
            errors.append("RustBridge stats must expose l1_event_bound / replay_key honesty")
        if "from_chain:event_tx_hash:log_index" not in bridge_py2:
            errors.append("bridge confirm_incoming must use event-derived replay key")
        if "debit_and_create_bridge_lock" not in bridge_py2:
            errors.append("lock_and_bridge must use debit_and_create_bridge_lock")
        if '"to_chain": self._normalize_chain(lock.get("to_chain", ""))' not in bridge_py2:
            errors.append("confirm_lock must pass lock to_chain to Rust L1 verify")
        if "BRIDGE_REQUIRE_L1_EVENT" not in bridge_py2 or "BRIDGE_L1_LOCK_CONTRACT" not in bridge_py2:
            errors.append("Rust subprocess env must forward L1 event binding settings")
        rust_main = (ROOT / "bridge" / "rust_bridge" / "src" / "main.rs").read_text(encoding="utf-8")
        if "receipt_status_ok" not in rust_main:
            errors.append("Rust bridge must require successful receipt status")
        if '"lock" | "bridge"' not in rust_main:
            errors.append("Rust bridge must verify L1 for lock/bridge commands")
        if "BRIDGE_REQUIRE_L1_EVENT" not in rust_main or "receipt_has_contract_log" not in rust_main:
            errors.append("Rust bridge must support BRIDGE_REQUIRE_L1_EVENT contract log binding")
        if "feature_smart_accounts" not in main_py2:
            errors.append("main.py must gate Smart Accounts on feature_smart_accounts")
        sa_py = (ROOT / "features" / "smart_accounts.py").read_text(encoding="utf-8")
        if "execution_bound" not in sa_py or "in_memory_registry" not in sa_py:
            errors.append("SmartAccountManager stats must expose execution_bound honesty")
        if "feature_minivm" not in main_py2 or "MiniVM: disabled" not in main_py2:
            errors.append("main.py must gate MiniVM on feature_minivm")
        if "unsigned DAO vote forbidden in prod" not in http_py2:
            errors.append("/pools/dao/vote must reject unsigned votes in prod")
        if "multi-hop lightning routing not implemented" not in http_py2:
            errors.append("/lightning/route must reject multi-hop until implemented")
        if "private keys in query forbidden" not in http_py2:
            errors.append("GET /zk/transaction must forbid private keys in query")
        if "zk_missing" not in http_py2:
            errors.append("ZK prove/range must not invent arithmetic validity when ZK missing")
        ln_py = (ROOT / "features" / "lightning.py").read_text(encoding="utf-8")
        if '"routing_enabled": False' not in ln_py or "direct_channel_only" not in ln_py:
            errors.append("Lightning stats must not claim multi-hop routing_enabled")
        if "FEATURE_MINIVM" not in (ROOT / "runtime" / "config.py").read_text(encoding="utf-8"):
            errors.append("config must include FEATURE_MINIVM prod block")
        if "heuristic_low_risk" not in (
            ROOT / "features" / "reorg_predictor.py"
        ).read_text(encoding="utf-8"):
            errors.append("reorg predictor must not emit reserved finalized heuristic label")
        if 'return "finalized"' in (
            ROOT / "features" / "reorg_predictor.py"
        ).read_text(encoding="utf-8"):
            errors.append("reorg predictor still returns finalized confidence label")
        if "standalone_observer" not in http_py2:
            errors.append("/finality/stats must label standalone_observer")
        if "finality_engine_standalone_observer" not in http_py2:
            errors.append("/status must expose finality_engine_standalone_observer")
        if "wasm_operational" not in http_py2:
            errors.append("/status must expose wasm_operational separately from wasm registry")
        wasm_py = (ROOT / "features" / "wasm_vm.py").read_text(encoding="utf-8")
        if "wasmtime_available" not in wasm_py or "pseudo_token_host" not in wasm_py:
            errors.append("WASM get_stats must expose wasmtime_available / pseudo_token_host")
        if "Binary WASM requires wasmtime" not in wasm_py:
            errors.append("WASM deploy must reject binary modules without wasmtime")
        if "deterministic_hash_selection" not in main_py2:
            errors.append("main.py must not greenwash ValidatorSelection as RANDAO")
        if "FEATURE_VALIDATOR_SELECTION" not in (
            ROOT / "runtime" / "config.py"
        ).read_text(encoding="utf-8"):
            errors.append("config must include FEATURE_VALIDATOR_SELECTION")
        chain_st = (ROOT / "storage" / "chain_storage.py").read_text(encoding="utf-8")
        if "abs_chain_replace_" not in chain_st or "os.rename(tmp_blocks" not in chain_st:
            errors.append("ChainStorage.replace_chain must atomically swap temp blocks dir")
        # v1.3.37 — bridge L1 proof / blind confirm / light / PBS / AI honesty
        cfg_py = (ROOT / "runtime" / "config.py").read_text(encoding="utf-8")
        if "env cannot weaken L1 proof requirement" not in cfg_py:
            errors.append("prod config must forbid BRIDGE_REQUIRE_L1_PROOF=false via env")
        if "FEATURE_AI_VALIDATOR" not in cfg_py:
            errors.append("config must include FEATURE_AI_VALIDATOR")
        relayer_py = (ROOT / "scripts" / "bridge_relayer.py").read_text(encoding="utf-8")
        if "refusing --allow-blind-confirm against prod API" not in relayer_py:
            errors.append("bridge_relayer must hard-fail --allow-blind-confirm on prod API")
        light_py = (ROOT / "light" / "light_client.py").read_text(encoding="utf-8")
        if "require_trusted_anchor" not in light_py or "trusted_local_replay" not in light_py:
            errors.append("light client must reject unanchored peer bootstrap")
        if "peer_import_requires_trusted_anchor" not in light_py:
            errors.append("light get_stats must expose peer_import_requires_trusted_anchor")
        pbs_py = (ROOT / "consensus" / "pbs.py").read_text(encoding="utf-8")
        if '"mev_protection": False' not in pbs_py or '"ordering_applied": False' not in pbs_py:
            errors.append("PBS must label mev_protection/ordering_applied false")
        if "PBS auction (MEV protection)" in main_py2 or "PBS handles protection" in main_py2:
            errors.append("main.py must not claim PBS MEV protection")
        if "feature_ai_validator" not in main_py2:
            errors.append("main.py must gate AIValidatorEngine on feature_ai_validator")
        ai_py = (ROOT / "features" / "ai_validator.py").read_text(encoding="utf-8")
        if "invented_numbers" not in ai_py or "consensus_wired" not in ai_py:
            errors.append("AI validator must expose simulation honesty (no invented MEV numbers)")
        if "random.uniform" in ai_py and "detect_mev_opportunity" in ai_py:
            # Fail if invented MEV numbers remain inside detect_mev_opportunity body.
            start = ai_py.find("def detect_mev_opportunity")
            end = ai_py.find("\n    def ", start + 1)
            body = ai_py[start:end] if start >= 0 else ai_py
            if "random.uniform" in body:
                errors.append("AI validator must not invent MEV profit/probability via random.uniform")
        if "consensus_wired" not in http_py2 or "model_bound" not in http_py2:
            errors.append("/ai/* API must expose consensus_wired / model_bound honesty")
        # v1.3.38 — native GHOST + simple block apply/replay
        ghost_py = (ROOT / "consensus" / "ghost.py").read_text(encoding="utf-8")
        if "ghost_select_head" not in ghost_py or "ghost_cumulative_weight" not in ghost_py:
            errors.append("ghost.py must route fork-choice to abs_native kernels")
        bc_py = (ROOT / "core" / "blockchain.py").read_text(encoding="utf-8")
        state_svc_py = (ROOT / "core" / "components" / "state_service.py").read_text(
            encoding="utf-8"
        )
        if "blockchain_apply_simple_block" not in main_py2 and (
            "blockchain_apply_simple_block" not in bc_py
            and "blockchain_apply_simple_block" not in state_svc_py
        ):
            errors.append("blockchain.py must wire blockchain_apply_simple_block")
        if "_apply_simple_block_native" not in bc_py and "_apply_simple_block_native" not in state_svc_py:
            errors.append("blockchain must expose native simple apply/replay helpers")
        if "_replay_simple_range_native" not in bc_py and "_replay_simple_range_native" not in state_svc_py:
            errors.append("blockchain must expose native simple apply/replay helpers")
        if (
            '"amount_satoshi"' not in state_svc_py
            or "resolve_tx_value_satoshi" not in state_svc_py
            or "value_satoshi=" not in state_svc_py
        ):
            errors.append(
                "state_service native apply must bind amount_satoshi / value_satoshi (ADR 0021)"
            )
        mk_rs = ROOT / "native" / "abs_native" / "src" / "mempool_kernel.rs"
        if not mk_rs.is_file():
            errors.append("mempool_kernel.rs missing (ADR 0021 phase-1)")
        else:
            mk_txt = mk_rs.read_text(encoding="utf-8", errors="replace")
            for needle in (
                "fn mempool_validate_post_sig",
                "fn mempool_admit_evm_deploy",
                "insufficient_balance",
                "nonce_mismatch",
                "validate_post_sig_inner",
                "admit_evm_deploy_inner",
            ):
                if needle not in mk_txt:
                    errors.append(f"mempool_kernel.rs missing {needle}")
        if not (ROOT / "docs" / "adr" / "0021-mempool-validation-rust-phases.md").is_file():
            errors.append("ADR 0021 mempool-validation-rust-phases missing")
        mempool_ports = ROOT / "blockchain" / "ports.py"
        if not mempool_ports.is_file():
            errors.append("blockchain/ports.py MempoolPort missing (ADR 0021 phase-0)")
        elif "class MempoolPort" not in mempool_ports.read_text(encoding="utf-8"):
            errors.append("blockchain/ports.py must define MempoolPort")
        tx_ports = ROOT / "core" / "components" / "ports.py"
        if not tx_ports.is_file() or "class TxPipelinePort" not in tx_ports.read_text(
            encoding="utf-8"
        ):
            errors.append("core/components/ports.py TxPipelinePort missing (ADR 0021)")
        ms_rs = ROOT / "native" / "abs_native" / "src" / "mempool_store.rs"
        if not ms_rs.is_file():
            errors.append("mempool_store.rs missing (ADR 0021 phase-2)")
        else:
            ms_txt = ms_rs.read_text(encoding="utf-8", errors="replace")
            for needle in (
                "struct MempoolStore",
                "fn insert",
                "fn get_sorted",
                "cleanup_cheapest_10pct",
                "fee_satoshi",
                "min_fee_satoshi",
            ):
                if needle not in ms_txt:
                    errors.append(f"mempool_store.rs missing {needle}")
        mempool_py_adr = (ROOT / "blockchain" / "mempool.py").read_text(
            encoding="utf-8", errors="replace"
        )
        if "create_mempool_store" not in mempool_py_adr:
            errors.append("blockchain/mempool.py must wire create_mempool_store (ADR 0021 phase-2)")
        if "store_backend" not in mempool_py_adr:
            errors.append("mempool get_stats must expose store_backend (ADR 0021 phase-2)")
        native_py_adr = (ROOT / "crypto" / "native.py").read_text(
            encoding="utf-8", errors="replace"
        )
        if "def mempool_validate_post_sig" not in native_py_adr:
            errors.append("crypto/native.py must export mempool_validate_post_sig (ADR 0021)")
        if "def create_mempool_store" not in native_py_adr:
            errors.append("crypto/native.py must export create_mempool_store (ADR 0021 phase-2)")
        if "def mempool_admit_evm_deploy" not in native_py_adr:
            errors.append("crypto/native.py must export mempool_admit_evm_deploy (ADR 0021 phase-3)")
        caps_py = (ROOT / "runtime" / "native_capabilities.py").read_text(
            encoding="utf-8", errors="replace"
        )
        if 'MEMPOOL_KERNEL = "mempool_kernel"' not in caps_py:
            errors.append("NativeFamily.MEMPOOL_KERNEL missing (ADR 0021 / ADR 0009)")
        if 'MEMPOOL_STORE = "mempool_store"' not in caps_py:
            errors.append("NativeFamily.MEMPOOL_STORE missing (ADR 0021 phase-2 / ADR 0009)")
        pipe_py = (ROOT / "core" / "components" / "tx_pipeline.py").read_text(
            encoding="utf-8", errors="replace"
        )
        if "_post_sig_kernel_check" not in pipe_py or "mempool_validate_post_sig" not in pipe_py:
            errors.append("TxPipeline must wire mempool_validate_post_sig after sig (ADR 0021)")
        if "mempool_admit_evm_deploy" not in pipe_py:
            errors.append("TxPipeline must wire mempool_admit_evm_deploy (ADR 0021 phase-3)")
        fixtures_dir = ROOT / "tests" / "fixtures" / "adr0021_phase1"
        if not (fixtures_dir / "kernel_input_accept.json").is_file():
            errors.append("ADR 0021 phase-1 golden fixtures missing")
        if not (ROOT / "tests" / "unit" / "test_adr0021_phase1_fixtures.py").is_file():
            errors.append("test_adr0021_phase1_fixtures.py missing")
        if not (ROOT / "tests" / "unit" / "test_adr0021_phase2_store.py").is_file():
            errors.append("test_adr0021_phase2_store.py missing (ADR 0021 phase-2)")
        if not (ROOT / "tests" / "unit" / "test_mempool_port.py").is_file():
            errors.append("test_mempool_port.py missing (ADR 0021 phase-0)")
        if not (ROOT / "scripts" / "verify_adr0021_phase1.py").is_file():
            errors.append("scripts/verify_adr0021_phase1.py missing (operator self-check)")
        lib_rs_txt = (ROOT / "native" / "abs_native" / "src" / "lib.rs").read_text(
            encoding="utf-8", errors="replace"
        )
        if "mempool_kernel" not in lib_rs_txt:
            errors.append("lib.rs must register mempool_kernel module")
        if "mempool_store" not in lib_rs_txt:
            errors.append("lib.rs must register mempool_store module (ADR 0021 phase-2)")
        amt_rs = (ROOT / "native" / "abs_native" / "src" / "amount.rs").read_text(
            encoding="utf-8", errors="replace"
        )
        if "must be integer satoshi" not in amt_rs:
            errors.append("amount.rs must refuse float satoshi fields (native hygiene)")
        if "to_f64().unwrap_or(0.0)" in amt_rs:
            errors.append("amount.rs must not paint satoshi→float failure as 0.0")
        http_py_money = (ROOT / "api" / "http.py").read_text(
            encoding="utf-8", errors="replace"
        )
        if "WireMoneyMismatch" not in http_py_money:
            errors.append("api/http.py must remap WireMoneyMismatch (ADR 0021)")
        if "mempool_store_demoted" not in http_py_money:
            errors.append("/status must degrade when mempool_store demoted in prod+require_native")
        types_py = (ROOT / "storage" / "types.py").read_text(
            encoding="utf-8", errors="replace"
        )
        if "class PersistError" not in types_py:
            errors.append("storage.types must define PersistError (persist fail-closed)")
        wb_rs = (ROOT / "native" / "abs_native" / "src" / "evm_writeback.rs").read_text(
            encoding="utf-8", errors="replace"
        )
        if "balance_satoshi must be integer" not in wb_rs:
            errors.append("evm_writeback must refuse float balance_satoshi")
        if "f * 1_000_000.0" in wb_rs or "(sat as f64) / 1_000_000.0" in wb_rs:
            errors.append("evm_writeback must not use IEEE×1e6 money path")
        xshard = (ROOT / "consensus" / "cross_shard_coordinator.py").read_text(
            encoding="utf-8", errors="replace"
        )
        if "balance_satoshi_required" not in xshard or "get_balance_satoshi_required" not in xshard:
            errors.append("cross_shard migration must require balance_satoshi (ADR 0021)")
        shard_py = (ROOT / "dynamic_sharding.py").read_text(encoding="utf-8", errors="replace")
        if "allow_float_fallback=False" not in shard_py or "amount_satoshi" not in shard_py:
            errors.append("dynamic_sharding must use satoshi ledger (ADR 0021)")
        for rel, label in (
            ("storage/rocks_store.py", "rocks_store"),
            ("storage/database.py", "database"),
            ("storage/chain_storage.py", "chain_storage"),
        ):
            src = (ROOT / rel).read_text(encoding="utf-8", errors="replace")
            if "raise PersistError" not in src:
                errors.append(f"{label} must raise PersistError on hot persist failure")
        backup_rocks = (ROOT / "storage" / "rocks_store.py").read_text(
            encoding="utf-8", errors="replace"
        )
        backup_db = (ROOT / "storage" / "database.py").read_text(
            encoding="utf-8", errors="replace"
        )
        for label, src in (("rocks_store.backup_to", backup_rocks), ("database.backup_to", backup_db)):
            chunk = src.split("def backup_to", 1)[1].split("\n    def ", 1)[0]
            if "raise PersistError" not in chunk:
                errors.append(f"{label} must raise PersistError (fail-closed backup)")
            if "return False" in chunk:
                errors.append(f"{label} must not soft-return False")
        chain_bak = (ROOT / "storage" / "chain_backup.py").read_text(
            encoding="utf-8", errors="replace"
        )
        if "never silent copy2 of a live DB" not in chain_bak:
            errors.append("chain_backup must refuse silent copy2 fallback for live SQLite")
        if 'if hasattr(db, "backup_to") and not db.backup_to' in chain_bak:
            errors.append("chain_backup must not soft-fallback copy2 after backup_to False")
        if not (ROOT / "tests" / "unit" / "test_persist_fail_closed.py").is_file():
            errors.append("test_persist_fail_closed.py missing")
        amount_py_wb = (ROOT / "runtime" / "amount.py").read_text(
            encoding="utf-8", errors="replace"
        )
        if "def writeback_balance_abs" not in amount_py_wb:
            errors.append("runtime.amount must define writeback_balance_abs for EVM writeback")
        evm_ad_py = (ROOT / "execution" / "evm_adapter.py").read_text(
            encoding="utf-8", errors="replace"
        )
        if "writeback_balance_abs" not in evm_ad_py:
            errors.append("evm_adapter must use writeback_balance_abs (not float balance paint)")
        if "evm_native_writeback_required" not in evm_ad_py:
            errors.append("evm_adapter must refuse native writeback fallback in prod/require_native")
        if 'p2p_mempool_require_explicit_gas: bool = True' not in (
            ROOT / "runtime" / "config.py"
        ).read_text(encoding="utf-8", errors="replace"):
            errors.append("config must define p2p_mempool_require_explicit_gas")
        ln_stats = (ROOT / "features" / "lightning.py").read_text(
            encoding="utf-8", errors="replace"
        )
        pl_stats = (ROOT / "features" / "plasma.py").read_text(
            encoding="utf-8", errors="replace"
        )
        if '"execution_bound"' not in ln_stats or '"execution_bound"' not in pl_stats:
            errors.append("lightning/plasma get_stats must expose execution_bound")
        if "_tx_affordable_sat" not in (
            ROOT / "execution" / "block_builder.py"
        ).read_text(encoding="utf-8"):
            errors.append("BlockBuilder must afford via satoshi (not float gasPrice*gas)")
        if "gas_limit_required" not in (
            ROOT / "core" / "tx_builder.py"
        ).read_text(encoding="utf-8"):
            errors.append("TransactionBuilder must refuse invent gas_limit=21000")
        if "stake_required" not in (
            ROOT / "consensus" / "slashing.py"
        ).read_text(encoding="utf-8"):
            errors.append("SlashingEngine.register_validator must refuse invent stake=100")
        evm_ad_py = (ROOT / "execution" / "evm_adapter.py").read_text(
            encoding="utf-8", errors="replace"
        )
        if "_resolve_call_value_sat" not in evm_ad_py:
            errors.append("evm_adapter must resolve call/deploy value in satoshi")
        if "wei_to_abs = value_wei / 10**18" in evm_ad_py:
            errors.append("evm_adapter nested writeback must not transfer via wei/1e18 float")
        if "int(value * 10**18)" in evm_ad_py:
            errors.append("evm_adapter must not convert ABS float to wei via *1e18")
        if "satoshi_store_required_selfdestruct" not in evm_ad_py:
            errors.append("evm_adapter SELFDESTRUCT must refuse float store")
        est_idx = evm_ad_py.find("def estimate_gas")
        est_fn = evm_ad_py[est_idx : est_idx + 500] if est_idx >= 0 else ""
        if "return None" not in est_fn:
            errors.append(
                "evm_adapter.estimate_gas must return None on failed dry-run (not invent gas_limit)"
            )
        if "gas_used * 1.2" in est_fn or "float(" in est_fn:
            errors.append(
                "evm_adapter.estimate_gas must use integer buffer (no float * 1.2)"
            )
        if not (ROOT / "execution" / "evm_precompiles.py").is_file():
            errors.append("execution/evm_precompiles.py missing (0x01–0x09 subset)")
        if "_precompile_gas_outcome" not in evm_ad_py:
            errors.append("EVM adapter must cap/burn precompile gas (geth CALL semantics)")
        if "_precompile_nested_call" not in evm_ad_py:
            errors.append("EVM nested precompile OOG must burn forwarded gas")
        if "get_balance(addr) * 10**18" in evm_ad_py.replace(" ", ""):
            errors.append("evm_adapter BALANCE must not use float get_balance*1e18")
        if "get_balance_satoshi" not in evm_ad_py or "WEI_PER_SATOSHI" not in evm_ad_py:
            errors.append("evm_adapter BALANCE must use get_balance_satoshi * WEI_PER_SATOSHI")
        sign_py = (ROOT / "crypto" / "signing.py").read_text(
            encoding="utf-8", errors="replace"
        )
        if "gas_limit_required" not in sign_py or "gas_price_required" not in sign_py:
            errors.append("crypto.signing must refuse invent gas_limit=21000 / gas_price=1")
        if '"gas_limit": 21000' in sign_py:
            errors.append("crypto.signing must not hardcode gas_limit=21000")
        wallet_py = (ROOT / "crypto" / "wallet.py").read_text(
            encoding="utf-8", errors="replace"
        )
        if "plaintext wallet export refused" not in wallet_py:
            errors.append("Wallet.export must refuse bare plaintext without allow_plaintext")
        if "plaintext wallet import refused" not in wallet_py:
            errors.append("Wallet.import_wallet must refuse bare plaintext without allow_plaintext")
        http_gate = (ROOT / "api" / "http.py").read_text(
            encoding="utf-8", errors="replace"
        )
        if '"/pq/keygen"' not in http_gate:
            errors.append("prod must block POST /pq/keygen")
        if "legacy invent-price path removed" not in http_gate:
            errors.append("/nft/mint-legacy must be 410 tombstone")
        if '"fee_satoshi": fee_sat' not in http_gate and '"fee_satoshi": int(est.get("fee_satoshi"' not in http_gate:
            errors.append("/bridge2/fee must emit fee_satoshi")
        main_boot = (ROOT / "main.py").read_text(encoding="utf-8", errors="replace")
        if "stake_satoshi=_min_stake_sat" not in main_boot:
            errors.append("boot add_validator must pass stake_satoshi")
        if "except TypeError:" in http_gate and "endswith(\"_satoshi\")" in http_gate:
            errors.append("http must not soft-drop *_satoshi kwargs on TypeError")
        if 'amount, amount_sat = 0.0, 0' in http_gate:
            errors.append("l1-register must not invent amount=0 on ValueError")
        if "use POST /nft/list with price_satoshi" not in http_gate:
            errors.append("/nft/list-legacy must be 410 tombstone")
        rocks_live = (ROOT / "storage" / "rocks_store.py").read_text(
            encoding="utf-8", errors="replace"
        )
        if "corrupt live_state_root_height meta" not in rocks_live:
            errors.append("rocks get_live_state_root_meta must warn on corrupt height")
        qf_py = (ROOT / "api" / "query_facade.py").read_text(
            encoding="utf-8", errors="replace"
        )
        if "canonical_balance_satoshi(store, address)" not in qf_py:
            errors.append("QueryFacade.get_balance_satoshi must use canonical_balance_satoshi")
        bft_svc = (ROOT / "consensus" / "bft" / "service.py").read_text(
            encoding="utf-8", errors="replace"
        )
        if "mark_slashed failed" in bft_svc:
            after = bft_svc.split("mark_slashed failed", 1)[1][:80]
            if "raise" not in after:
                errors.append("RoundSM must re-raise after mark_slashed failure")
        if "lockdown failed" in bft_svc:
            after_l = bft_svc.split("lockdown failed", 1)[1][:120]
            if "raise" not in after_l:
                errors.append("RoundSM must re-raise after lockdown failure")
        if "if is_prod:" not in http_gate or 'return ""' not in http_gate:
            # Defense-in-depth: prod must refuse CORS *
            cors_fn = ""
            if "def _resolve_cors_allow_origin" in http_gate:
                cors_fn = http_gate.split("def _resolve_cors_allow_origin", 1)[1].split(
                    "\ndef ", 1
                )[0]
            if "is_prod" not in cors_fn or 'return ""' not in cors_fn:
                errors.append("prod CORS resolver must refuse wildcard *")
        if "native engine drop failed" not in rocks_live:
            errors.append("rocks close must warn on native engine drop failure")
        if "get_account_rows failed, per-account load" not in rocks_live:
            errors.append("rocks load_writeback_accounts must warn on get_account_rows failure")
        native_py = (ROOT / "crypto" / "native.py").read_text(
            encoding="utf-8", errors="replace"
        )
        if "insufficient_writeback_value" not in native_py:
            errors.append("writeback must refuse underfunded transfer_value (no mint)")
        if "def _writeback_transfers_covered" not in native_py:
            errors.append("native must preflight writeback transfers")
        if "account_blob_to_json failed under require" not in native_py:
            errors.append("account_blob_to_row must raise under require mode")
        evm_ad_gate = (ROOT / "execution" / "evm_adapter.py").read_text(
            encoding="utf-8", errors="replace"
        )
        if "bridge_pending_writeback_failed" not in evm_ad_gate:
            errors.append("evm_adapter must fail-closed on pending writeback parse")
        slash_py = (ROOT / "consensus" / "slashing.py").read_text(
            encoding="utf-8", errors="replace"
        )
        if "Dict[int, Dict[str, str]]" not in slash_py:
            errors.append("slashing proposals must be height→validator→hash (idempotent)")
        if "Same-hash proposal retry" not in slash_py and "prior == digest" not in slash_py:
            errors.append("slashing record_proposal must accept same-hash retries")
        bc_py = (ROOT / "core" / "blockchain.py").read_text(
            encoding="utf-8", errors="replace"
        )
        if "allow_slashed=bool(preserve_peer_hash)" not in bc_py:
            errors.append("catch-up must allow_slashed for preserve_peer_hash import")
        if "Last committed canonical root" not in bc_py:
            errors.append(
                "get_state_root must return committed header/meta, not rescan accounts"
            )
        sr_idx = bc_py.find("def get_state_root")
        sr_fn = bc_py[sr_idx : sr_idx + 1400] if sr_idx >= 0 else ""
        if "return self._compute_state_root_from_db()" in sr_fn:
            errors.append(
                "get_state_root must not fall through to _compute_state_root_from_db"
            )
        if "ABS_ALLOW_DEV_ADMIN_JWT" not in http_gate:
            errors.append("non-prod admin JWT mint must require ABS_ALLOW_DEV_ADMIN_JWT")
        sphincs_py = (ROOT / "crypto" / "sphincs_plus.py").read_text(
            encoding="utf-8", errors="replace"
        )
        if "verify backend not available" not in sphincs_py:
            errors.append("SPHINCS+ verify must raise NotImplementedError (not return False)")
        # Code must not invent verify=False / blake2b qc: addresses (comments OK).
        code_lines = [
            ln
            for ln in sphincs_py.splitlines()
            if not ln.lstrip().startswith("#") and '"""' not in ln
        ]
        code_blob = "\n".join(code_lines)
        if "blake2b" in code_blob or "return False" in code_blob:
            errors.append("SPHINCS+ must not invent qc: addresses or fake verify=False")
        if '"qc:"' in code_blob or "'qc:'" in code_blob:
            errors.append("SPHINCS+ must not invent qc: addresses without real backend")
        evm_interp = (ROOT / "evm_interpreter.py").read_text(
            encoding="utf-8", errors="replace"
        )
        if "def _revert_static_write" not in evm_interp:
            errors.append("evm_interpreter must refuse STATICCALL writes (EIP-214)")
        rust_runner = (
            ROOT / "native" / "abs_native" / "src" / "evm_pure_runner.rs"
        ).read_text(encoding="utf-8", errors="replace")
        if "static_write_protection" not in rust_runner or "_abs_inline_read_only" not in rust_runner:
            errors.append("Rust EVM runner must refuse STATICCALL writes (EIP-214)")
        if "fn charge_nested_call_gas" not in rust_runner:
            errors.append("evm_pure_runner must charge all forwarded gas on nested OOG")
        if 'host["_abs_read_only"]' not in native_py:
            errors.append("evm_host_context_from_evm must copy _abs_read_only")
        create_hook = evm_ad_gate.split("def _contract_create_hook", 1)
        if len(create_hook) < 2 or "insufficient_call_value" not in create_hook[1][:2500]:
            errors.append("CREATE hook must pre-transfer endowment fail-closed")
        p2p_py = (ROOT / "network" / "p2p_node.py").read_text(
            encoding="utf-8", errors="replace"
        )
        if "mempool_dup_check_failed" not in p2p_py:
            errors.append("P2P mempool dup check must refuse on has_transaction failure")
        validators_py = (ROOT / "middleware" / "validators.py").read_text(
            encoding="utf-8", errors="replace"
        )
        if "amount_float = float(amount)" in validators_py:
            errors.append("middleware.validators must not validate amounts via float()")
        if "to_satoshi" not in validators_py:
            errors.append("middleware.validators must validate amounts via to_satoshi")
        nft_ports_gate = (ROOT / "features" / "nft_ports.py").read_text(
            encoding="utf-8", errors="replace"
        )
        if "price_satoshi" not in nft_ports_gate:
            errors.append("nft_ports must forward price_satoshi (ADR 0021)")
        if "float(price)" in nft_ports_gate and "price_satoshi" not in nft_ports_gate:
            errors.append("nft_ports must not coerce list price via float() alone")
        lightning_py = (ROOT / "features" / "lightning.py").read_text(
            encoding="utf-8", errors="replace"
        )
        if "ch.balance1 += htlc.amount" in lightning_py or "ch.balance2 += htlc.amount" in lightning_py:
            errors.append("lightning settle/refund must not float-mutate channel balances")
        if "amt_sat = int(to_satoshi(htlc.amount))" not in lightning_py:
            errors.append("lightning settle/refund must use satoshi int arithmetic")
        mev_py = (ROOT / "features" / "mev_analyzer.py").read_text(
            encoding="utf-8", errors="replace"
        )
        if '"profit_satoshi": profit_sat' not in mev_py:
            errors.append("mev_analyzer._record must dual-write profit_satoshi")
        wasm_py = (ROOT / "features" / "wasm_vm.py").read_text(
            encoding="utf-8", errors="replace"
        )
        if "allow_float_fallback=False" not in wasm_py:
            errors.append("wasm_vm deploy fee must refuse float money fallback")
        if "satoshi_store_required_dev_signer_fund" not in (
            ROOT / "main.py"
        ).read_text(encoding="utf-8", errors="replace"):
            errors.append("dev_signer fund must require balance_delta_satoshi")
        if "allow_float_fallback=False" not in (
            ROOT / "runtime" / "devnet_validators.py"
        ).read_text(encoding="utf-8", errors="replace"):
            errors.append("devnet_validators fund must refuse float money fallback")
        eth_fmt_py = (ROOT / "api" / "eth_format.py").read_text(
            encoding="utf-8", errors="replace"
        )
        if "def observed_tx_input" not in eth_fmt_py:
            errors.append("eth_format must expose observed_tx_input (null if unobserved)")
        if "def observed_block_gas_limit" not in eth_fmt_py:
            errors.append("eth_format must not invent gasLimit as Ethereum 30M")
        if 'tx.get("data", tx.get("tx_data", "0x"))' in eth_fmt_py:
            errors.append("format_tx must not default missing input to 0x")
        if "transactionIndex" not in eth_fmt_py or "query=None, bc=None" not in eth_fmt_py:
            errors.append("format_tx must observe transactionIndex via query/bc (null if unobserved)")
        if "def observed_tx_hash" not in eth_fmt_py:
            errors.append("eth_format must expose observed_tx_hash (null if unobserved)")
        if "def observed_tx_address" not in eth_fmt_py:
            errors.append("eth_format must expose observed_tx_address (null if unobserved)")
        if '"extraData": "0x"' in eth_fmt_py:
            errors.append("format_block must not hardcode extraData as empty")
        if "def block_extra_data" not in eth_fmt_py:
            errors.append("eth_format must expose extraData from the stored header")
        if (
            "blockchain_replay_simple_blocks" not in bc_py
            and "blockchain_replay_simple_blocks" not in state_svc_py
        ):
            errors.append("blockchain reorg must prefer blockchain_replay_simple_blocks")
        native_py = (ROOT / "crypto" / "native.py").read_text(encoding="utf-8")
        for sym in (
            "ghost_select_head",
            "blockchain_apply_simple_block",
            "blockchain_replay_simple_blocks",
            "lmd_compute_weights",
        ):
            if f"def {sym}" not in native_py:
                errors.append(f"crypto/native.py must export {sym}")
        # v1.3.39 — FFG finality + slashing conflict kernels
        for sym in (
            "ffg_evaluate_epoch",
            "ffg_threshold",
            "slash_check_double_vote",
            "slash_check_double_proposal",
            "fe_quorum_reached",
            "fe_can_finalize",
        ):
            if f"def {sym}" not in native_py:
                errors.append(f"crypto/native.py must export {sym} (v1.3.39)")
        if "ffg_evaluate_epoch" not in (
            ROOT / "consensus" / "finality_casper.py"
        ).read_text(encoding="utf-8"):
            errors.append("finality_casper.py must route to ffg_evaluate_epoch")
        if "slash_check_double_vote" not in (
            ROOT / "consensus" / "slashing.py"
        ).read_text(encoding="utf-8"):
            errors.append("slashing.py must route to slash_check_double_vote")
        if "fe_quorum_reached" not in (
            ROOT / "finality_engine.py"
        ).read_text(encoding="utf-8"):
            errors.append("finality_engine.py must route to fe_quorum_reached")
        ffg_rs = ROOT / "native" / "abs_native" / "src" / "consensus_ffg.rs"
        if not ffg_rs.is_file():
            errors.append("native consensus_ffg.rs missing")
        # v1.3.40 — eth raw tx decode kernel
        for sym in ("decode_eth_raw_tx", "decode_eth_raw_tx_hex"):
            if f"def {sym}" not in native_py:
                errors.append(f"crypto/native.py must export {sym} (v1.3.40)")
        eth_tx_py = (ROOT / "crypto" / "eth_tx.py").read_text(encoding="utf-8")
        if "decode_eth_raw_tx" not in eth_tx_py:
            errors.append("eth_tx.py must prefer decode_eth_raw_tx native path")
        eth_tx_rs = ROOT / "native" / "abs_native" / "src" / "eth_tx.rs"
        if not eth_tx_rs.is_file():
            errors.append("native eth_tx.rs missing")
        # v1.3.41 — EVM host storage snapshot around runner
        for sym in ("evm_host_snapshot_storage", "evm_host_restore_storage"):
            if f"def {sym}" not in native_py:
                errors.append(f"crypto/native.py must export {sym} (v1.3.41)")
        interp = (ROOT / "evm_interpreter.py").read_text(encoding="utf-8")
        if "_take_host_storage_snap" not in interp or "evm_host_snapshot_storage" not in interp:
            errors.append("evm_interpreter must snapshot host storage around execute")
        adapter = (ROOT / "execution" / "evm_adapter.py").read_text(encoding="utf-8")
        if 'if not result.get("reverted"):' not in adapter:
            errors.append("evm_adapter must fail-closed writeback on reverted calls")
        # v1.3.42 — Rocks typed key codecs
        for sym in ("rocks_key_account", "rocks_pack_u64", "rocks_key_block_height", "rocks_unpack_u64"):
            if f"def {sym}" not in native_py:
                errors.append(f"crypto/native.py must export {sym} (v1.3.42)")
        kc_py = (ROOT / "storage" / "keycodec.py").read_text(encoding="utf-8")
        if "rocks_key_account" not in kc_py or "native_keycodec_available" not in kc_py:
            errors.append("keycodec.py must prefer native rocks_* codecs")
        kc_rs = ROOT / "native" / "abs_native" / "src" / "rocks_keycodec.rs"
        if not kc_rs.is_file():
            errors.append("native rocks_keycodec.rs missing")
        # v1.3.43 — P2P rate-limit / strike table
        if "P2PRateLimitTable" not in native_py:
            errors.append("crypto/native.py must export P2PRateLimitTable (v1.3.43)")
        for sym in ("p2p_rate_limit_is_exempt", "p2p_rate_limit_tick", "p2p_strike_should_ban"):
            if f"def {sym}" not in native_py:
                errors.append(f"crypto/native.py must export {sym} (v1.3.43)")
        p2p_py = (ROOT / "network" / "p2p_node.py").read_text(encoding="utf-8")
        if "P2PRateLimitTable" not in p2p_py or "_rl_table" not in p2p_py:
            errors.append("p2p_node.py must wire native P2PRateLimitTable")
        rl_rs = ROOT / "native" / "abs_native" / "src" / "p2p_rate_limit.rs"
        if not rl_rs.is_file():
            errors.append("native p2p_rate_limit.rs missing")
        # v1.3.44 — EVM host-in-apply fee effects
        if "def blockchain_apply_host_effects" not in native_py:
            errors.append("crypto/native.py must export blockchain_apply_host_effects (v1.3.44)")
        bc_py = (ROOT / "core" / "blockchain.py").read_text(encoding="utf-8")
        state_svc_py = (ROOT / "core" / "components" / "state_service.py").read_text(
            encoding="utf-8"
        )
        if (
            ("blockchain_apply_host_effects" not in bc_py and "blockchain_apply_host_effects" not in state_svc_py)
            or (
                "_apply_evm_host_block_native" not in bc_py
                and "_apply_evm_host_block_native" not in state_svc_py
            )
        ):
            errors.append("blockchain.py must wire blockchain_apply_host_effects")
        if "blockchain_apply_host_effects" not in (
            ROOT / "native" / "abs_native" / "src" / "amount.rs"
        ).read_text(encoding="utf-8"):
            errors.append("amount.rs must define blockchain_apply_host_effects")
        # v1.3.45 — native apply writeback / receipt honesty
        if (
            "never wipe EVM code/storage" not in bc_py
            and "never wipe EVM code/storage" not in state_svc_py
        ):
            errors.append("blockchain writeback must preserve EVM code/storage (v1.3.45)")
        if "tx.status = 1" not in bc_py and "tx.status = 1" not in state_svc_py:
            errors.append("blockchain must set tx.status=1 on successful apply (v1.3.45)")
        if "0x0000000000000000000000000000000000000001" in (
            ROOT / "validators.manifest.example.json"
        ).read_text(encoding="utf-8"):
            errors.append("validators.manifest.example.json must not use 0x…0001 placeholders")
        # v1.3.46 — mixed simple+EVM native apply
        if "_apply_mixed_block_native" not in bc_py or "_block_transactions_are_mixed" not in bc_py:
            errors.append("blockchain.py must wire mixed simple+EVM native apply (v1.3.46)")
        if "expected_nonce" not in bc_py:
            errors.append("validate_transaction must accept expected_nonce for block assembly")
        # v1.3.47 — nested CALL effects planner
        if "def evm_plan_nested_call_effects" not in native_py:
            errors.append("crypto/native.py must export evm_plan_nested_call_effects (v1.3.47)")
        adapter_py = (ROOT / "execution" / "evm_adapter.py").read_text(encoding="utf-8")
        if "evm_plan_nested_call_effects" not in adapter_py:
            errors.append("evm_adapter must wire evm_plan_nested_call_effects")
        if "fn evm_plan_nested_call_effects" not in (
            ROOT / "native" / "abs_native" / "src" / "lib.rs"
        ).read_text(encoding="utf-8"):
            errors.append("lib.rs must define evm_plan_nested_call_effects")
        # v1.3.48 — nested CALL gas planner
        if "def evm_plan_nested_call_gas" not in native_py:
            errors.append("crypto/native.py must export evm_plan_nested_call_gas (v1.3.48)")
        interp_py = (ROOT / "evm_interpreter.py").read_text(encoding="utf-8")
        if "evm_plan_nested_call_gas" not in interp_py:
            errors.append("evm_interpreter must wire evm_plan_nested_call_gas")
        if "fn evm_plan_nested_call_gas" not in (
            ROOT / "native" / "abs_native" / "src" / "lib.rs"
        ).read_text(encoding="utf-8"):
            errors.append("lib.rs must define evm_plan_nested_call_gas")
        # v1.3.49 — nested CALL frame decode
        if "def evm_decode_nested_call_frame" not in native_py:
            errors.append("crypto/native.py must export evm_decode_nested_call_frame (v1.3.49)")
        bridge_py = (ROOT / "execution" / "evm_host_bridge.py").read_text(encoding="utf-8")
        if "evm_decode_nested_call_frame" not in bridge_py:
            errors.append("evm_host_bridge must wire evm_decode_nested_call_frame")
        if "fn evm_decode_nested_call_frame" not in (
            ROOT / "native" / "abs_native" / "src" / "lib.rs"
        ).read_text(encoding="utf-8"):
            errors.append("lib.rs must define evm_decode_nested_call_frame")
        # v1.3.50 — nested pure bytecode frame
        if "def evm_run_nested_pure_frame" not in native_py:
            errors.append("crypto/native.py must export evm_run_nested_pure_frame (v1.3.50)")
        if "def evm_bytecode_is_nested_pure_eligible" not in native_py:
            errors.append("crypto/native.py must export evm_bytecode_is_nested_pure_eligible")
        adapter_py = (ROOT / "execution" / "evm_adapter.py").read_text(encoding="utf-8")
        if "evm_run_nested_pure_frame" not in adapter_py:
            errors.append("evm_adapter must wire evm_run_nested_pure_frame")
        if "evm_run_nested_pure_frame" not in (
            ROOT / "native" / "abs_native" / "src" / "evm_pure_runner.rs"
        ).read_text(encoding="utf-8"):
            errors.append("evm_pure_runner.rs must define evm_run_nested_pure_frame")
        # v1.3.51 — P2P import off the event loop
        p2p_py = (ROOT / "network" / "p2p_node.py").read_text(encoding="utf-8")
        if "async def _import_block_async" not in p2p_py:
            errors.append("p2p_node must define _import_block_async (v1.3.51)")
        if "async def _reorg_and_import_async" not in p2p_py:
            errors.append("p2p_node must define _reorg_and_import_async (v1.3.51)")
        if "await self._import_block_async" not in p2p_py:
            errors.append("p2p_node hot paths must await _import_block_async")
        main_py = (ROOT / "main.py").read_text(encoding="utf-8")
        if "asyncio.to_thread(self.sync_engine.fast_sync)" not in main_py:
            errors.append("main.py follower genesis must offload fast_sync")
        # v1.3.52 — serial ChainApplyQueue
        if "class ChainApplyQueue" not in (
            ROOT / "core" / "chain_apply_queue.py"
        ).read_text(encoding="utf-8"):
            errors.append("core/chain_apply_queue.py must define ChainApplyQueue")
        if "ChainApplyQueue" not in main_py or "submit_forge_and_apply_async" not in main_py:
            errors.append("main.py mining must use ChainApplyQueue forge_and_apply")
        if "apply_queue" not in p2p_py:
            errors.append("p2p_node must wire apply_queue")
        # v1.3.53 — metrics + dedicated sync executor
        metrics_src = (ROOT / "observability" / "metrics.py").read_text(encoding="utf-8")
        for needle in (
            "abs_chain_apply_queue_depth",
            "abs_chain_apply_wait_seconds_total",
            "abs_chain_apply_reject_total",
            "abs_p2p_import_offload_total",
        ):
            if needle not in metrics_src:
                errors.append(f"metrics.py missing {needle} (v1.3.53)")
        if "ThreadPoolExecutor" not in main_py or "sync_executor" not in main_py:
            errors.append("main.py must create dedicated sync_executor")
        if "async def _sync_state_async" not in p2p_py:
            errors.append("p2p_node must define _sync_state_async")
        if "apply queue backpressure" not in main_py:
            errors.append("mining must fail-loud on apply queue backpressure")
        if "_apply_isolation_metrics" not in (
            ROOT / "api" / "http.py"
        ).read_text(encoding="utf-8"):
            errors.append("api/http.py must expose apply isolation metrics")
        # v1.3.54 — EVM/mempool load harness
        harness = ROOT / "scripts" / "evm_mempool_load_harness.py"
        if not harness.is_file():
            errors.append("scripts/evm_mempool_load_harness.py missing (v1.3.54)")
        else:
            htxt = harness.read_text(encoding="utf-8")
            if "ChainApplyQueue" not in htxt or "submit_forge_and_apply" not in htxt:
                errors.append("evm_mempool_load_harness must exercise ChainApplyQueue")
        # v1.3.55 — nested native bridge surface
        if "def evm_bytecode_is_nested_native_eligible" not in native_py:
            errors.append("crypto/native.py must export evm_bytecode_is_nested_native_eligible")
        if "allow_bridge=True" not in (
            ROOT / "execution" / "evm_adapter.py"
        ).read_text(encoding="utf-8"):
            errors.append("evm_adapter must call nested frame with allow_bridge=True")
        # v1.3.56 — nested host frame (CALL/CREATE/LOG via Rust + host_bridge)
        if "def evm_run_nested_host_frame" not in native_py:
            errors.append("crypto/native.py must export evm_run_nested_host_frame (v1.3.56)")
        adapter_now = (ROOT / "execution" / "evm_adapter.py").read_text(encoding="utf-8")
        if "evm_run_nested_host_frame" not in adapter_now:
            errors.append("evm_adapter must wire evm_run_nested_host_frame")
        if "native_nested_host" not in adapter_now:
            errors.append("evm_adapter must mark native_nested_host results")
        if "evm_run_nested_host_frame" not in (
            ROOT / "native" / "abs_native" / "src" / "evm_pure_runner.rs"
        ).read_text(encoding="utf-8"):
            errors.append("evm_pure_runner.rs must define evm_run_nested_host_frame")
        # v1.3.57 — host opcode bodies in Rust (LOG/CALL/CREATE via thin hooks)
        runner_rs = (
            ROOT / "native" / "abs_native" / "src" / "evm_pure_runner.rs"
        ).read_text(encoding="utf-8")
        for needle in (
            "fn execute_log_native",
            "fn execute_call_native",
            "fn execute_create_native",
        ):
            if needle not in runner_rs:
                errors.append(f"evm_pure_runner.rs missing {needle} (v1.3.57)")
        if 'hooks["contract_call"]' not in native_py:
            errors.append("evm_host_context_from_evm must wire contract_call hook (v1.3.57)")
        if 'hooks["contract_create"]' not in native_py:
            errors.append("evm_host_context_from_evm must wire contract_create hook (v1.3.57)")
        interp = (ROOT / "evm_interpreter.py").read_text(encoding="utf-8")
        if 'seg.get("logs")' not in interp:
            errors.append("evm_interpreter must merge native segment logs (v1.3.57)")
        # v1.3.58 — native account view decode for nested CALL preload
        if "def account_storage_map_from_raw" not in native_py:
            errors.append("crypto/native.py must export account_storage_map_from_raw (v1.3.58)")
        if "def account_view_from_blob" not in native_py:
            errors.append("crypto/native.py must export account_view_from_blob (v1.3.58)")
        if "def account_view_from_row" not in native_py:
            errors.append("crypto/native.py must export account_view_from_row (v1.3.58)")
        av_rs = ROOT / "native" / "abs_native" / "src" / "account_view.rs"
        if not av_rs.is_file():
            errors.append("account_view.rs missing (v1.3.58)")
        else:
            av_txt = av_rs.read_text(encoding="utf-8")
            for needle in (
                "account_storage_map_from_raw",
                "account_view_from_blob",
                "fn decode_account_view_bytes",
            ):
                if needle not in av_txt:
                    errors.append(f"account_view.rs missing {needle}")
        if "get_account_view" not in (
            ROOT / "native" / "abs_native" / "src" / "storage" / "mod.rs"
        ).read_text(encoding="utf-8"):
            errors.append("RocksEngine must expose get_account_view (v1.3.58)")
        adapter_av = (ROOT / "execution" / "evm_adapter.py").read_text(encoding="utf-8")
        if "def _account_view" not in adapter_av:
            errors.append("evm_adapter must define _account_view (v1.3.58)")
        if "account_storage_map_from_raw" not in adapter_av:
            errors.append("evm_adapter must use account_storage_map_from_raw")
        # v1.3.59 — nested CALL writeback ops
        if "def evm_plan_nested_call_writeback" not in native_py:
            errors.append("crypto/native.py must export evm_plan_nested_call_writeback (v1.3.59)")
        wb_rs = ROOT / "native" / "abs_native" / "src" / "evm_writeback.rs"
        if not wb_rs.is_file():
            errors.append("evm_writeback.rs missing (v1.3.59)")
        elif "evm_plan_nested_call_writeback" not in wb_rs.read_text(encoding="utf-8"):
            errors.append("evm_writeback.rs must define evm_plan_nested_call_writeback")
        adapter_wb = (ROOT / "execution" / "evm_adapter.py").read_text(encoding="utf-8")
        if "evm_plan_nested_call_writeback" not in adapter_wb:
            errors.append("evm_adapter must wire evm_plan_nested_call_writeback")
        if "def _apply_nested_writeback_ops" not in adapter_wb:
            errors.append("evm_adapter must define _apply_nested_writeback_ops")
        # v1.3.60 — CREATE writeback ops
        if "def evm_plan_create_writeback" not in native_py:
            errors.append("crypto/native.py must export evm_plan_create_writeback (v1.3.60)")
        wb_txt = (
            ROOT / "native" / "abs_native" / "src" / "evm_writeback.rs"
        ).read_text(encoding="utf-8")
        if "evm_plan_create_writeback" not in wb_txt:
            errors.append("evm_writeback.rs must define evm_plan_create_writeback")
        adapter_cr = (ROOT / "execution" / "evm_adapter.py").read_text(encoding="utf-8")
        if "evm_plan_create_writeback" not in adapter_cr:
            errors.append("evm_adapter must wire evm_plan_create_writeback")
        if "save_account" not in adapter_cr:
            errors.append("evm_adapter writeback must support save_account op")
        # v1.3.61 — native writeback apply
        if "def evm_apply_writeback_ops" not in native_py:
            errors.append("crypto/native.py must export evm_apply_writeback_ops (v1.3.61)")
        if "evm_apply_writeback_ops" not in (
            ROOT / "native" / "abs_native" / "src" / "evm_writeback.rs"
        ).read_text(encoding="utf-8"):
            errors.append("evm_writeback.rs must define evm_apply_writeback_ops")
        if "evm_apply_writeback_ops" not in (
            ROOT / "execution" / "evm_adapter.py"
        ).read_text(encoding="utf-8"):
            errors.append("evm_adapter must wire evm_apply_writeback_ops")
        # v1.3.62 — store-lock Rocks writeback commit
        storage_rs = (
            ROOT / "native" / "abs_native" / "src" / "storage" / "mod.rs"
        ).read_text(encoding="utf-8")
        if "fn commit_account_rows" not in storage_rs:
            errors.append("RocksEngine must expose commit_account_rows (v1.3.62)")
        rocks_py = (ROOT / "storage" / "rocks_store.py").read_text(encoding="utf-8")
        if "def commit_writeback_accounts" not in rocks_py:
            errors.append("rocks_store must define commit_writeback_accounts (v1.3.62)")
        if "commit_writeback_accounts" not in (
            ROOT / "execution" / "evm_adapter.py"
        ).read_text(encoding="utf-8"):
            errors.append("evm_adapter must wire commit_writeback_accounts")
        if "def commit_writeback_accounts" not in (
            ROOT / "storage" / "hybrid_database.py"
        ).read_text(encoding="utf-8"):
            errors.append("hybrid_database must delegate commit_writeback_accounts")
        # v1.3.63 — unified writeback bundle
        if "fn commit_writeback_bundle" not in storage_rs:
            errors.append("RocksEngine must expose commit_writeback_bundle (v1.3.63)")
        if "def commit_writeback_bundle" not in rocks_py:
            errors.append("rocks_store must define commit_writeback_bundle (v1.3.63)")
        if "writeback_balance_abs" not in rocks_py:
            errors.append("rocks_store commit_writeback must use writeback_balance_abs")
        if 'row["balance"] = float(' in rocks_py:
            errors.append("rocks_store must not rehydrate ABS via float(balance) when satoshi exists")
        if "commit_writeback_bundle" not in (
            ROOT / "execution" / "evm_adapter.py"
        ).read_text(encoding="utf-8"):
            errors.append("evm_adapter must wire commit_writeback_bundle")
        if "def commit_writeback_bundle" not in (
            ROOT / "storage" / "hybrid_database.py"
        ).read_text(encoding="utf-8"):
            errors.append("hybrid_database must delegate commit_writeback_bundle")
        # v1.3.64 — Rocks batch writeback preload
        if "fn get_account_rows" not in storage_rs:
            errors.append("RocksEngine must expose get_account_rows (v1.3.64)")
        if "def load_writeback_accounts" not in rocks_py:
            errors.append("rocks_store must define load_writeback_accounts (v1.3.64)")
        if "load_writeback_accounts" not in (
            ROOT / "execution" / "evm_adapter.py"
        ).read_text(encoding="utf-8"):
            errors.append("evm_adapter must wire load_writeback_accounts")
        if "def load_writeback_accounts" not in (
            ROOT / "storage" / "hybrid_database.py"
        ).read_text(encoding="utf-8"):
            errors.append("hybrid_database must delegate load_writeback_accounts")
        if "def get_rocks_runtime_stats" not in (
            ROOT / "storage" / "hybrid_database.py"
        ).read_text(encoding="utf-8"):
            errors.append("hybrid_database must delegate get_rocks_runtime_stats")
        if "def count_address_transactions" not in (
            ROOT / "storage" / "hybrid_database.py"
        ).read_text(encoding="utf-8"):
            errors.append("HybridDatabase must forward count_address_transactions")
        if "def count_proposer_audit" not in (
            ROOT / "storage" / "hybrid_database.py"
        ).read_text(encoding="utf-8"):
            errors.append("HybridDatabase must forward count_proposer_audit")
        # Rocks O(1) honesty cluster — live RPC/metrics must not prefix-scan growing CFs.
        latest_fn = rocks_py.split("def get_latest_blocks", 1)[-1].split("def ", 1)[0]
        if "_scan_prefix" in latest_fn:
            errors.append("Rocks get_latest_blocks must not prefix-scan all heights")
        if "key_block_height" not in latest_fn:
            errors.append("Rocks get_latest_blocks must point-read key_block_height from tip")
        burn_fn = rocks_py.split("def get_total_burned", 1)[-1].split("def ", 1)[0]
        if "prefix_last" not in burn_fn:
            errors.append("get_total_burned must use Rocks prefix_last (not full P_BURN scan)")
        act_fn = rocks_py.split("def get_address_activity", 1)[-1].split(
            "def get_proposer_audit_log", 1
        )[0]
        if "_scan_prefix(kc.P_PROPOSER_AUDIT)" in act_fn:
            errors.append("Rocks get_address_activity must not prefix-scan proposer_audit")
        if "_max_indexed_tx_height" not in act_fn:
            errors.append("Rocks get_address_activity must use indexed last_tx_height")
        plog_fn = rocks_py.split("def get_proposer_audit_log", 1)[-1].split(
            "def count_proposer_audit", 1
        )[0]
        if "_scan_prefix(kc.P_PROPOSER_AUDIT)" in plog_fn:
            errors.append("Rocks get_proposer_audit_log must not prefix-scan proposer_audit")
        if "key_proposer_audit" not in plog_fn:
            errors.append("Rocks get_proposer_audit_log must seek by height key")
        if "def count_proposer_audit" not in rocks_py:
            errors.append("RocksChainStore must implement count_proposer_audit")
        if "def count_address_transactions" not in rocks_py:
            errors.append("RocksChainStore must implement count_address_transactions")
        if 'len(self._scan_prefix(kc.prefix_tx_from' in rocks_py:
            errors.append("Rocks address tx count must not prefix-scan the from-index")
        metrics_fn = rocks_py.split("def get_chain_metrics", 1)[-1].split("def ", 1)[0]
        if "_iter_transaction_rows()" in metrics_fn:
            errors.append("Rocks get_chain_metrics must not iterate every tx row")
        if "_scan_prefix(kc.P_TX_RECEIPT)" in metrics_fn:
            errors.append("Rocks get_chain_metrics must not scan every receipt")
        if '_cached_prefix_len("stats_tx_count"' not in metrics_fn:
            errors.append("Rocks get_chain_metrics must use cached prefix lengths")
        tx_addr_fn = rocks_py.split("def get_transactions_by_address", 1)[-1].split(
            "def ", 1
        )[0]
        if "_rows_from_address_index" in tx_addr_fn:
            errors.append(
                "Rocks get_transactions_by_address must not load the full address index"
            )
        if "_scan_prefix" in tx_addr_fn:
            errors.append(
                "Rocks get_transactions_by_address must paginate via prefix_prev, not prefix_scan"
            )
        if "_address_index_page_hashes" not in tx_addr_fn:
            errors.append("Rocks get_transactions_by_address must page index hashes newest-first")
        page_fn = rocks_py.split("def _address_index_page_hashes", 1)[-1].split(
            "def ", 1
        )[0]
        if "_prefix_prev_kv" not in page_fn or "_scan_prefix" in page_fn:
            errors.append("_address_index_page_hashes must walk via _prefix_prev_kv only")
        keycodec_py = (ROOT / "storage" / "keycodec.py").read_text(encoding="utf-8")
        if "def prefix_family_end" not in keycodec_py:
            errors.append("keycodec must expose prefix_family_end for exclusive family scans")
        recent_fn = rocks_py.split("def get_recent_transactions", 1)[-1].split(
            "def ", 1
        )[0]
        if "_scan_prefix" in recent_fn:
            errors.append(
                "Rocks get_recent_transactions must scan_range the inverted recent index"
            )
        if "_scan_range" not in recent_fn:
            errors.append("Rocks get_recent_transactions must use _scan_range")
        lock_fn = rocks_py.split("def get_bridge_locks", 1)[-1].split("def ", 1)[0]
        if "_scan_prefix(kc.prefix_bridge_locks())" in lock_fn:
            errors.append("Rocks get_bridge_locks must not unbounded prefix-scan locks")
        if "_scan_range" not in lock_fn:
            errors.append("Rocks get_bridge_locks must bound the lock walk via _scan_range")
        if "_bump_addr_tx_count" not in rocks_py or "_bump_proposer_count" not in rocks_py:
            errors.append("Rocks must maintain addr_tx / proposer meta counters")
        ready_fn = http_py.split('if path == "/health/ready"', 1)[-1].split(
            "checks = {", 1
        )[0]
        if "db.get_stats()" in ready_fn:
            errors.append("/health/ready must not call db.get_stats()")
        if "no cheap db probe" not in ready_fn:
            errors.append("/health/ready must fail-closed without cheap tip/height probe")
        if '"topology_deferred": True' not in http_py:
            errors.append("/status p2p_summary must defer get_topology (topology_deferred)")
        # v1.3.65 — L1 fail-closed hardening
        vk_py = (ROOT / "crypto" / "validator_keys.py").read_text(encoding="utf-8")
        if "derive_address" not in vk_py:
            errors.append("validator_keys.verify_attestation must bind pubkey→validator (v1.3.65)")
        p2p_py = (ROOT / "network" / "p2p_node.py").read_text(encoding="utf-8")
        if "validator_register_disabled" not in p2p_py:
            errors.append("p2p must disable unauthenticated validator_register in prod (v1.3.65)")
        if "attestation_verifier_unavailable" not in p2p_py:
            errors.append("p2p must fail-closed when attestation verifier missing (v1.3.65)")
        bc_py = (ROOT / "core" / "blockchain.py").read_text(encoding="utf-8")
        if "_native_apply_fail_closed" not in bc_py:
            errors.append("blockchain must fail-closed native apply in prod (v1.3.65)")
        amount_py = (ROOT / "runtime" / "amount.py").read_text(encoding="utf-8")
        if "ABS_REQUIRE_NATIVE_CRYPTO" not in amount_py:
            errors.append("amount._native_required must honor ABS_REQUIRE_NATIVE_CRYPTO (v1.3.65)")
        rocks_py2 = (ROOT / "storage" / "rocks_store.py").read_text(encoding="utf-8")
        if "AccountCorruptError" not in rocks_py2:
            errors.append("rocks_store must raise AccountCorruptError on corrupt account (v1.3.65)")
        http_py = (ROOT / "api" / "http.py").read_text(encoding="utf-8")
        if "_read_limited_body" not in http_py or "batch too large" not in http_py:
            errors.append("http must cap body size and JSON-RPC batch (v1.3.65)")
        # v1.3.66 — load / backpressure
        apply_q = (ROOT / "core" / "chain_apply_queue.py").read_text(encoding="utf-8")
        if "expired_total" not in apply_q or "deadline_monotonic" not in apply_q:
            errors.append("chain_apply_queue must expire stale jobs (v1.3.66)")
        if "asyncio.wrap_future" not in apply_q:
            errors.append("async apply submit must wrap_future (not to_thread wait)")
        if "asyncio.to_thread(self.submit_import" in apply_q:
            errors.append("submit_import_async must not block a thread-pool worker")
        if "drop mempool txs only after successful import" not in p2p_py:
            errors.append("p2p must remove mempool only after successful import (v1.3.66)")
        if "_schedule_sync" not in p2p_py or "_schedule_connect" not in p2p_py:
            errors.append("p2p must coalesce sync/connect tasks (v1.3.66)")
        if "fn prefix_last" not in storage_rs:
            errors.append("RocksEngine must expose prefix_last (v1.3.66)")
        if "fn prefix_prev" not in storage_rs:
            errors.append("RocksEngine must expose prefix_prev (address index pagination)")
        if "fn scan_range" not in storage_rs:
            errors.append("RocksEngine must expose scan_range (bounded recent-tx / bridge walks)")
        if "lexicographically last key across" not in storage_rs:
            errors.append(
                "prefix_last must merge target CF + legacy default (not primary-first)"
            )
        if 'key_meta("chain_tip")' not in rocks_py2:
            errors.append("rocks_store must persist chain_tip meta (v1.3.66)")
        metrics_py2 = (ROOT / "observability" / "metrics.py").read_text(encoding="utf-8")
        if "abs_chain_apply_expired_total" not in metrics_py2:
            errors.append("metrics must emit apply expired counter (v1.3.66)")
        # v1.3.67 — EVM journal + arena
        adapter_py = (ROOT / "execution" / "evm_adapter.py").read_text(encoding="utf-8")
        if "begin_writeback_journal" not in adapter_py or "commit_writeback_journal" not in adapter_py:
            errors.append("evm_adapter must expose writeback journal (v1.3.67)")
        pure_rs = (
            ROOT / "native" / "abs_native" / "src" / "evm_pure_runner.rs"
        ).read_text(encoding="utf-8")
        if "Rust-owned storage arena" not in pure_rs:
            errors.append("evm_pure_runner must use Rust storage arena (v1.3.67)")
        # v1.3.68 — bridge debit + semantic event
        if "def try_debit_satoshi" not in amount_py:
            errors.append("amount.py must define try_debit_satoshi (v1.3.68)")
        if "try_debit_satoshi" not in rocks_py2:
            errors.append("rocks_store debit must use try_debit_satoshi (v1.3.68)")
        bridge_rs = (ROOT / "bridge" / "rust_bridge" / "src" / "main.rs").read_text(
            encoding="utf-8"
        )
        if "receipt_has_semantic_lock_log" not in bridge_rs:
            errors.append("rust_bridge must support semantic lock-log bind (v1.3.68)")
        cfg_py = (ROOT / "runtime" / "config.py").read_text(encoding="utf-8")
        if "bridge_require_l1_event=true" not in cfg_py and "BRIDGE_REQUIRE_L1_EVENT=true" not in cfg_py:
            errors.append("prod config must require bridge_require_l1_event (v1.3.68)")
        # v1.3.69 — block-scoped sat session
        if (
            "block-scoped sat session" not in bc_py
            and "block-scoped sat session" not in state_svc_py
        ):
            errors.append("blockchain mixed apply must use block-scoped sat session (v1.3.69)")
        if not (ROOT / "scripts" / "verify_industrial_waves.py").is_file():
            errors.append("scripts/verify_industrial_waves.py missing (v1.3.69)")
        # v1.3.70 — recursive frame arena sync
        rust_runner = (ROOT / "native" / "abs_native" / "src" / "evm_pure_runner.rs").read_text(
            encoding="utf-8", errors="replace"
        )
        if "v1.3.70" not in rust_runner or "re-sync arena after DELEGATECALL" not in rust_runner:
            errors.append("evm_pure_runner must flush/resync arena around nested CALL (v1.3.70)")
        adapter_py = (ROOT / "execution" / "evm_adapter.py").read_text(
            encoding="utf-8", errors="replace"
        )
        if "_abs_live_storage" not in adapter_py:
            errors.append("evm_adapter must expose _abs_live_storage for DELEGATECALL (v1.3.70)")
        # v1.3.71 — inline leaf frame
        if "try_inline_leaf_delegate_call" not in rust_runner or "v1.3.71" not in rust_runner:
            errors.append("evm_pure_runner must inline eligible DELEGATECALL leaf (v1.3.71)")
        # v1.3.72 — P2P sync admission
        p2p_py = (ROOT / "network" / "p2p_node.py").read_text(
            encoding="utf-8", errors="replace"
        )
        if "sync admission reject" not in p2p_py or "_bump_outbound_drop" not in p2p_py:
            errors.append("p2p_node must enforce sync admission + outbound drop metrics (v1.3.72)")
        if "p2p_max_sync_inflight" not in cfg_py:
            errors.append("config must define p2p_max_sync_inflight (v1.3.72)")
        # v1.3.73 — apply priority lanes
        if "PriorityQueue" not in apply_q or "_APPLY_PRIORITY" not in apply_q:
            errors.append("chain_apply_queue must use PriorityQueue lanes (v1.3.73)")
        # v1.3.74 — value=0 CALL inline
        if "try_inline_leaf_value0_call" not in rust_runner or "v1.3.74" not in rust_runner:
            errors.append("evm_pure_runner must inline value=0 CALL leaf (v1.3.74)")
        # v1.3.75 — multi-depth call frames
        if "bytecode_is_inline_call_frame_eligible" not in rust_runner:
            errors.append("evm_pure_runner must allow multi-depth call-frames (v1.3.75)")
        if "MAX_INLINE_CALL_DEPTH" not in rust_runner or "_abs_inline_depth" not in rust_runner:
            errors.append("evm_pure_runner must track inline CALL depth (v1.3.75)")
        # v1.3.76 — value CALL fail-closed
        if "try_inline_value_transfer" not in rust_runner or "v1.3.76" not in rust_runner:
            errors.append("evm_pure_runner must fail-closed value CALL transfer (v1.3.76)")
        # v1.3.77 — Rust P2P ingress pipeline
        ingress_rs = (
            ROOT / "native" / "abs_native" / "src" / "p2p_ingress.rs"
        ).read_text(encoding="utf-8")
        if "p2p_ingress_admit" not in ingress_rs or "P2PConnectionGovernor" not in ingress_rs:
            errors.append("p2p_ingress must expose admit + connection governor (v1.3.77)")
        if "p2p_ingress_admit" not in p2p_py or "_use_native_ingress" not in p2p_py:
            errors.append("p2p_node must wire native ingress admit (v1.3.77)")
        if "p2p_max_inbound_per_ip" not in cfg_py:
            errors.append("config must define p2p_max_inbound_per_ip (v1.3.77)")
        if "mod p2p_ingress" not in (
            ROOT / "native" / "abs_native" / "src" / "lib.rs"
        ).read_text(encoding="utf-8"):
            errors.append("abs_native lib.rs must register p2p_ingress (v1.3.77)")
        # v1.3.78 — bandwidth / cost accounting
        rl_rs = (ROOT / "native" / "abs_native" / "src" / "p2p_rate_limit.rs").read_text(
            encoding="utf-8"
        )
        if "bandwidth_exceeded" not in rl_rs or "ingress_cost_units" not in rl_rs:
            errors.append("p2p_rate_limit must enforce bandwidth budget (v1.3.78)")
        if "p2p_max_bytes_per_sec" not in cfg_py:
            errors.append("config must define p2p_max_bytes_per_sec (v1.3.78)")
        metrics_bw = (ROOT / "observability" / "metrics.py").read_text(encoding="utf-8")
        if "abs_p2p_bandwidth_rejects_total" not in metrics_bw:
            errors.append("metrics must export abs_p2p_bandwidth_rejects_total (v1.3.78)")
        # v1.3.79 — CALLCODE value
        if "native_inline_callcode_value" not in rust_runner or "v1.3.79" not in rust_runner:
            errors.append("evm_pure_runner must inline CALLCODE value (v1.3.79)")
        # v1.3.80 — simple CREATE
        if "try_inline_simple_create" not in rust_runner or "v1.3.80" not in rust_runner:
            errors.append("evm_pure_runner must inline simple CREATE (v1.3.80)")
        # v1.3.81 — CREATE2
        if "native_inline_create2" not in rust_runner or "v1.3.81" not in rust_runner:
            errors.append("evm_pure_runner must inline CREATE2 (v1.3.81)")
        if "create2_eip1014_enabled" not in rust_runner:
            errors.append("evm_pure_runner must gate CREATE2 EIP-1014 (v1.3.81)")
        # v1.3.82 — CREATE RETURN runtime
        if "run_inline_create_init" not in rust_runner or "v1.3.82" not in rust_runner:
            errors.append("evm_pure_runner must run eligible CREATE init (v1.3.82)")
        if "native_inline_create_runtime" not in rust_runner:
            errors.append("evm_pure_runner must mark CREATE runtime (v1.3.82)")
        # v1.3.83 — inline value → writeback journal
        if "push_pending_writeback_transfer" not in rust_runner or "v1.3.83" not in rust_runner:
            errors.append("evm_pure_runner must plan inline writeback transfers (v1.3.83)")
        if "pending_writeback_ops" not in rust_runner:
            errors.append("evm_pure_runner must emit pending_writeback_ops (v1.3.83)")
        adapter_py = (ROOT / "execution" / "evm_adapter.py").read_text(encoding="utf-8")
        if "_take_bridge_pending_writeback" not in adapter_py:
            errors.append("evm_adapter must flush bridge pending_writeback_ops (v1.3.83)")
        # v1.3.84 — inline CREATE save_account journal
        if "push_pending_writeback_save_account" not in rust_runner or "v1.3.84" not in rust_runner:
            errors.append("evm_pure_runner must plan inline CREATE save_account (v1.3.84)")
        if "native_inline_writeback_create" not in rust_runner:
            errors.append("evm_pure_runner must mark CREATE writeback (v1.3.84)")
        # v1.3.85 — outbound egress bandwidth
        rl_rs = (ROOT / "native" / "abs_native" / "src" / "p2p_rate_limit.rs").read_text(
            encoding="utf-8"
        )
        if "admit_egress" not in rl_rs or "v1.3.85" not in rl_rs:
            errors.append("p2p_rate_limit must enforce egress bandwidth (v1.3.85)")
        if "egress_bandwidth_exceeded" not in rl_rs:
            errors.append("p2p_rate_limit must reject egress_bandwidth_exceeded (v1.3.85)")
        if "p2p_max_outbound_bytes_per_sec" not in cfg_py:
            errors.append("config must define p2p_max_outbound_bytes_per_sec (v1.3.85)")
        metrics_eg = (ROOT / "observability" / "metrics.py").read_text(encoding="utf-8")
        if "abs_p2p_egress_rejects_total" not in metrics_eg:
            errors.append("metrics must export abs_p2p_egress_rejects_total (v1.3.85)")
        p2p_py = (ROOT / "network" / "p2p_node.py").read_text(encoding="utf-8")
        if "_egress_ok" not in p2p_py or "admit_egress" not in p2p_py:
            errors.append("p2p_node must gate send via egress admit (v1.3.85)")
        # v1.3.86 — NDJSON line framer
        frame_rs = (ROOT / "native" / "abs_native" / "src" / "p2p_frame.rs").read_text(
            encoding="utf-8"
        )
        if "P2PLineFramer" not in frame_rs or "v1.3.86" not in frame_rs:
            errors.append("p2p_frame must expose P2PLineFramer (v1.3.86)")
        if "mod p2p_frame" not in (
            ROOT / "native" / "abs_native" / "src" / "lib.rs"
        ).read_text(encoding="utf-8"):
            errors.append("abs_native lib.rs must register p2p_frame (v1.3.86)")
        if "_read_wire_line" not in p2p_py or "P2PLineFramer" not in p2p_py:
            errors.append("p2p_node must wire native line framer (v1.3.86)")
        # v1.3.87 — unified egress prepare
        ingress_rs87 = (
            ROOT / "native" / "abs_native" / "src" / "p2p_ingress.rs"
        ).read_text(encoding="utf-8")
        if "p2p_egress_prepare" not in ingress_rs87 or "v1.3.87" not in ingress_rs87:
            errors.append("p2p_ingress must expose p2p_egress_prepare (v1.3.87)")
        if "_prepare_outbound" not in p2p_py or "p2p_egress_prepare" not in p2p_py:
            errors.append("p2p_node must wire egress prepare (v1.3.87)")
        # v1.3.89 — Sybil / Eclipse governor
        if "p2p_subnet_key" not in ingress_rs87 or "reserved_outbound_slots" not in ingress_rs87:
            errors.append("p2p_ingress must expose subnet/reserved Sybil defenses (v1.3.89)")
        if "p2p_max_peers_per_subnet" not in cfg_py or "p2p_eclipse_warn_ratio" not in cfg_py:
            errors.append("config must define Sybil/Eclipse knobs (v1.3.89)")
        if "_maybe_eclipse_prune" not in p2p_py:
            errors.append("p2p_node must wire eclipse prune + diversity (v1.3.89)")
        peer_mgr_py = (ROOT / "network" / "peer_manager.py").read_text(
            encoding="utf-8", errors="replace"
        )
        if (
            "diversity_snapshot" not in p2p_py
            and "diversity_snapshot" not in peer_mgr_py
        ):
            errors.append("p2p_node must wire eclipse prune + diversity (v1.3.89)")
        metrics_sybil = (ROOT / "observability" / "metrics.py").read_text(encoding="utf-8")
        if "abs_p2p_subnet_rejects_total" not in metrics_sybil:
            errors.append("metrics must export abs_p2p_subnet_rejects_total (v1.3.89)")
        if "abs_p2p_eclipse_at_risk" not in metrics_sybil:
            errors.append("metrics must export abs_p2p_eclipse_at_risk (v1.3.89)")
        # v1.3.90 — native plain-TCP transport slice
        transport_rs = (
            ROOT / "native" / "abs_native" / "src" / "p2p_transport.rs"
        ).read_text(encoding="utf-8")
        if "P2PNativeListener" not in transport_rs or "P2PNativeConn" not in transport_rs:
            errors.append("p2p_transport must expose listener + conn (v1.3.90)")
        if "p2p_native_transport" not in cfg_py:
            errors.append("config must define p2p_native_transport (v1.3.90)")
        if "_native_accept_loop" not in p2p_py:
            errors.append("p2p_node must wire native accept loop (v1.3.90)")
        if "mod p2p_transport" not in (
            ROOT / "native" / "abs_native" / "src" / "lib.rs"
        ).read_text(encoding="utf-8"):
            errors.append("abs_native lib.rs must register p2p_transport (v1.3.90)")
        # v1.3.91 — native rustls TLS
        if "rustls" not in transport_rs or "WebPkiClientVerifier" not in transport_rs:
            errors.append("p2p_transport must include rustls mTLS (v1.3.91)")
        if "_native_tls" not in p2p_py:
            errors.append("p2p_node must wire native TLS flag (v1.3.91)")
        if "abs_p2p_native_tls" not in (
            ROOT / "observability" / "metrics.py"
        ).read_text(encoding="utf-8"):
            errors.append("metrics must export abs_p2p_native_tls (v1.3.91)")
        # v1.3.92 — native read_message pump
        if "read_message" not in transport_rs or "v1.3.92" not in transport_rs:
            errors.append("p2p_transport must expose read_message (v1.3.92)")
        if "_native_read_message" not in p2p_py or "read_message" not in p2p_py:
            errors.append("p2p_node must wire native read_message (v1.3.92)")
        if "abs_p2p_native_read_message" not in (
            ROOT / "observability" / "metrics.py"
        ).read_text(encoding="utf-8"):
            errors.append("metrics must export abs_p2p_native_read_message (v1.3.92)")
        # v1.3.93 — native write_message pump
        if "write_message" not in transport_rs or "v1.3.93" not in transport_rs:
            errors.append("p2p_transport must expose write_message (v1.3.93)")
        if "_native_write_message" not in p2p_py or "_write_message" not in p2p_py:
            errors.append("p2p_node must wire native write_message (v1.3.93)")
        if "abs_p2p_native_write_message" not in (
            ROOT / "observability" / "metrics.py"
        ).read_text(encoding="utf-8"):
            errors.append("metrics must export abs_p2p_native_write_message (v1.3.93)")
        # v1.3.94 — native read_messages batch
        if "read_messages" not in transport_rs or "v1.3.94" not in transport_rs:
            errors.append("p2p_transport must expose read_messages (v1.3.94)")
        if "_native_read_messages" not in p2p_py or "_pending_msgs" not in p2p_py:
            errors.append("p2p_node must wire native read_messages (v1.3.94)")
        if "abs_p2p_native_read_messages" not in (
            ROOT / "observability" / "metrics.py"
        ).read_text(encoding="utf-8"):
            errors.append("metrics must export abs_p2p_native_read_messages (v1.3.94)")
        # v1.3.95 — native write_messages batch
        if "write_messages" not in transport_rs or "write_payloads" not in transport_rs:
            errors.append("p2p_transport must expose write_messages/payloads (v1.3.95)")
        if "_native_write_messages" not in p2p_py or "_write_messages_batch" not in p2p_py:
            errors.append("p2p_node must wire native write_messages batch (v1.3.95)")
        if "abs_p2p_native_write_messages" not in (
            ROOT / "observability" / "metrics.py"
        ).read_text(encoding="utf-8"):
            errors.append("metrics must export abs_p2p_native_write_messages (v1.3.95)")
        # v1.3.96 — native handshake I/O fuse
        if "handshake_roundtrip" not in transport_rs or "v1.3.96" not in transport_rs:
            errors.append("p2p_transport must expose handshake_roundtrip (v1.3.96)")
        if "_native_handshake" not in p2p_py or "handshake_roundtrip" not in p2p_py:
            errors.append("p2p_node must wire native handshake (v1.3.96)")
        if "abs_p2p_native_handshake" not in (
            ROOT / "observability" / "metrics.py"
        ).read_text(encoding="utf-8"):
            errors.append("metrics must export abs_p2p_native_handshake (v1.3.96)")
        # v1.3.97 — native peer cert identities
        if "peer_cert_identities" not in transport_rs or "extract_cert_identities" not in transport_rs:
            errors.append("p2p_transport must extract peer cert identities (v1.3.97)")
        if "_native_peer_identities" not in p2p_py or "peer_cert_identities" not in p2p_py:
            errors.append("p2p_node must wire native peer identities (v1.3.97)")
        if "abs_p2p_native_peer_identities" not in (
            ROOT / "observability" / "metrics.py"
        ).read_text(encoding="utf-8"):
            errors.append("metrics must export abs_p2p_native_peer_identities (v1.3.97)")
        # v1.3.98 — native auto-pong
        if "maybe_auto_pong" not in transport_rs or "v1.3.98" not in transport_rs:
            errors.append("p2p_transport must expose auto_pong (v1.3.98)")
        if "_native_auto_pong" not in p2p_py:
            errors.append("p2p_node must wire native auto_pong (v1.3.98)")
        if "p2p_native_auto_pong" not in cfg_py:
            errors.append("config must define p2p_native_auto_pong (v1.3.98)")
        if "abs_p2p_native_auto_pong" not in (
            ROOT / "observability" / "metrics.py"
        ).read_text(encoding="utf-8"):
            errors.append("metrics must export abs_p2p_native_auto_pong (v1.3.98)")
        # v1.3.99 — keepalive consume + touch
        if "keepalive_touches" not in transport_rs or "v1.3.99" not in transport_rs:
            errors.append("p2p_transport must expose keepalive_touches (v1.3.99)")
        if "keepalive_touches" not in p2p_py or "native_keepalive" not in p2p_py:
            errors.append("p2p_node must wire keepalive touch (v1.3.99)")
        if "abs_p2p_native_keepalive" not in (
            ROOT / "observability" / "metrics.py"
        ).read_text(encoding="utf-8"):
            errors.append("metrics must export abs_p2p_native_keepalive (v1.3.99)")
        # v1.3.100 — housekeeping payload gate
        if "housekeeping_payload_ok" not in transport_rs or "v1.3.100" not in transport_rs:
            errors.append("p2p_transport must expose housekeeping gate (v1.3.100)")
        if "native_housekeeping_gate" not in p2p_py:
            errors.append("p2p_node must expose native_housekeeping_gate (v1.3.100)")
        if "abs_p2p_native_housekeeping_gate" not in (
            ROOT / "observability" / "metrics.py"
        ).read_text(encoding="utf-8"):
            errors.append("metrics must export abs_p2p_native_housekeeping_gate (v1.3.100)")
        # v1.3.101 — batch/chunk config
        if "p2p_native_clamp_batch" not in transport_rs or "v1.3.101" not in transport_rs:
            errors.append("p2p_transport must expose clamp_batch (v1.3.101)")
        if "p2p_native_read_batch" not in cfg_py or "_clamp_native_batch" not in p2p_py:
            errors.append("config/p2p_node must wire native batch knobs (v1.3.101)")
        if "abs_p2p_native_read_batch" not in (
            ROOT / "observability" / "metrics.py"
        ).read_text(encoding="utf-8"):
            errors.append("metrics must export abs_p2p_native_read_batch (v1.3.101)")
        # v1.3.102 — I/O timeout
        if "p2p_native_clamp_timeout_ms" not in transport_rs or "v1.3.102" not in transport_rs:
            errors.append("p2p_transport must expose clamp_timeout_ms (v1.3.102)")
        if "p2p_native_io_timeout_ms" not in cfg_py or "_apply_native_io_timeout" not in p2p_py:
            errors.append("config/p2p_node must wire native I/O timeout (v1.3.102)")
        if "abs_p2p_native_io_timeout_ms" not in (
            ROOT / "observability" / "metrics.py"
        ).read_text(encoding="utf-8"):
            errors.append("metrics must export abs_p2p_native_io_timeout_ms (v1.3.102)")
        # v1.3.103 — mid-session handshake gate
        if "check_mid_session_handshake" not in transport_rs or "v1.3.103" not in transport_rs:
            errors.append("p2p_transport must expose mid-session gate (v1.3.103)")
        if "set_session_established" not in p2p_py or "native_mid_session_gate" not in p2p_py:
            errors.append("p2p_node must wire mid-session gate (v1.3.103)")
        if "abs_p2p_native_mid_session_gate" not in (
            ROOT / "observability" / "metrics.py"
        ).read_text(encoding="utf-8"):
            errors.append("metrics must export abs_p2p_native_mid_session_gate (v1.3.103)")
        # v1.3.104 — status payload gate
        if "check_status_payload" not in transport_rs or "v1.3.104" not in transport_rs:
            errors.append("p2p_transport must expose status gate (v1.3.104)")
        if "native_status_gate" not in p2p_py:
            errors.append("p2p_node must expose native_status_gate (v1.3.104)")
        if "abs_p2p_native_status_gate" not in (
            ROOT / "observability" / "metrics.py"
        ).read_text(encoding="utf-8"):
            errors.append("metrics must export abs_p2p_native_status_gate (v1.3.104)")
        # v1.3.105 — attestation shape gate
        if "check_attestation_payload" not in transport_rs or "v1.3.105" not in transport_rs:
            errors.append("p2p_transport must expose attestation gate (v1.3.105)")
        if "native_attestation_gate" not in p2p_py:
            errors.append("p2p_node must expose native_attestation_gate (v1.3.105)")
        if "abs_p2p_native_attestation_gate" not in (
            ROOT / "observability" / "metrics.py"
        ).read_text(encoding="utf-8"):
            errors.append("metrics must export abs_p2p_native_attestation_gate (v1.3.105)")
        # v1.3.106 — block sync shape gates
        if "check_block_announce_payload" not in transport_rs or "v1.3.106" not in transport_rs:
            errors.append("p2p_transport must expose block announce gate (v1.3.106)")
        if "check_get_block_payload" not in transport_rs:
            errors.append("p2p_transport must expose get_block gate (v1.3.106)")
        if "native_block_sync_gate" not in p2p_py:
            errors.append("p2p_node must expose native_block_sync_gate (v1.3.106)")
        if "abs_p2p_native_block_sync_gate" not in (
            ROOT / "observability" / "metrics.py"
        ).read_text(encoding="utf-8"):
            errors.append("metrics must export abs_p2p_native_block_sync_gate (v1.3.106)")
        # v1.3.107 — block fetch shape gates
        if "check_get_blocks_payload" not in transport_rs or "v1.3.107" not in transport_rs:
            errors.append("p2p_transport must expose get_blocks gate (v1.3.107)")
        if "check_get_block_by_hash_payload" not in transport_rs:
            errors.append("p2p_transport must expose get_block_by_hash gate (v1.3.107)")
        if "check_blocks_batch_payload" not in transport_rs:
            errors.append("p2p_transport must expose blocks batch gate (v1.3.107)")
        if "native_block_fetch_gate" not in p2p_py:
            errors.append("p2p_node must expose native_block_fetch_gate (v1.3.107)")
        if "abs_p2p_native_block_fetch_gate" not in (
            ROOT / "observability" / "metrics.py"
        ).read_text(encoding="utf-8"):
            errors.append("metrics must export abs_p2p_native_block_fetch_gate (v1.3.107)")
        # v1.3.108 — tx gossip shape gates
        if "check_wire_tx_payload" not in transport_rs or "v1.3.108" not in transport_rs:
            errors.append("p2p_transport must expose wire_tx gate (v1.3.108)")
        if "check_mempool_batch_payload" not in transport_rs:
            errors.append("p2p_transport must expose mempool batch gate (v1.3.108)")
        if "check_ingress_shape_gates" not in transport_rs:
            errors.append("p2p_transport must expose check_ingress_shape_gates (v1.3.108)")
        if "native_tx_gossip_gate" not in p2p_py:
            errors.append("p2p_node must expose native_tx_gossip_gate (v1.3.108)")
        if "abs_p2p_native_tx_gossip_gate" not in (
            ROOT / "observability" / "metrics.py"
        ).read_text(encoding="utf-8"):
            errors.append("metrics must export abs_p2p_native_tx_gossip_gate (v1.3.108)")
        # v1.3.109 — singular block payload gate
        if "check_block_payload" not in transport_rs or "v1.3.109" not in transport_rs:
            errors.append("p2p_transport must expose singular block gate (v1.3.109)")
        if "native_block_payload_gate" not in p2p_py:
            errors.append("p2p_node must expose native_block_payload_gate (v1.3.109)")
        if "abs_p2p_native_block_payload_gate" not in (
            ROOT / "observability" / "metrics.py"
        ).read_text(encoding="utf-8"):
            errors.append("metrics must export abs_p2p_native_block_payload_gate (v1.3.109)")
        # v1.3.110 — peer discovery shape gates
        if "check_peers_list_payload" not in transport_rs or "v1.3.110" not in transport_rs:
            errors.append("p2p_transport must expose peers list gate (v1.3.110)")
        if "check_validator_register_payload" not in transport_rs:
            errors.append("p2p_transport must expose validator_register gate (v1.3.110)")
        if "native_peer_discovery_gate" not in p2p_py:
            errors.append("p2p_node must expose native_peer_discovery_gate (v1.3.110)")
        if "abs_p2p_native_peer_discovery_gate" not in (
            ROOT / "observability" / "metrics.py"
        ).read_text(encoding="utf-8"):
            errors.append("metrics must export abs_p2p_native_peer_discovery_gate (v1.3.110)")
        # v1.3.111 — state-root shape gates
        if "check_state_root_request_payload" not in transport_rs or "v1.3.111" not in transport_rs:
            errors.append("p2p_transport must expose state_root_request gate (v1.3.111)")
        if "check_state_root_response_payload" not in transport_rs:
            errors.append("p2p_transport must expose state_root_response gate (v1.3.111)")
        if "native_state_root_gate" not in p2p_py:
            errors.append("p2p_node must expose native_state_root_gate (v1.3.111)")
        if "abs_p2p_native_state_root_gate" not in (
            ROOT / "observability" / "metrics.py"
        ).read_text(encoding="utf-8"):
            errors.append("metrics must export abs_p2p_native_state_root_gate (v1.3.111)")
        # v1.3.112 — cross-shard shape gates
        if "check_cross_shard_tx_payload" not in transport_rs or "v1.3.112" not in transport_rs:
            errors.append("p2p_transport must expose cross_shard_tx gate (v1.3.112)")
        if "check_cross_shard_ack_payload" not in transport_rs:
            errors.append("p2p_transport must expose cross_shard_ack gate (v1.3.112)")
        if "check_shard_migration_payload" not in transport_rs:
            errors.append("p2p_transport must expose shard_migration gate (v1.3.112)")
        if "native_cross_shard_gate" not in p2p_py:
            errors.append("p2p_node must expose native_cross_shard_gate (v1.3.112)")
        if "abs_p2p_native_cross_shard_gate" not in (
            ROOT / "observability" / "metrics.py"
        ).read_text(encoding="utf-8"):
            errors.append("metrics must export abs_p2p_native_cross_shard_gate (v1.3.112)")
        # v1.3.113 — handshake payload gate
        if "check_handshake_payload" not in transport_rs or "v1.3.113" not in transport_rs:
            errors.append("p2p_transport must expose handshake payload gate (v1.3.113)")
        if "native_handshake_payload_gate" not in p2p_py:
            errors.append("p2p_node must expose native_handshake_payload_gate (v1.3.113)")
        if "abs_p2p_native_handshake_payload_gate" not in (
            ROOT / "observability" / "metrics.py"
        ).read_text(encoding="utf-8"):
            errors.append("metrics must export abs_p2p_native_handshake_payload_gate (v1.3.113)")
        # v1.3.114 — prod-mandatory native transport + skip dual shape re-validate
        if "prod mode requires p2p_native_transport" not in (
            ROOT / "runtime" / "config.py"
        ).read_text(encoding="utf-8"):
            errors.append("config must fail-closed for prod p2p_native_transport (v1.3.114)")
        if '"p2p_native_transport"' not in (
            ROOT / "scripts" / "prod_gate.py"
        ).read_text(encoding="utf-8"):
            errors.append("prod_gate must require p2p_native_transport (v1.3.114)")
        if "must_native_tx" not in p2p_py or "native_shape_revalidate" not in p2p_py:
            errors.append("p2p_node must fail-closed + skip dual shape re-validate (v1.3.114)")
        if "abs_p2p_native_shape_revalidate" not in (
            ROOT / "observability" / "metrics.py"
        ).read_text(encoding="utf-8"):
            errors.append("metrics must export abs_p2p_native_shape_revalidate (v1.3.114)")
        # v1.3.115 — handshake policy fuse + native ready listener
        if "check_handshake_policy" not in transport_rs or "v1.3.115" not in transport_rs:
            errors.append("p2p_transport must expose handshake policy fuse (v1.3.115)")
        if "native_policy_applied" not in p2p_py or "native_handshake_policy_gate" not in p2p_py:
            errors.append("p2p_node must wire native handshake policy (v1.3.115)")
        if 'getattr(p2p, "_native_listener", None) is not None' not in (
            ROOT / "api" / "http.py"
        ).read_text(encoding="utf-8"):
            errors.append("/health/ready must accept native _native_listener (v1.3.115)")
        if "abs_p2p_native_handshake_policy_gate" not in (
            ROOT / "observability" / "metrics.py"
        ).read_text(encoding="utf-8"):
            errors.append("metrics must export abs_p2p_native_handshake_policy_gate (v1.3.115)")
        # v1.3.116 — message-loop event shell
        if "read_message_loop_events" not in transport_rs or "v1.3.116" not in transport_rs:
            errors.append("p2p_transport must expose read_message_loop_events (v1.3.116)")
        if "recv_loop_events" not in p2p_py or "native_message_loop_shell" not in p2p_py:
            errors.append("p2p_node must wire native message-loop shell (v1.3.116)")
        if "abs_p2p_native_message_loop_shell" not in (
            ROOT / "observability" / "metrics.py"
        ).read_text(encoding="utf-8"):
            errors.append("metrics must export abs_p2p_native_message_loop_shell (v1.3.116)")
        # v1.3.117 — attestation semantic gate on loop-shell
        if "check_attestation_semantics" not in transport_rs or "v1.3.117" not in transport_rs:
            errors.append("p2p_transport must expose attestation semantic gate (v1.3.117)")
        if "verify_attestation_semantics_inner" not in (
            ROOT / "native" / "abs_native" / "src" / "p2p_wire.rs"
        ).read_text(encoding="utf-8"):
            errors.append("p2p_wire must expose verify_attestation_semantics_inner (v1.3.117)")
        if "native_attestation_semantic_gate" not in p2p_py:
            errors.append("p2p_node must expose native_attestation_semantic_gate (v1.3.117)")
        if "abs_p2p_native_attestation_semantic_gate" not in (
            ROOT / "observability" / "metrics.py"
        ).read_text(encoding="utf-8"):
            errors.append(
                "metrics must export abs_p2p_native_attestation_semantic_gate (v1.3.117)"
            )
        # v1.3.118 — new_tx signature semantic gate on loop-shell
        if "check_wire_tx_semantics" not in transport_rs or "v1.3.118" not in transport_rs:
            errors.append("p2p_transport must expose new_tx semantic gate (v1.3.118)")
        if "verify_wire_tx_signature_inner" not in (
            ROOT / "native" / "abs_native" / "src" / "p2p_wire.rs"
        ).read_text(encoding="utf-8"):
            errors.append("p2p_wire must expose verify_wire_tx_signature_inner (v1.3.118)")
        if "native_tx_semantic_gate" not in p2p_py:
            errors.append("p2p_node must expose native_tx_semantic_gate (v1.3.118)")
        if "abs_p2p_native_tx_semantic_gate" not in (
            ROOT / "observability" / "metrics.py"
        ).read_text(encoding="utf-8"):
            errors.append("metrics must export abs_p2p_native_tx_semantic_gate (v1.3.118)")
        # v1.3.119 — mempool batch signature semantic gate on loop-shell
        if "check_mempool_batch_semantics" not in transport_rs or "v1.3.119" not in transport_rs:
            errors.append("p2p_transport must expose mempool semantic gate (v1.3.119)")
        if "verify_mempool_batch_signatures_inner" not in (
            ROOT / "native" / "abs_native" / "src" / "p2p_wire.rs"
        ).read_text(encoding="utf-8"):
            errors.append(
                "p2p_wire must expose verify_mempool_batch_signatures_inner (v1.3.119)"
            )
        if "native_mempool_semantic_gate" not in p2p_py:
            errors.append("p2p_node must expose native_mempool_semantic_gate (v1.3.119)")
        if "abs_p2p_native_mempool_semantic_gate" not in (
            ROOT / "observability" / "metrics.py"
        ).read_text(encoding="utf-8"):
            errors.append(
                "metrics must export abs_p2p_native_mempool_semantic_gate (v1.3.119)"
            )
        # v1.3.120 — new_block canonical-hash semantic gate on loop-shell
        if "check_block_announce_semantics" not in transport_rs or "v1.3.120" not in transport_rs:
            errors.append("p2p_transport must expose block semantic gate (v1.3.120)")
        if "verify_block_announce_semantics_inner" not in (
            ROOT / "native" / "abs_native" / "src" / "p2p_wire.rs"
        ).read_text(encoding="utf-8"):
            errors.append(
                "p2p_wire must expose verify_block_announce_semantics_inner (v1.3.120)"
            )
        if "recomputed_canonical_block_hash" not in (
            ROOT / "native" / "abs_native" / "src" / "lib.rs"
        ).read_text(encoding="utf-8"):
            errors.append("lib.rs must expose recomputed_canonical_block_hash (v1.3.120)")
        if "native_block_semantic_gate" not in p2p_py:
            errors.append("p2p_node must expose native_block_semantic_gate (v1.3.120)")
        if "abs_p2p_native_block_semantic_gate" not in (
            ROOT / "observability" / "metrics.py"
        ).read_text(encoding="utf-8"):
            errors.append(
                "metrics must export abs_p2p_native_block_semantic_gate (v1.3.120)"
            )
        # v1.3.121 — blocks batch hash semantic gate + Makefile
        if "check_blocks_batch_semantics" not in transport_rs or "v1.3.121" not in transport_rs:
            errors.append("p2p_transport must expose blocks batch semantic gate (v1.3.121)")
        if "verify_blocks_batch_semantics_inner" not in (
            ROOT / "native" / "abs_native" / "src" / "p2p_wire.rs"
        ).read_text(encoding="utf-8"):
            errors.append(
                "p2p_wire must expose verify_blocks_batch_semantics_inner (v1.3.121)"
            )
        if "native_blocks_batch_semantic_gate" not in p2p_py:
            errors.append(
                "p2p_node must expose native_blocks_batch_semantic_gate (v1.3.121)"
            )
        makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
        if "test-quick" not in makefile or "build_native.sh" not in makefile:
            errors.append("root Makefile must expose test-quick and build_native.sh (v1.3.121)")
        if "abs_p2p_native_blocks_batch_semantic_gate" not in (
            ROOT / "observability" / "metrics.py"
        ).read_text(encoding="utf-8"):
            errors.append(
                "metrics must export abs_p2p_native_blocks_batch_semantic_gate (v1.3.121)"
            )
        # v1.3.122 — singular block response hash semantic gate
        if "check_block_payload_semantics" not in transport_rs or "v1.3.122" not in transport_rs:
            errors.append(
                "p2p_transport must expose block payload semantic gate (v1.3.122)"
            )
        if "native_block_payload_semantic_gate" not in p2p_py:
            errors.append(
                "p2p_node must expose native_block_payload_semantic_gate (v1.3.122)"
            )
        if "abs_p2p_native_block_payload_semantic_gate" not in (
            ROOT / "observability" / "metrics.py"
        ).read_text(encoding="utf-8"):
            errors.append(
                "metrics must export abs_p2p_native_block_payload_semantic_gate (v1.3.122)"
            )
        # v1.3.123 — state_root_response digest semantic gate
        if (
            "check_state_root_response_semantics" not in transport_rs
            or "v1.3.123" not in transport_rs
        ):
            errors.append(
                "p2p_transport must expose state_root_response semantic gate (v1.3.123)"
            )
        if "verify_state_root_response_semantics_inner" not in (
            ROOT / "native" / "abs_native" / "src" / "p2p_wire.rs"
        ).read_text(encoding="utf-8"):
            errors.append(
                "p2p_wire must expose verify_state_root_response_semantics_inner (v1.3.123)"
            )
        if "native_state_root_response_semantic_gate" not in p2p_py:
            errors.append(
                "p2p_node must expose native_state_root_response_semantic_gate (v1.3.123)"
            )
        if "abs_p2p_native_state_root_response_semantic_gate" not in (
            ROOT / "observability" / "metrics.py"
        ).read_text(encoding="utf-8"):
            errors.append(
                "metrics must export abs_p2p_native_state_root_response_semantic_gate (v1.3.123)"
            )
        # v1.3.124 — status.head_hash digest semantic gate
        if (
            "check_status_head_hash_semantics" not in transport_rs
            or "v1.3.124" not in transport_rs
        ):
            errors.append(
                "p2p_transport must expose status head_hash semantic gate (v1.3.124)"
            )
        if "verify_status_head_hash_semantics_inner" not in (
            ROOT / "native" / "abs_native" / "src" / "p2p_wire.rs"
        ).read_text(encoding="utf-8"):
            errors.append(
                "p2p_wire must expose verify_status_head_hash_semantics_inner (v1.3.124)"
            )
        if "native_status_head_hash_semantic_gate" not in p2p_py:
            errors.append(
                "p2p_node must expose native_status_head_hash_semantic_gate (v1.3.124)"
            )
        if "abs_p2p_native_status_head_hash_semantic_gate" not in (
            ROOT / "observability" / "metrics.py"
        ).read_text(encoding="utf-8"):
            errors.append(
                "metrics must export abs_p2p_native_status_head_hash_semantic_gate (v1.3.124)"
            )
        # v1.3.125 — request-bound blocks response + prod shell contract
        if "verify_blocks_response_semantics_inner" not in (
            ROOT / "native" / "abs_native" / "src" / "p2p_wire.rs"
        ).read_text(encoding="utf-8"):
            errors.append(
                "p2p_wire must expose verify_blocks_response_semantics_inner (v1.3.125)"
            )
        if "verify_p2p_blocks_response_semantics" not in p2p_py:
            errors.append(
                "p2p_node must call verify_p2p_blocks_response_semantics (v1.3.125)"
            )
        if "stale wheel is not prod-safe" not in p2p_py:
            errors.append("p2p_node must fail-closed on missing loop shell in prod (v1.3.125)")
        if "p2p_native_message_loop_shell" not in (
            ROOT / "api" / "http.py"
        ).read_text(encoding="utf-8"):
            errors.append("/health/ready must expose p2p_native_message_loop_shell (v1.3.125)")
        if "abs_p2p_native_blocks_response_semantic_gate" not in (
            ROOT / "observability" / "metrics.py"
        ).read_text(encoding="utf-8"):
            errors.append(
                "metrics must export abs_p2p_native_blocks_response_semantic_gate (v1.3.125)"
            )
        # v1.3.126 — request-bound singular block response hash correlation
        if "verify_block_response_semantics_inner" not in (
            ROOT / "native" / "abs_native" / "src" / "p2p_wire.rs"
        ).read_text(encoding="utf-8"):
            errors.append(
                "p2p_wire must expose verify_block_response_semantics_inner (v1.3.126)"
            )
        if "verify_p2p_block_response_semantics" not in p2p_py:
            errors.append(
                "p2p_node must call verify_p2p_block_response_semantics (v1.3.126)"
            )
        if "abs_p2p_native_block_response_semantic_gate" not in (
            ROOT / "observability" / "metrics.py"
        ).read_text(encoding="utf-8"):
            errors.append(
                "metrics must export abs_p2p_native_block_response_semantic_gate (v1.3.126)"
            )
        # v1.3.127 — request-bound state_root_response height correlation
        if "verify_state_root_response_request_semantics_inner" not in (
            ROOT / "native" / "abs_native" / "src" / "p2p_wire.rs"
        ).read_text(encoding="utf-8"):
            errors.append(
                "p2p_wire must expose verify_state_root_response_request_semantics_inner (v1.3.127)"
            )
        if "verify_p2p_state_root_response_request_semantics" not in p2p_py:
            errors.append(
                "p2p_node must call verify_p2p_state_root_response_request_semantics (v1.3.127)"
            )
        if "abs_p2p_native_state_root_response_request_gate" not in (
            ROOT / "observability" / "metrics.py"
        ).read_text(encoding="utf-8"):
            errors.append(
                "metrics must export abs_p2p_native_state_root_response_request_gate (v1.3.127)"
            )
        # v1.3.128 — discovery dialability + soft height↔head binding
        if "p2p_peer_addr_is_dialable_inner" not in (
            ROOT / "native" / "abs_native" / "src" / "p2p_ingress.rs"
        ).read_text(encoding="utf-8"):
            errors.append(
                "p2p_ingress must expose p2p_peer_addr_is_dialable_inner (v1.3.128)"
            )
        if "verify_handshake_head_semantics_inner" not in (
            ROOT / "native" / "abs_native" / "src" / "p2p_wire.rs"
        ).read_text(encoding="utf-8"):
            errors.append(
                "p2p_wire must expose verify_handshake_head_semantics_inner (v1.3.128)"
            )
        if "p2p_peer_addr_is_dialable" not in p2p_py:
            errors.append("p2p_node must call p2p_peer_addr_is_dialable (v1.3.128)")
        if "verify_p2p_status_height_head_binding" not in p2p_py and (
            "verify_p2p_status_height_head_binding" not in dispatch_handlers
        ):
            errors.append(
                "p2p_node must call verify_p2p_status_height_head_binding (v1.3.128)"
            )
        if "abs_p2p_native_discovery_dialability_gate" not in (
            ROOT / "observability" / "metrics.py"
        ).read_text(encoding="utf-8"):
            errors.append(
                "metrics must export abs_p2p_native_discovery_dialability_gate (v1.3.128)"
            )
        # v1.3.129 — outbound state_root height honesty
        if "_state_root_response_for_height" not in p2p_py:
            errors.append(
                "p2p_node must expose _state_root_response_for_height (v1.3.129)"
            )
        if (
            "must not inflate peer.height" not in p2p_py
            and "must not inflate peer tip" not in p2p_py
        ):
            errors.append(
                "p2p_node must refuse peer.height inflation from state_root_response (v1.3.129)"
            )
        if "abs_p2p_native_state_root_outbound_honesty" not in (
            ROOT / "observability" / "metrics.py"
        ).read_text(encoding="utf-8"):
            errors.append(
                "metrics must export abs_p2p_native_state_root_outbound_honesty (v1.3.129)"
            )
        # v1.3.130 — soft expected_head + professional repo surface
        if "bad_state_root_response_head" not in (
            ROOT / "native" / "abs_native" / "src" / "p2p_wire.rs"
        ).read_text(encoding="utf-8"):
            errors.append(
                "p2p_wire must expose bad_state_root_response_head (v1.3.130)"
            )
        if "expected_head" not in p2p_py:
            errors.append("p2p_node must pass expected_head on state_root waiters (v1.3.130)")
        if not (ROOT / ".github" / "dependabot.yml").is_file():
            errors.append("missing .github/dependabot.yml (v1.3.130)")
        if not (ROOT / "docs" / "AUDITS.md").is_file():
            errors.append("missing docs/AUDITS.md (v1.3.130)")
        if "abs_p2p_native_state_root_response_head_gate" not in (
            ROOT / "observability" / "metrics.py"
        ).read_text(encoding="utf-8"):
            errors.append(
                "metrics must export abs_p2p_native_state_root_response_head_gate (v1.3.130)"
            )
        # v1.3.131 — solicit-only mempool + status height ahead cap
        if "unsolicited_mempool" not in p2p_py:
            errors.append("p2p_node must strike unsolicited_mempool (v1.3.131)")
        if 'kind": "mempool"' not in p2p_py:
            errors.append("p2p_node must use mempool request_ctx (v1.3.131)")
        if "p2p_max_peer_height_ahead" not in (
            ROOT / "runtime" / "config.py"
        ).read_text(encoding="utf-8"):
            errors.append("config must expose p2p_max_peer_height_ahead (v1.3.131)")
        if "abs_p2p_native_mempool_solicit_only" not in (
            ROOT / "observability" / "metrics.py"
        ).read_text(encoding="utf-8"):
            errors.append(
                "metrics must export abs_p2p_native_mempool_solicit_only (v1.3.131)"
            )
        # v1.3.132 — resilient bootstrap redial (sticky-first-peer fix)
        if "_missing_bootstrap_addrs" not in p2p_py:
            errors.append("p2p_node must expose _missing_bootstrap_addrs (v1.3.132)")
        if "native_bootstrap_resilient" not in p2p_py:
            errors.append("p2p_node must advertise native_bootstrap_resilient (v1.3.132)")
        if "abs_p2p_native_bootstrap_resilient" not in (
            ROOT / "observability" / "metrics.py"
        ).read_text(encoding="utf-8"):
            errors.append(
                "metrics must export abs_p2p_native_bootstrap_resilient (v1.3.132)"
            )
        # v1.3.133 — authenticated bootstrap seed pins
        if "bootstrap_pin_map" not in (
            ROOT / "network" / "p2p_tls.py"
        ).read_text(encoding="utf-8"):
            errors.append("p2p_tls must expose bootstrap_pin_map (v1.3.133)")
        if "native_bootstrap_pin_gate" not in p2p_py:
            errors.append("p2p_node must advertise native_bootstrap_pin_gate (v1.3.133)")
        if "p2p_bootstrap_pins" not in (
            ROOT / "runtime" / "config.py"
        ).read_text(encoding="utf-8"):
            errors.append("config must expose p2p_bootstrap_pins (v1.3.133)")
        if "abs_p2p_native_bootstrap_pin_gate" not in (
            ROOT / "observability" / "metrics.py"
        ).read_text(encoding="utf-8"):
            errors.append(
                "metrics must export abs_p2p_native_bootstrap_pin_gate (v1.3.133)"
            )
        # v1.3.134 — soft NEW_BLOCK height-ahead ownership gate
        if "new_block_height_cap_total" not in p2p_py:
            errors.append("p2p_node must track new_block_height_cap_total (v1.3.134)")
        if "native_new_block_height_cap" not in p2p_py:
            errors.append("p2p_node must advertise native_new_block_height_cap (v1.3.134)")
        if "abs_p2p_native_new_block_height_cap" not in (
            ROOT / "observability" / "metrics.py"
        ).read_text(encoding="utf-8"):
            errors.append(
                "metrics must export abs_p2p_native_new_block_height_cap (v1.3.134)"
            )
        # v1.3.135 — local state_root consistency + handshake/status tip ownership
        if "_state_root_request_ctx" not in p2p_py:
            errors.append("p2p_node must expose _state_root_request_ctx (v1.3.135)")
        if "bad_state_root_response_local_root" not in solicit_surface:
            errors.append(
                "p2p_node must surface bad_state_root_response_local_root (v1.3.135)"
            )
        if "Tip-race state_root solicit" not in p2p_py:
            errors.append(
                "P2P soft-refuse must include bad_state_root_response_local_root "
                "(tip-race must not 300s-ban the miner)"
            )
        if "Soft ownership bind races" not in p2p_py or "Counting recv_error toward 300s ban" not in p2p_py:
            errors.append(
                "P2P soft-refuse must include handshake_head_height_mismatch and recv_error "
                "(mesh_min>=2 must not self-ban on tip/EOF races)"
            )
        if "under_mesh soak WARN" not in p2p_py:
            errors.append(
                "p2p catch-up must reconnect_known_peers when under mesh_min (evm48 soft)"
            )
        if "mid_session_handshake_libp2p" not in p2p_py:
            errors.append(
                "libp2p mid-session Absolute handshake must soft-refuse (no 300s soak ban)"
            )
        if "native_handshake_height_cap" not in p2p_py:
            errors.append("p2p_node must advertise native_handshake_height_cap (v1.3.135)")
        if "abs_p2p_state_root_local_rejects_total" not in (
            ROOT / "observability" / "metrics.py"
        ).read_text(encoding="utf-8"):
            errors.append(
                "metrics must export abs_p2p_state_root_local_rejects_total (v1.3.135)"
            )
        # v1.3.136 — soft attestation slot-ahead ownership gate
        if "_attestation_ahead_reject_reason" not in p2p_py:
            errors.append(
                "p2p_node must expose _attestation_ahead_reject_reason (v1.3.136)"
            )
        if "p2p_max_attestation_slot_ahead" not in (
            ROOT / "runtime" / "config.py"
        ).read_text(encoding="utf-8"):
            errors.append(
                "config must expose p2p_max_attestation_slot_ahead (v1.3.136)"
            )
        if "abs_p2p_native_attestation_slot_ahead" not in (
            ROOT / "observability" / "metrics.py"
        ).read_text(encoding="utf-8"):
            errors.append(
                "metrics must export abs_p2p_native_attestation_slot_ahead (v1.3.136)"
            )
        # v1.3.137 — attestation local-head + solicit-only block responses
        if "_attestation_local_head_reject_reason" not in p2p_py:
            errors.append(
                "p2p_node must expose _attestation_local_head_reject_reason (v1.3.137)"
            )
        if "unsolicited_blocks" not in solicit_surface:
            errors.append("p2p_node must strike unsolicited_blocks (v1.3.137)")
        if "abs_p2p_native_block_solicit_only" not in (
            ROOT / "observability" / "metrics.py"
        ).read_text(encoding="utf-8"):
            errors.append(
                "metrics must export abs_p2p_native_block_solicit_only (v1.3.137)"
            )
        # v1.3.138 — solicit-only state_root + ceremony_status honesty
        if "unsolicited_state_root_response" not in solicit_surface:
            errors.append(
                "p2p_node must strike unsolicited_state_root_response (v1.3.138)"
            )
        if not (ROOT / "scripts" / "ceremony_status.py").is_file():
            errors.append("scripts/ceremony_status.py missing (v1.3.138)")
        if "ceremony_status" not in (
            ROOT / "scripts" / "check_all.ps1"
        ).read_text(encoding="utf-8"):
            errors.append("check_all.ps1 must invoke ceremony_status (v1.3.138)")
        if "abs_p2p_native_state_root_solicit_only" not in (
            ROOT / "observability" / "metrics.py"
        ).read_text(encoding="utf-8"):
            errors.append(
                "metrics must export abs_p2p_native_state_root_solicit_only (v1.3.138)"
            )
        # v1.3.139 — catch-up requires peer.head
        if "_catch_up_ahead_refuse_reason" not in p2p_py:
            errors.append(
                "p2p_node must expose _catch_up_ahead_refuse_reason (v1.3.139)"
            )
        if "p2p_catch_up_require_head" not in (
            ROOT / "runtime" / "config.py"
        ).read_text(encoding="utf-8"):
            errors.append("config must expose p2p_catch_up_require_head (v1.3.139)")
        if "abs_p2p_native_catch_up_require_head" not in (
            ROOT / "observability" / "metrics.py"
        ).read_text(encoding="utf-8"):
            errors.append(
                "metrics must export abs_p2p_native_catch_up_require_head (v1.3.139)"
            )
        # v1.3.140 — SyncEngine never invents peer.head from local blocks
        sync_py = (ROOT / "sync" / "sync_engine.py").read_text(encoding="utf-8")
        if "never invent peer.head" not in sync_py:
            errors.append("sync_engine must refuse inventing peer.head (v1.3.140)")
        if "get_block(peer.height)" in sync_py:
            errors.append(
                "sync_engine must not invent head via get_block(peer.height) (v1.3.140)"
            )
        if "abs_p2p_native_sync_heads_no_invent" not in (
            ROOT / "observability" / "metrics.py"
        ).read_text(encoding="utf-8"):
            errors.append(
                "metrics must export abs_p2p_native_sync_heads_no_invent (v1.3.140)"
            )
        # v1.3.141 — sync_state same-height match is wire-only
        if (
            "same-height consistency only from wire roots" not in sync_py
            and "native_sync_state_wire_only" not in sync_py
        ):
            errors.append(
                "sync_engine must document wire-only same-height match (v1.3.141)"
            )
        if "get_block(peer_height)" in sync_py:
            errors.append(
                "sync_engine must not invent same-height match via get_block(peer_height) (v1.3.141)"
            )
        if "native_sync_state_wire_only" not in sync_py:
            errors.append(
                "sync_engine must expose native_sync_state_wire_only (v1.3.141)"
            )
        if "abs_p2p_native_sync_state_wire_only" not in (
            ROOT / "observability" / "metrics.py"
        ).read_text(encoding="utf-8"):
            errors.append(
                "metrics must export abs_p2p_native_sync_state_wire_only (v1.3.141)"
            )
        # v1.3.143 — mempool cheap-refuse + new_tx primary rate
        p2p_py = (ROOT / "network" / "p2p_node.py").read_text(encoding="utf-8")
        if "native_mempool_cheap_refuse" not in p2p_py:
            errors.append("p2p must expose native_mempool_cheap_refuse (v1.3.143)")
        if "MSG_NEW_TX," in p2p_py.split("RATE_LIMIT_EXEMPT_TYPES")[1].split("})")[0]:
            errors.append("RATE_LIMIT_EXEMPT_TYPES must not list MSG_NEW_TX (v1.3.143)")
        if "def _class_rate_ok" not in p2p_py:
            errors.append("P2P must enforce per-class rate quotas (attest/tx/block)")
        if "rate_limit_class_exceeded" not in p2p_py:
            errors.append("P2P class quota must soft-refuse rate_limit_class_exceeded")
        if "_send_ctrl_q" not in p2p_py:
            errors.append("priority P2P send must enqueue on ctrl queue, not take write lock on caller")
        if "_send_root_q" not in p2p_py:
            errors.append("state_root must have its own send queue ahead of BLOCK/STATUS")
        if "state_root enqueue does not wait the write Future" not in p2p_py:
            errors.append("state_root send must not wait the write Future (solicit waiter owns RTT)")
        tx_pipe_py = (ROOT / "core" / "components" / "tx_pipeline.py").read_text(
            encoding="utf-8", errors="replace"
        )
        if (
            "nonce/balance DB lookups" not in (
                ROOT / "core" / "blockchain.py"
            ).read_text(encoding="utf-8")
            and "nonce/balance DB lookups" not in tx_pipe_py
        ):
            errors.append("validate_transaction must verify sig before DB (v1.3.143)")
        if "abs_p2p_native_mempool_cheap_refuse" not in (
            ROOT / "observability" / "metrics.py"
        ).read_text(encoding="utf-8"):
            errors.append(
                "metrics must export abs_p2p_native_mempool_cheap_refuse (v1.3.143)"
            )
        # v1.3.144 — native solicit-armed mempool shell
        if "mempool_solicit_armed" not in (
            ROOT / "native" / "abs_native" / "src" / "p2p_transport.rs"
        ).read_text(encoding="utf-8"):
            errors.append(
                "p2p_transport must expose mempool_solicit_armed (v1.3.144)"
            )
        if "_mempool_solicit_armed_for" not in p2p_py:
            errors.append("p2p must expose _mempool_solicit_armed_for (v1.3.144)")
        if "abs_p2p_native_mempool_solicit_armed_shell" not in (
            ROOT / "observability" / "metrics.py"
        ).read_text(encoding="utf-8"):
            errors.append(
                "metrics must export abs_p2p_native_mempool_solicit_armed_shell (v1.3.144)"
            )
        # v1.3.145 — peer score quality (strikes + import fails)
        if "native_peer_score_quality" not in p2p_py:
            errors.append("p2p must expose native_peer_score_quality (v1.3.145)")
        if "_note_peer_import_fail" not in p2p_py:
            errors.append("p2p must attribute import fails to peers (v1.3.145)")
        if "abs_p2p_native_peer_score_quality" not in (
            ROOT / "observability" / "metrics.py"
        ).read_text(encoding="utf-8"):
            errors.append(
                "metrics must export abs_p2p_native_peer_score_quality (v1.3.145)"
            )
        # v1.3.146 — catch-up tip probe + head↔height bind
        if "catch_up_head_height_mismatch" not in p2p_py:
            errors.append(
                "p2p must refuse catch-up on head/height mismatch (v1.3.146)"
            )
        if "_catch_up_local_tip_probe_refuse_reason" not in p2p_py:
            errors.append("p2p must probe local tip before catch-up (v1.3.146)")
        if "p2p_catch_up_tip_probe" not in (
            ROOT / "runtime" / "config.py"
        ).read_text(encoding="utf-8"):
            errors.append("config must expose p2p_catch_up_tip_probe (v1.3.146)")
        if "abs_p2p_native_catch_up_tip_probe" not in (
            ROOT / "observability" / "metrics.py"
        ).read_text(encoding="utf-8"):
            errors.append(
                "metrics must export abs_p2p_native_catch_up_tip_probe (v1.3.146)"
            )
        # v1.3.147 — typed Rocks account-row ABAR codec
        account_row_rs = (
            ROOT / "native" / "abs_native" / "src" / "account_row.rs"
        ).read_text(encoding="utf-8")
        if "pack_account_row_value" not in account_row_rs:
            errors.append("native must expose pack_account_row_value (v1.3.147)")
        if "account_blob_to_value" not in account_row_rs:
            errors.append("native must dual-decode account blobs (v1.3.147)")
        rocks_py = (ROOT / "storage" / "rocks_store.py").read_text(encoding="utf-8")
        if "_pack_account_blob" not in rocks_py:
            errors.append("rocks_store must pack ABAR account rows (v1.3.147)")
        if "_loads_account_blob_or_none" not in rocks_py:
            errors.append("rocks_store must dual-read account blobs (v1.3.147)")
        keycodec_py = (ROOT / "storage" / "keycodec.py").read_text(encoding="utf-8")
        if "def prefix_evm_logs_block" not in keycodec_py:
            errors.append(
                "keycodec must expose prefix_evm_logs_block for height-bounded log seeks"
            )
        if "def prefix_family_end" not in keycodec_py:
            errors.append(
                "keycodec must expose prefix_family_end for exclusive family scans"
            )
        qlog_fn = rocks_py.split("def query_evm_logs", 1)[-1].split(
            "def _decode_nft_token", 1
        )[0]
        if "_scan_prefix" in qlog_fn:
            errors.append(
                "Rocks query_evm_logs must not prefix-scan; delegate to _scan_evm_log_blobs"
            )
        if "_scan_evm_log_blobs" not in qlog_fn:
            errors.append("Rocks query_evm_logs must seek via _scan_evm_log_blobs")
        evm_blob_fn = rocks_py.split("def _scan_evm_log_blobs", 1)[-1].split(
            "def query_evm_logs", 1
        )[0]
        if "_scan_prefix(kc.prefix_evm_logs()" in evm_blob_fn:
            errors.append("_scan_evm_log_blobs must not scan the full P_EVM_LOG family")
        if "prefix_evm_logs_block" not in evm_blob_fn:
            errors.append("_scan_evm_log_blobs must seek per-height EVM log prefixes")
        # v1.3.148 — typed Rocks tx-row ATXV codec
        tx_row_rs = (ROOT / "native" / "abs_native" / "src" / "tx_row.rs").read_text(
            encoding="utf-8"
        )
        if "pack_tx_row_value" not in tx_row_rs:
            errors.append("native must expose pack_tx_row_value (v1.3.148)")
        if "tx_blob_to_value" not in tx_row_rs:
            errors.append("native must dual-decode tx blobs (v1.3.148)")
        if "TX_ROW_VERSION: u8 = 2" not in tx_row_rs:
            errors.append("ATXV tx_row must pack satoshi money as version 2")
        if "TX_ROW_VERSION_V1" not in tx_row_rs:
            errors.append("ATXV tx_row must dual-read v1 blobs")
        if "FLAG_GAS_USED_UNOBSERVED" not in tx_row_rs:
            errors.append("ATXV tx_row must not invent unobserved gas_used")
        if "_pack_tx_blob" not in rocks_py:
            errors.append("rocks_store must pack ATXV tx rows (v1.3.148)")
        if "_loads_tx_blob_or_none" not in rocks_py:
            errors.append("rocks_store must dual-read tx blobs (v1.3.148)")
        # v1.3.149 — typed Rocks block-row ABLK codec
        block_row_rs = (
            ROOT / "native" / "abs_native" / "src" / "block_row.rs"
        ).read_text(encoding="utf-8")
        if "pack_block_row_value" not in block_row_rs:
            errors.append("native must expose pack_block_row_value (v1.3.149)")
        if "block_blob_to_value" not in block_row_rs:
            errors.append("native must dual-decode block blobs (v1.3.149)")
        if "_pack_block_blob" not in rocks_py:
            errors.append("rocks_store must pack ABLK block rows (v1.3.149)")
        if "_loads_block_blob_or_none" not in rocks_py:
            errors.append("rocks_store must dual-read block blobs (v1.3.149)")
        # v1.3.150 — Standard needles aligned with new_tx rate + dual-read helpers
        p2p_test = (
            ROOT / "tests" / "unit" / "test_p2p_industrial.py"
        ).read_text(encoding="utf-8")
        if "MSG_NEW_TX not in RATE_LIMIT_EXEMPT_TYPES" not in p2p_test:
            errors.append(
                "p2p industrial test must assert new_tx not exempt (v1.3.150)"
            )
        supply_test = (
            ROOT / "tests" / "unit" / "test_supply_broadcast_honesty.py"
        ).read_text(encoding="utf-8")
        if "_loads_tx_blob_or_none" not in supply_test:
            errors.append(
                "supply honesty test must accept tx dual-read helper (v1.3.150)"
            )
        # v1.3.151 — typed Rocks receipt-row ATXR codec
        receipt_row_rs = (
            ROOT / "native" / "abs_native" / "src" / "receipt_row.rs"
        ).read_text(encoding="utf-8")
        if "pack_receipt_row_value" not in receipt_row_rs:
            errors.append("native must expose pack_receipt_row_value (v1.3.151)")
        if "RECEIPT_ROW_VERSION: u8 = 2" not in receipt_row_rs:
            errors.append("ATXR receipt_row must pack satoshi money as version 2")
        if "RECEIPT_ROW_VERSION_V1" not in receipt_row_rs:
            errors.append("ATXR receipt_row must dual-read v1 blobs")
        if "receipt_blob_to_value" not in receipt_row_rs:
            errors.append("native must dual-decode receipt blobs (v1.3.151)")
        if "_pack_receipt_blob" not in rocks_py:
            errors.append("rocks_store must pack ATXR receipt rows (v1.3.151)")
        if "_loads_receipt_blob_or_none" not in rocks_py:
            errors.append("rocks_store must dual-read receipt blobs (v1.3.151)")
        # v1.3.152 — solicit-only MSG_PEERS discovery
        if "unsolicited_peers" not in p2p_py:
            errors.append("p2p must refuse unsolicited MSG_PEERS (v1.3.152)")
        if "_ingest_discovered_peers" not in p2p_py:
            errors.append("p2p must ingest solicited peers via helper (v1.3.152)")
        if "native_peers_solicit_only" not in p2p_py:
            errors.append("p2p must expose native_peers_solicit_only (v1.3.152)")
        if "p2p_peers_solicit_only" not in (
            ROOT / "runtime" / "config.py"
        ).read_text(encoding="utf-8"):
            errors.append("config must expose p2p_peers_solicit_only (v1.3.152)")
        if "abs_p2p_native_peers_solicit_only" not in (
            ROOT / "observability" / "metrics.py"
        ).read_text(encoding="utf-8"):
            errors.append(
                "metrics must export abs_p2p_native_peers_solicit_only (v1.3.152)"
            )
        # v1.3.153 — NEW_BLOCK head↔height bind
        if "new_block_head_height_mismatch" not in p2p_py:
            errors.append(
                "p2p must refuse new_block on head/height mismatch (v1.3.153)"
            )
        if "_new_block_head_height_refuse_reason" not in p2p_py:
            errors.append(
                "p2p must expose _new_block_head_height_refuse_reason (v1.3.153)"
            )
        if "p2p_new_block_head_height_bind" not in (
            ROOT / "runtime" / "config.py"
        ).read_text(encoding="utf-8"):
            errors.append(
                "config must expose p2p_new_block_head_height_bind (v1.3.153)"
            )
        if "abs_p2p_native_new_block_head_height_bind" not in (
            ROOT / "observability" / "metrics.py"
        ).read_text(encoding="utf-8"):
            errors.append(
                "metrics must export abs_p2p_native_new_block_head_height_bind (v1.3.153)"
            )
        # v1.3.154 — catch-up peer-head wire probe
        if "catch_up_peer_head_probe_failed" not in p2p_py:
            errors.append(
                "p2p must refuse catch-up on peer-head probe fail (v1.3.154)"
            )
        if "_catch_up_peer_head_probe_refuse_reason" not in p2p_py:
            errors.append(
                "p2p must expose _catch_up_peer_head_probe_refuse_reason (v1.3.154)"
            )
        if "p2p_catch_up_peer_head_probe" not in (
            ROOT / "runtime" / "config.py"
        ).read_text(encoding="utf-8"):
            errors.append(
                "config must expose p2p_catch_up_peer_head_probe (v1.3.154)"
            )
        if "abs_p2p_native_catch_up_peer_head_probe" not in (
            ROOT / "observability" / "metrics.py"
        ).read_text(encoding="utf-8"):
            errors.append(
                "metrics must export abs_p2p_native_catch_up_peer_head_probe (v1.3.154)"
            )
        # v1.3.155 — STATUS/handshake head↔height bind
        if "status_head_height_mismatch" not in p2p_py:
            errors.append(
                "p2p must refuse status on head/height mismatch (v1.3.155)"
            )
        if "_status_head_height_refuse_reason" not in p2p_py:
            errors.append(
                "p2p must expose _status_head_height_refuse_reason (v1.3.155)"
            )
        if "p2p_status_head_height_bind" not in (
            ROOT / "runtime" / "config.py"
        ).read_text(encoding="utf-8"):
            errors.append(
                "config must expose p2p_status_head_height_bind (v1.3.155)"
            )
        if "abs_p2p_native_status_head_height_bind" not in (
            ROOT / "observability" / "metrics.py"
        ).read_text(encoding="utf-8"):
            errors.append(
                "metrics must export abs_p2p_native_status_head_height_bind (v1.3.155)"
            )
        # v1.3.156 — NEW_BLOCK defer tip + announce↔body bind
        if "new_block_announce_hash_mismatch" not in p2p_py:
            errors.append(
                "p2p must refuse new_block on announce/body hash mismatch (v1.3.156)"
            )
        if "_new_block_announce_body_refuse_reason" not in p2p_py:
            errors.append(
                "p2p must expose _new_block_announce_body_refuse_reason (v1.3.156)"
            )
        if "BEFORE tip mutate" not in p2p_py:
            errors.append(
                "p2p must defer new_block tip mutate until body parse (v1.3.156)"
            )
        if "p2p_new_block_announce_body_bind" not in (
            ROOT / "runtime" / "config.py"
        ).read_text(encoding="utf-8"):
            errors.append(
                "config must expose p2p_new_block_announce_body_bind (v1.3.156)"
            )
        if "abs_p2p_native_new_block_announce_body_bind" not in (
            ROOT / "observability" / "metrics.py"
        ).read_text(encoding="utf-8"):
            errors.append(
                "metrics must export abs_p2p_native_new_block_announce_body_bind (v1.3.156)"
            )
        # v1.3.157 — catch-up contiguous peer-head parent bind
        if "catch_up_peer_head_parent_mismatch" not in p2p_py:
            errors.append(
                "p2p must refuse catch-up on +1 peer-head parent mismatch (v1.3.157)"
            )
        if "p2p_catch_up_peer_head_parent_bind" not in (
            ROOT / "runtime" / "config.py"
        ).read_text(encoding="utf-8"):
            errors.append(
                "config must expose p2p_catch_up_peer_head_parent_bind (v1.3.157)"
            )
        if "abs_p2p_native_catch_up_peer_head_parent_bind" not in (
            ROOT / "observability" / "metrics.py"
        ).read_text(encoding="utf-8"):
            errors.append(
                "metrics must export abs_p2p_native_catch_up_peer_head_parent_bind (v1.3.157)"
            )
        # v1.3.158 — JWT HS256 min 32-byte secret
        jwt_py = (ROOT / "middleware" / "jwt_auth.py").read_text(encoding="utf-8")
        if "MIN_HS256_SECRET_BYTES" not in jwt_py:
            errors.append(
                "jwt_auth must expose MIN_HS256_SECRET_BYTES (v1.3.158)"
            )
        if "_assert_hs256_secret" not in jwt_py:
            errors.append(
                "jwt_auth must expose _assert_hs256_secret (v1.3.158)"
            )
        if "SECRET_API_JWT" not in jwt_py or "build_secret_manager" not in jwt_py:
            errors.append(
                "jwt_auth must resolve secret via SecretManagerPort SECRET_API_JWT"
            )
        http_py_stake = (ROOT / "api" / "http.py").read_text(encoding="utf-8")
        if "_http_stake_abs" not in http_py_stake:
            errors.append("api/http.py must expose _http_stake_abs (stake_satoshi)")
        if "stake_satoshi required" not in http_py_stake:
            errors.append("HTTP validators/register must refuse float-only stake in prod")
        if "HS256 requires >= 32 bytes" not in (
            ROOT / "runtime" / "config.py"
        ).read_text(encoding="utf-8"):
            errors.append(
                "config must enforce JWT HS256 >= 32 bytes (v1.3.158)"
            )
        # v1.3.159 — height-cap clears fantasy peer.head
        if "p2p_height_cap_clear_head" not in p2p_py:
            errors.append(
                "p2p must clear fantasy head on height-cap (v1.3.159)"
            )
        if "native_height_cap_clear_head" not in p2p_py:
            errors.append(
                "p2p must expose native_height_cap_clear_head (v1.3.159)"
            )
        if "p2p_height_cap_clear_head" not in (
            ROOT / "runtime" / "config.py"
        ).read_text(encoding="utf-8"):
            errors.append(
                "config must expose p2p_height_cap_clear_head (v1.3.159)"
            )
        if "abs_p2p_native_height_cap_clear_head" not in (
            ROOT / "observability" / "metrics.py"
        ).read_text(encoding="utf-8"):
            errors.append(
                "metrics must export abs_p2p_native_height_cap_clear_head (v1.3.159)"
            )
        # v1.3.160 — NEW_BLOCK contiguous parent bind
        if "new_block_contiguous_parent_mismatch" not in p2p_py:
            errors.append(
                "p2p must refuse +1 new_block on parent mismatch (v1.3.160)"
            )
        if "_new_block_contiguous_parent_refuse_reason" not in p2p_py:
            errors.append(
                "p2p must expose _new_block_contiguous_parent_refuse_reason (v1.3.160)"
            )
        if "p2p_new_block_contiguous_parent_bind" not in (
            ROOT / "runtime" / "config.py"
        ).read_text(encoding="utf-8"):
            errors.append(
                "config must expose p2p_new_block_contiguous_parent_bind (v1.3.160)"
            )
        if "abs_p2p_native_new_block_contiguous_parent_bind" not in (
            ROOT / "observability" / "metrics.py"
        ).read_text(encoding="utf-8"):
            errors.append(
                "metrics must export abs_p2p_native_new_block_contiguous_parent_bind (v1.3.160)"
            )
        # v1.3.161 — STATUS head requires positive height
        if "status_head_without_height" not in p2p_py:
            errors.append(
                "p2p must refuse head-only STATUS when local tip > 0 (v1.3.161)"
            )
        if "p2p_status_head_requires_height" not in (
            ROOT / "runtime" / "config.py"
        ).read_text(encoding="utf-8"):
            errors.append(
                "config must expose p2p_status_head_requires_height (v1.3.161)"
            )
        if "abs_p2p_native_status_head_requires_height" not in (
            ROOT / "observability" / "metrics.py"
        ).read_text(encoding="utf-8"):
            errors.append(
                "metrics must export abs_p2p_native_status_head_requires_height (v1.3.161)"
            )
        # v1.3.162 — fork peer-head wire probe
        if "fork_peer_head_probe_failed" not in p2p_py:
            errors.append(
                "p2p must refuse fork reorg on peer-head probe fail (v1.3.162)"
            )
        if "_fork_peer_head_probe_refuse_reason" not in p2p_py:
            errors.append(
                "p2p must expose _fork_peer_head_probe_refuse_reason (v1.3.162)"
            )
        if "p2p_fork_peer_head_probe" not in (
            ROOT / "runtime" / "config.py"
        ).read_text(encoding="utf-8"):
            errors.append(
                "config must expose p2p_fork_peer_head_probe (v1.3.162)"
            )
        if "abs_p2p_native_fork_peer_head_probe" not in (
            ROOT / "observability" / "metrics.py"
        ).read_text(encoding="utf-8"):
            errors.append(
                "metrics must export abs_p2p_native_fork_peer_head_probe (v1.3.162)"
            )
        # v1.3.163 — reconcile fetched head hash bind
        if "reconcile_head_hash_mismatch" not in p2p_py:
            errors.append(
                "p2p must refuse reconcile on fetched head hash mismatch (v1.3.163)"
            )
        if "_reconcile_fetched_head_refuse_reason" not in p2p_py:
            errors.append(
                "p2p must expose _reconcile_fetched_head_refuse_reason (v1.3.163)"
            )
        if "p2p_reconcile_head_hash_bind" not in (
            ROOT / "runtime" / "config.py"
        ).read_text(encoding="utf-8"):
            errors.append(
                "config must expose p2p_reconcile_head_hash_bind (v1.3.163)"
            )
        if "abs_p2p_native_reconcile_head_hash_bind" not in (
            ROOT / "observability" / "metrics.py"
        ).read_text(encoding="utf-8"):
            errors.append(
                "metrics must export abs_p2p_native_reconcile_head_hash_bind (v1.3.163)"
            )
        # v1.3.164 — GHOST head wire probe
        if "ghost_head_probe_failed" not in p2p_py:
            errors.append(
                "p2p must refuse GHOST reorg on head probe fail (v1.3.164)"
            )
        if "_ghost_head_probe_refuse_reason" not in p2p_py:
            errors.append(
                "p2p must expose _ghost_head_probe_refuse_reason (v1.3.164)"
            )
        if "p2p_ghost_head_probe" not in (
            ROOT / "runtime" / "config.py"
        ).read_text(encoding="utf-8"):
            errors.append(
                "config must expose p2p_ghost_head_probe (v1.3.164)"
            )
        if "abs_p2p_native_ghost_head_probe" not in (
            ROOT / "observability" / "metrics.py"
        ).read_text(encoding="utf-8"):
            errors.append(
                "metrics must export abs_p2p_native_ghost_head_probe (v1.3.164)"
            )
        # v1.3.165 — reconcile contiguous parent bind
        if "reconcile_contiguous_parent_mismatch" not in p2p_py:
            errors.append(
                "p2p must refuse +1 reconcile on parent mismatch (v1.3.165)"
            )
        if "_reconcile_contiguous_parent_refuse_reason" not in p2p_py:
            errors.append(
                "p2p must expose _reconcile_contiguous_parent_refuse_reason (v1.3.165)"
            )
        if "p2p_reconcile_contiguous_parent_bind" not in (
            ROOT / "runtime" / "config.py"
        ).read_text(encoding="utf-8"):
            errors.append(
                "config must expose p2p_reconcile_contiguous_parent_bind (v1.3.165)"
            )
        if "abs_p2p_native_reconcile_contiguous_parent_bind" not in (
            ROOT / "observability" / "metrics.py"
        ).read_text(encoding="utf-8"):
            errors.append(
                "metrics must export abs_p2p_native_reconcile_contiguous_parent_bind (v1.3.165)"
            )
        # v1.3.166 — handshake head requires positive height
        if "handshake_head_without_height" not in p2p_py:
            errors.append(
                "p2p must refuse head-only handshake when local tip > 0 (v1.3.166)"
            )
        if "_handshake_head_without_height_refuse_reason" not in p2p_py:
            errors.append(
                "p2p must expose _handshake_head_without_height_refuse_reason (v1.3.166)"
            )
        if "p2p_handshake_head_requires_height" not in (
            ROOT / "runtime" / "config.py"
        ).read_text(encoding="utf-8"):
            errors.append(
                "config must expose p2p_handshake_head_requires_height (v1.3.166)"
            )
        if "abs_p2p_native_handshake_head_requires_height" not in (
            ROOT / "observability" / "metrics.py"
        ).read_text(encoding="utf-8"):
            errors.append(
                "metrics must export abs_p2p_native_handshake_head_requires_height (v1.3.166)"
            )
        # v1.3.167 — attestation tip target-head bind
        if "attestation_target_head_mismatch" not in p2p_py:
            errors.append(
                "p2p must refuse tip-height attestation for non-tip hash (v1.3.167)"
            )
        if "_attestation_target_head_refuse_reason" not in p2p_py:
            errors.append(
                "p2p must expose _attestation_target_head_refuse_reason (v1.3.167)"
            )
        if "p2p_attestation_target_head_bind" not in (
            ROOT / "runtime" / "config.py"
        ).read_text(encoding="utf-8"):
            errors.append(
                "config must expose p2p_attestation_target_head_bind (v1.3.167)"
            )
        if "abs_p2p_native_attestation_target_head_bind" not in (
            ROOT / "observability" / "metrics.py"
        ).read_text(encoding="utf-8"):
            errors.append(
                "metrics must export abs_p2p_native_attestation_target_head_bind (v1.3.167)"
            )
        # v1.3.168 — fork peer-head parent bind
        if "fork_peer_head_parent_mismatch" not in p2p_py:
            errors.append(
                "p2p must refuse same-height fork on parent mismatch (v1.3.168)"
            )
        if "p2p_fork_peer_head_parent_bind" not in (
            ROOT / "runtime" / "config.py"
        ).read_text(encoding="utf-8"):
            errors.append(
                "config must expose p2p_fork_peer_head_parent_bind (v1.3.168)"
            )
        if "abs_p2p_native_fork_peer_head_parent_bind" not in (
            ROOT / "observability" / "metrics.py"
        ).read_text(encoding="utf-8"):
            errors.append(
                "metrics must export abs_p2p_native_fork_peer_head_parent_bind (v1.3.168)"
            )
        # v1.3.169 — GHOST head parent bind
        if "ghost_head_parent_mismatch" not in p2p_py:
            errors.append(
                "p2p must refuse GHOST reorg on parent mismatch (v1.3.169)"
            )
        if "p2p_ghost_head_parent_bind" not in (
            ROOT / "runtime" / "config.py"
        ).read_text(encoding="utf-8"):
            errors.append(
                "config must expose p2p_ghost_head_parent_bind (v1.3.169)"
            )
        if "abs_p2p_native_ghost_head_parent_bind" not in (
            ROOT / "observability" / "metrics.py"
        ).read_text(encoding="utf-8"):
            errors.append(
                "metrics must export abs_p2p_native_ghost_head_parent_bind (v1.3.169)"
            )
        # v1.3.170 — NEW_BLOCK same-height parent bind
        if "new_block_same_height_parent_mismatch" not in p2p_py:
            errors.append(
                "p2p must refuse same-height new_block on parent mismatch (v1.3.170)"
            )
        if "_new_block_same_height_parent_refuse_reason" not in p2p_py:
            errors.append(
                "p2p must expose _new_block_same_height_parent_refuse_reason (v1.3.170)"
            )
        if "p2p_new_block_same_height_parent_bind" not in (
            ROOT / "runtime" / "config.py"
        ).read_text(encoding="utf-8"):
            errors.append(
                "config must expose p2p_new_block_same_height_parent_bind (v1.3.170)"
            )
        if "abs_p2p_native_new_block_same_height_parent_bind" not in (
            ROOT / "observability" / "metrics.py"
        ).read_text(encoding="utf-8"):
            errors.append(
                "metrics must export abs_p2p_native_new_block_same_height_parent_bind (v1.3.170)"
            )
        # v1.3.171 — reconcile same-height parent bind
        if "reconcile_same_height_parent_mismatch" not in p2p_py:
            errors.append(
                "p2p must refuse same-height reconcile on parent mismatch (v1.3.171)"
            )
        if "_reconcile_same_height_parent_refuse_reason" not in p2p_py:
            errors.append(
                "p2p must expose _reconcile_same_height_parent_refuse_reason (v1.3.171)"
            )
        if "p2p_reconcile_same_height_parent_bind" not in (
            ROOT / "runtime" / "config.py"
        ).read_text(encoding="utf-8"):
            errors.append(
                "config must expose p2p_reconcile_same_height_parent_bind (v1.3.171)"
            )
        if "abs_p2p_native_reconcile_same_height_parent_bind" not in (
            ROOT / "observability" / "metrics.py"
        ).read_text(encoding="utf-8"):
            errors.append(
                "metrics must export abs_p2p_native_reconcile_same_height_parent_bind (v1.3.171)"
            )
        # v1.3.172 — catch-up tip-head bind
        if "catch_up_tip_head_mismatch" not in p2p_py:
            errors.append(
                "p2p must refuse catch-up completion on tip!=peer.head (v1.3.172)"
            )
        if "_catch_up_tip_head_refuse_reason" not in p2p_py:
            errors.append(
                "p2p must expose _catch_up_tip_head_refuse_reason (v1.3.172)"
            )
        if "p2p_catch_up_tip_head_bind" not in (
            ROOT / "runtime" / "config.py"
        ).read_text(encoding="utf-8"):
            errors.append(
                "config must expose p2p_catch_up_tip_head_bind (v1.3.172)"
            )
        if "abs_p2p_native_catch_up_tip_head_bind" not in (
            ROOT / "observability" / "metrics.py"
        ).read_text(encoding="utf-8"):
            errors.append(
                "metrics must export abs_p2p_native_catch_up_tip_head_bind (v1.3.172)"
            )
        # v1.3.173 — reconcile tip-head bind
        if "reconcile_tip_head_mismatch" not in p2p_py:
            errors.append(
                "p2p must refuse reconcile success on tip!=target_head (v1.3.173)"
            )
        if "_reconcile_tip_head_refuse_reason" not in p2p_py:
            errors.append(
                "p2p must expose _reconcile_tip_head_refuse_reason (v1.3.173)"
            )
        if "p2p_reconcile_tip_head_bind" not in (
            ROOT / "runtime" / "config.py"
        ).read_text(encoding="utf-8"):
            errors.append(
                "config must expose p2p_reconcile_tip_head_bind (v1.3.173)"
            )
        if "abs_p2p_native_reconcile_tip_head_bind" not in (
            ROOT / "observability" / "metrics.py"
        ).read_text(encoding="utf-8"):
            errors.append(
                "metrics must export abs_p2p_native_reconcile_tip_head_bind (v1.3.173)"
            )
        # v1.3.174 — NEW_BLOCK tip-head bind
        if "new_block_tip_head_mismatch" not in p2p_py:
            errors.append(
                "p2p must refuse new_block accept on tip!=announce hash (v1.3.174)"
            )
        if "_new_block_tip_head_refuse_reason" not in p2p_py:
            errors.append(
                "p2p must expose _new_block_tip_head_refuse_reason (v1.3.174)"
            )
        if "def _try_local_head" not in p2p_py:
            errors.append("p2p_node must expose _try_local_head for tip-bind honesty")
        if "local_tip_unreadable" not in p2p_py:
            errors.append(
                "p2p_node must refuse local_tip_unreadable instead of skipping tip binds"
            )
        if "p2p_new_block_tip_head_bind" not in (
            ROOT / "runtime" / "config.py"
        ).read_text(encoding="utf-8"):
            errors.append(
                "config must expose p2p_new_block_tip_head_bind (v1.3.174)"
            )
        if "abs_p2p_native_new_block_tip_head_bind" not in (
            ROOT / "observability" / "metrics.py"
        ).read_text(encoding="utf-8"):
            errors.append(
                "metrics must export abs_p2p_native_new_block_tip_head_bind (v1.3.174)"
            )
        # v1.3.175 — catch-up contiguous parent bind
        if "catch_up_contiguous_parent_mismatch" not in p2p_py:
            errors.append(
                "p2p must refuse +1 catch-up import on parent mismatch (v1.3.175)"
            )
        if "_catch_up_contiguous_parent_refuse_reason" not in p2p_py:
            errors.append(
                "p2p must expose _catch_up_contiguous_parent_refuse_reason (v1.3.175)"
            )
        if "p2p_catch_up_contiguous_parent_bind" not in (
            ROOT / "runtime" / "config.py"
        ).read_text(encoding="utf-8"):
            errors.append(
                "config must expose p2p_catch_up_contiguous_parent_bind (v1.3.175)"
            )
        if "abs_p2p_native_catch_up_contiguous_parent_bind" not in (
            ROOT / "observability" / "metrics.py"
        ).read_text(encoding="utf-8"):
            errors.append(
                "metrics must export abs_p2p_native_catch_up_contiguous_parent_bind (v1.3.175)"
            )
        # v1.3.176 — catch-up height continuity bind
        if "catch_up_height_continuity_mismatch" not in p2p_py:
            errors.append(
                "p2p must refuse catch-up import on height!=cursor (v1.3.176)"
            )
        if "_catch_up_height_continuity_refuse_reason" not in p2p_py:
            errors.append(
                "p2p must expose _catch_up_height_continuity_refuse_reason (v1.3.176)"
            )
        if "p2p_catch_up_height_continuity_bind" not in (
            ROOT / "runtime" / "config.py"
        ).read_text(encoding="utf-8"):
            errors.append(
                "config must expose p2p_catch_up_height_continuity_bind (v1.3.176)"
            )
        if "abs_p2p_native_catch_up_height_continuity_bind" not in (
            ROOT / "observability" / "metrics.py"
        ).read_text(encoding="utf-8"):
            errors.append(
                "metrics must export abs_p2p_native_catch_up_height_continuity_bind (v1.3.176)"
            )
        # v1.3.177 — mempool min-fee refuse before validate
        if "fee_too_low" not in p2p_py or "p2p_mempool_min_fee_refuse" not in p2p_py:
            errors.append(
                "p2p must refuse fee<min_fee before validate_transaction (v1.3.177)"
            )
        if "native_mempool_min_fee_refuse" not in p2p_py:
            errors.append(
                "p2p must expose native_mempool_min_fee_refuse (v1.3.177)"
            )
        if "p2p_mempool_min_fee_refuse" not in (
            ROOT / "runtime" / "config.py"
        ).read_text(encoding="utf-8"):
            errors.append(
                "config must expose p2p_mempool_min_fee_refuse (v1.3.177)"
            )
        if "p2p_mempool_require_wire_satoshi" not in p2p_py:
            errors.append("p2p_node must honor p2p_mempool_require_wire_satoshi")
        if "amount_satoshi_required" not in p2p_py or "fee_satoshi_required" not in p2p_py:
            errors.append(
                "p2p_node must refuse float-only wire (amount/fee_satoshi_required)"
            )
        if "value_satoshi_mismatch" not in p2p_py or "fee_satoshi_mismatch" not in p2p_py:
            errors.append("p2p_node must refuse fee/value satoshi mismatch")
        if "p2p_mempool_require_wire_satoshi" not in (
            ROOT / "runtime" / "config.py"
        ).read_text(encoding="utf-8"):
            errors.append("config must expose p2p_mempool_require_wire_satoshi")
        if "gas_missing" not in p2p_py:
            errors.append("p2p_node must refuse missing/zero gas (no invent 21000)")
        http_src = (ROOT / "api" / "http.py").read_text(encoding="utf-8", errors="replace")
        if "plan_transfer_fees_sat" not in http_src:
            errors.append("api/http admit must use plan_transfer_fees_sat")
        if 'gas or gas_limit required' not in http_src:
            errors.append("api/http must require explicit gas on send/deploy/call")
        if "gas_limit_required" not in (ROOT / "crypto" / "wallet.py").read_text(
            encoding="utf-8", errors="replace"
        ):
            errors.append("wallet.sign_transaction must refuse invent gas_limit=21000")
        if "gas_required" not in (ROOT / "core" / "blockchain.py").read_text(
            encoding="utf-8", errors="replace"
        ):
            errors.append("Transaction must refuse invent gas=21000")
        ident_py = (ROOT / "core" / "tx_identity.py").read_text(
            encoding="utf-8", errors="replace"
        )
        if "_require_positive_gas" not in ident_py:
            errors.append("tx_identity must refuse omitted gas (_require_positive_gas)")
        state_svc_src = (ROOT / "core" / "components" / "state_service.py").read_text(
            encoding="utf-8", errors="replace"
        )
        if "tx.gas or 21000" in state_svc_src:
            errors.append("state_service must not invent gas=21000")
        if "gas_required" not in state_svc_src:
            errors.append("state_service must raise gas_required when gas missing")
        bb_src = (ROOT / "execution" / "block_builder.py").read_text(
            encoding="utf-8", errors="replace"
        )
        if 'gas", 21000)' in bb_src:
            errors.append("block_builder must not invent gas_limit=21000")
        if 'tx.get("gas", 21000)' in (
            ROOT / "blockchain" / "tx_validator.py"
        ).read_text(encoding="utf-8", errors="replace"):
            errors.append("tx_validator must not invent gas=21000 on signature bind")
        db_py = (ROOT / "storage" / "database.py").read_text(
            encoding="utf-8", errors="replace"
        )
        if 'tx.get("gas", 21000)' in db_py or 'tx.get("gas_used", tx.get("gas", 21000))' in db_py:
            errors.append("SQLite tx persist must not invent gas=21000")
        if "_tx_gas_fields" not in db_py:
            errors.append("SQLite must expose _tx_gas_fields (no invent gas)")
        rocks_store_py = (ROOT / "storage" / "rocks_store.py").read_text(
            encoding="utf-8", errors="replace"
        )
        if 'tx.get("gas_used", tx.get("gas", 21000))' in rocks_store_py:
            errors.append("Rocks tx persist must not invent gas_used=21000")
        hash_py = (ROOT / "crypto" / "hashing.py").read_text(
            encoding="utf-8", errors="replace"
        )
        if 'tx.get("gas_limit", 21000)' in hash_py:
            errors.append("Hasher.hash_transaction must not invent gas_limit=21000")
        if 'gas: int = 0  # explicit gas required on add' not in (
            ROOT / "blockchain" / "mempool.py"
        ).read_text(encoding="utf-8", errors="replace"):
            errors.append("MempoolTransaction must default gas=0 (no invent 21000)")
        main_py = (ROOT / "main.py").read_text(encoding="utf-8", errors="replace")
        if "gas_required (no invent)" not in main_py:
            errors.append("main mining must skip txs with missing gas (no invent)")
        if "abs_p2p_native_mempool_min_fee_refuse" not in (
            ROOT / "observability" / "metrics.py"
        ).read_text(encoding="utf-8"):
            errors.append(
                "metrics must export abs_p2p_native_mempool_min_fee_refuse (v1.3.177)"
            )
        # v1.3.178 — GET_MEMPOOL tip-align serve gate
        if "get_mempool_tip_misaligned" not in p2p_py:
            errors.append(
                "p2p must refuse GET_MEMPOOL dump for far peer tip (v1.3.178)"
            )
        if "_get_mempool_tip_align_refuse_reason" not in p2p_py:
            errors.append(
                "p2p must expose _get_mempool_tip_align_refuse_reason (v1.3.178)"
            )
        if "p2p_mempool_serve_tip_align" not in (
            ROOT / "runtime" / "config.py"
        ).read_text(encoding="utf-8"):
            errors.append(
                "config must expose p2p_mempool_serve_tip_align (v1.3.178)"
            )
        if "abs_p2p_native_mempool_serve_tip_align" not in (
            ROOT / "observability" / "metrics.py"
        ).read_text(encoding="utf-8"):
            errors.append(
                "metrics must export abs_p2p_native_mempool_serve_tip_align (v1.3.178)"
            )
        # v1.3.179 — mempool max-gas refuse before validate
        if "gas_too_high" not in p2p_py or "p2p_mempool_max_gas_refuse" not in p2p_py:
            errors.append(
                "p2p must refuse gas>evm_gas_limit before validate_transaction (v1.3.179)"
            )
        if "native_mempool_max_gas_refuse" not in p2p_py:
            errors.append(
                "p2p must expose native_mempool_max_gas_refuse (v1.3.179)"
            )
        if "p2p_mempool_max_gas_refuse" not in (
            ROOT / "runtime" / "config.py"
        ).read_text(encoding="utf-8"):
            errors.append(
                "config must expose p2p_mempool_max_gas_refuse (v1.3.179)"
            )
        if "abs_p2p_native_mempool_max_gas_refuse" not in (
            ROOT / "observability" / "metrics.py"
        ).read_text(encoding="utf-8"):
            errors.append(
                "metrics must export abs_p2p_native_mempool_max_gas_refuse (v1.3.179)"
            )
        # v1.3.180 — GET_BLOCKS future-height refuse
        if "get_blocks_future_height" not in p2p_py:
            errors.append(
                "p2p must refuse GET_BLOCKS when from_height>local tip (v1.3.180)"
            )
        if "_get_blocks_future_refuse_reason" not in p2p_py:
            errors.append(
                "p2p must expose _get_blocks_future_refuse_reason (v1.3.180)"
            )
        if "p2p_get_blocks_future_refuse" not in (
            ROOT / "runtime" / "config.py"
        ).read_text(encoding="utf-8"):
            errors.append(
                "config must expose p2p_get_blocks_future_refuse (v1.3.180)"
            )
        if "abs_p2p_native_get_blocks_future_refuse" not in (
            ROOT / "observability" / "metrics.py"
        ).read_text(encoding="utf-8"):
            errors.append(
                "metrics must export abs_p2p_native_get_blocks_future_refuse (v1.3.180)"
            )
        # v1.3.181 — GET_BLOCK future-height refuse
        if "get_block_future_height" not in p2p_py:
            errors.append(
                "p2p must refuse GET_BLOCK when height>local tip (v1.3.181)"
            )
        if "_get_block_future_refuse_reason" not in p2p_py:
            errors.append(
                "p2p must expose _get_block_future_refuse_reason (v1.3.181)"
            )
        if "p2p_get_block_future_refuse" not in (
            ROOT / "runtime" / "config.py"
        ).read_text(encoding="utf-8"):
            errors.append(
                "config must expose p2p_get_block_future_refuse (v1.3.181)"
            )
        if "abs_p2p_native_get_block_future_refuse" not in (
            ROOT / "observability" / "metrics.py"
        ).read_text(encoding="utf-8"):
            errors.append(
                "metrics must export abs_p2p_native_get_block_future_refuse (v1.3.181)"
            )
        # v1.3.182 — GET_BLOCKS past-tip end clamp
        if "get_blocks_past_tip_clamp" not in p2p_py:
            errors.append(
                "p2p must clamp GET_BLOCKS end to local tip (v1.3.182)"
            )
        if "_get_blocks_past_tip_clamp_end" not in p2p_py:
            errors.append(
                "p2p must expose _get_blocks_past_tip_clamp_end (v1.3.182)"
            )
        if "p2p_get_blocks_past_tip_clamp" not in (
            ROOT / "runtime" / "config.py"
        ).read_text(encoding="utf-8"):
            errors.append(
                "config must expose p2p_get_blocks_past_tip_clamp (v1.3.182)"
            )
        if "abs_p2p_native_get_blocks_past_tip_clamp" not in (
            ROOT / "observability" / "metrics.py"
        ).read_text(encoding="utf-8"):
            errors.append(
                "metrics must export abs_p2p_native_get_blocks_past_tip_clamp (v1.3.182)"
            )
        # Exp→pin merge wave (non-LR): GET_BLOCKS offload, disconnect redial,
        # tip-safety tip anchor/rebind, solicit state_root lag. No soak implied.
        get_blocks_fn = p2p_py.split("async def _handle_get_blocks", 1)[-1].split(
            "def _get_blocks_future_refuse_reason", 1
        )[0]
        if "asyncio.to_thread(_load_range)" not in get_blocks_fn:
            errors.append(
                "_handle_get_blocks offloads via to_thread(_load_range) "
                "(Rocks range read must not block the asyncio loop)"
            )
        remove_peer_fn = p2p_py.split("def _remove_peer", 1)[-1].split(
            "def _host_looks_like_libp2p_peer_id", 1
        )[0]
        if (
            "Immediate bootstrap redial" not in remove_peer_fn
            or "_redial_known_addrs_after_disconnect" not in remove_peer_fn
            or "def _redial_known_addrs_after_disconnect" not in p2p_py
        ):
            errors.append(
                "_remove_peer immediate-redial: schedule connect to known addrs "
                "after unregister when under testnet_expected_peers"
            )
        shadow_src = (ROOT / "consensus" / "tip_safety" / "shadow.py").read_text(
            encoding="utf-8"
        )
        if "Canonical tip is get_height()" not in shadow_src:
            errors.append(
                "tip_state_from_chain anchors get_height (not stale get_last_block)"
            )
        if "tip height mismatch" not in shadow_src:
            errors.append(
                "tip_state_from_chain must refuse get_height/last_block mismatch"
            )
        if (
            "Bind to live tip before evaluate" not in shadow_src
            or "_tip_window_stale" not in shadow_src
        ):
            errors.append(
                "tip-safety observe rebinds stale window to live tip before evaluate"
            )
        solicit_gate_src = (ROOT / "sync" / "solicit.py").read_text(encoding="utf-8")
        if (
            "state_root_lag" not in solicit_gate_src
            or "state_root_lag_replies_total" not in solicit_gate_src
        ):
            errors.append(
                "solicit accepts lower-height state_root as lag "
                "(state_root_lag / state_root_lag_replies_total, no strike)"
            )
        # Exp→pin wave: outbound state_root lag + soak FullHarnessEvery + status cache.
        handlers_src = (
            ROOT / "network" / "p2p_dispatch" / "handlers.py"
        ).read_text(encoding="utf-8")
        if "state_root_outbound_lag_total" not in handlers_src:
            errors.append(
                "state_root handler must answer ahead requests with local tip lag"
            )
        http_py = (ROOT / "api" / "http.py").read_text(encoding="utf-8")
        if "_status_native_crypto_cached" not in http_py:
            errors.append("GET /status must cache native_crypto_status (soak HOL)")
        soak_mon = (ROOT / "scripts" / "soak_monitor.ps1").read_text(encoding="utf-8")
        if "$hwArgs.FullHarnessEvery = 6" not in soak_mon:
            errors.append(
                "48h soak_monitor must set FullHarnessEvery=6 (not AlwaysFullHarness)"
            )
        if "$hwArgs.Strict = $true" not in soak_mon:
            errors.append("soak_monitor must pass -Strict through to health_watch")
        hw_ps1 = (ROOT / "scripts" / "health_watch.ps1").read_text(encoding="utf-8")
        if "[switch]$Strict" not in hw_ps1:
            errors.append("health_watch.ps1 must expose -Strict")
        hw_core = (ROOT / "scripts" / "health_watch_core.ps1").read_text(encoding="utf-8")
        if "Invoke-ParallelNodeHealth" not in hw_core:
            errors.append("health_watch_core must provide Invoke-ParallelNodeHealth")
        if not (ROOT / "scripts" / "start_soak_prod_mesh_48h.ps1").is_file():
            errors.append("scripts/start_soak_prod_mesh_48h.ps1 missing")
        start48 = (ROOT / "scripts" / "start_soak_prod_mesh_48h.ps1").read_text(
            encoding="utf-8"
        )
        if "-FullHarness" not in start48:
            errors.append("48h start script must pass -FullHarness (not Strict)")
        if "-Strict" in start48:
            errors.append("48h start script must not pass -Strict (that is the 5h bar)")
        if not (ROOT / "scripts" / "start_soak_prod_mesh_48h_strict.ps1").is_file():
            errors.append(
                "scripts/start_soak_prod_mesh_48h_strict.ps1 missing (pin STRICT)"
            )
        start48s = (ROOT / "scripts" / "start_soak_prod_mesh_48h_strict.ps1").read_text(
            encoding="utf-8"
        )
        if "-Strict" not in start48s or "IntervalSec = 60" not in start48s:
            errors.append(
                "48h STRICT start must default IntervalSec=60 and pass -Strict"
            )
        if not (ROOT / "scripts" / "start_soak_prod_mesh_5h_strict.ps1").is_file():
            errors.append("scripts/start_soak_prod_mesh_5h_strict.ps1 missing")
        if not (ROOT / "scripts" / "start_soak_evm_mesh_48h_strict.ps1").is_file():
            errors.append("scripts/start_soak_evm_mesh_48h_strict.ps1 missing")
        else:
            evm_strict = (
                ROOT / "scripts" / "start_soak_evm_mesh_48h_strict.ps1"
            ).read_text(encoding="utf-8")
            if "start_soak_prod_mesh_48h_strict.ps1" not in evm_strict:
                errors.append(
                    "EVM STRICT must delegate to start_soak_prod_mesh_48h_strict.ps1"
                )
        rocks_ad = (ROOT / "storage" / "adapters" / "rocks_adapter.py").read_text(
            encoding="utf-8"
        )
        if 'money_abs(raw, field="burned")' not in rocks_ad:
            errors.append("rocks_adapter _block_burn_fields must use money_abs (no float burn)")
        if 'reason_code="persist_failed"' not in rocks_ad or "save_block returned False" not in rocks_ad:
            errors.append("rocks_adapter save_block must raise persist_failed on False")
        bridge_ad = (ROOT / "bridge" / "adapter.py").read_text(encoding="utf-8")
        if "bridge_result_not_boolean" not in bridge_ad:
            errors.append("normalize_bridge_http_result must refuse non-boolean success paint")
        bc_init = (ROOT / "core" / "blockchain.py").read_text(encoding="utf-8")
        if "bind_tip_encoding_config failed" not in bc_init:
            errors.append(
                "Blockchain.__init__ must log/raise bind_tip_encoding_config failures"
            )
        if "genesis_founder meta write failed" not in bc_init:
            errors.append(
                "artifact genesis_founder meta write must log/raise in production"
            )
        if "DAO_VOTE_BPS" not in (
            ROOT / "runtime" / "pool_locks.py"
        ).read_text(encoding="utf-8"):
            errors.append("pool_locks DAO must use integer BPS quorum (Wave O)")
        rpc_src = (ROOT / "api" / "rpc_service.py").read_text(encoding="utf-8")
        if 'gas_limit=getattr(cfg, "evm_gas_limit", None)' not in rpc_src:
            errors.append("RPC eth_getBlock* must pass cfg.evm_gas_limit into format_block")
        # Exp→pin polish: uncle-by-hash hash validate + audit live_automated +
        # bridge money_abs / prod raise honesty + consensus _native_fb logs.
        uncle_hash_idx = rpc_src.find("eth_getUncleByBlockHashAndIndex")
        if uncle_hash_idx < 0 or "validate_block_hash_param" not in rpc_src[uncle_hash_idx:]:
            errors.append(
                "RPC eth_getUncleByBlockHash* must validate_block_hash_param"
            )
        uncle_count_idx = rpc_src.find("eth_getUncleCountByBlockHash")
        if uncle_count_idx < 0 or "validate_block_hash_param" not in rpc_src[uncle_count_idx:]:
            errors.append(
                "RPC eth_getUncleCountByBlockHash must validate_block_hash_param"
            )
        audit_py = (ROOT / "runtime" / "external_audit.py").read_text(encoding="utf-8")
        if "live_automated: bool = True" not in audit_py:
            errors.append("external_audit.evaluate must support live_automated")
        if '"live_automated": bool(live_automated)' not in audit_py:
            errors.append("external_audit summary must expose live_automated")
        if not (ROOT / "tests" / "unit" / "test_external_audit_live_automated.py").is_file():
            errors.append("tests/unit/test_external_audit_live_automated.py missing")
        relayer_mod = (ROOT / "bridge" / "relayer.py").read_text(encoding="utf-8")
        if 'money_abs(item.get("amount", 0), field="amount")' not in relayer_mod:
            errors.append("bridge relayer must parse amount via money_abs (no float)")
        abs_bridge_py = (ROOT / "bridge" / "abs_bridge.py").read_text(encoding="utf-8")
        if (
            'self._is_prod and bool(getattr(config, "bridge_enabled", False))'
            not in abs_bridge_py
        ):
            errors.append(
                "abs_bridge missing Rust bin must raise only when prod+bridge_enabled"
            )
        casper_py = (ROOT / "consensus" / "finality_casper.py").read_text(
            encoding="utf-8"
        )
        if "native %s failed; Python path: %s" not in casper_py:
            errors.append("Casper FFG must log native kernel fallbacks")
        if '_native_fb("ffg_accumulate_vote"' not in casper_py:
            errors.append("Casper FFG must log native ffg_accumulate_vote fallback")
        ghost_fb = (ROOT / "consensus" / "ghost.py").read_text(encoding="utf-8")
        if '_native_fb("ghost_select_head"' not in ghost_fb:
            errors.append("GHOST must log native ghost_select_head fallback")
        lmd_fb = (ROOT / "consensus" / "lmd.py").read_text(encoding="utf-8")
        if '_native_fb("lmd_compute_weights"' not in lmd_fb:
            errors.append("LMD must log native lmd_compute_weights fallback")
        beacon_fb = (ROOT / "consensus" / "finality_beacon.py").read_text(
            encoding="utf-8"
        )
        if '_native_fb("ffg_evaluate_epoch"' not in beacon_fb:
            errors.append("Beacon FFG must log native ffg_evaluate_epoch fallback")
        # v1.3.183 — mempool max-calldata refuse before validate
        if "calldata_too_large" not in p2p_py:
            errors.append(
                "p2p must refuse oversized calldata before validate (v1.3.183)"
            )
        if "_wire_calldata_byte_len" not in p2p_py:
            errors.append(
                "p2p must expose _wire_calldata_byte_len (v1.3.183)"
            )
        if "p2p_mempool_max_calldata_refuse" not in (
            ROOT / "runtime" / "config.py"
        ).read_text(encoding="utf-8"):
            errors.append(
                "config must expose p2p_mempool_max_calldata_refuse (v1.3.183)"
            )
        if "abs_p2p_native_mempool_max_calldata_refuse" not in (
            ROOT / "observability" / "metrics.py"
        ).read_text(encoding="utf-8"):
            errors.append(
                "metrics must export abs_p2p_native_mempool_max_calldata_refuse (v1.3.183)"
            )
        # v1.3.184 — mempool negative-value refuse before validate
        if "value_negative" not in p2p_py:
            errors.append(
                "p2p must refuse value<0 before validate (v1.3.184)"
            )
        if "p2p_mempool_negative_value_refuse" not in p2p_py:
            errors.append(
                "p2p must gate on p2p_mempool_negative_value_refuse (v1.3.184)"
            )
        if "p2p_mempool_negative_value_refuse" not in (
            ROOT / "runtime" / "config.py"
        ).read_text(encoding="utf-8"):
            errors.append(
                "config must expose p2p_mempool_negative_value_refuse (v1.3.184)"
            )
        if "abs_p2p_native_mempool_negative_value_refuse" not in (
            ROOT / "observability" / "metrics.py"
        ).read_text(encoding="utf-8"):
            errors.append(
                "metrics must export abs_p2p_native_mempool_negative_value_refuse (v1.3.184)"
            )
        # v1.3.185 — mempool negative-nonce refuse before validate
        if "nonce_negative" not in p2p_py:
            errors.append(
                "p2p must refuse nonce<0 before validate (v1.3.185)"
            )
        if "p2p_mempool_negative_nonce_refuse" not in p2p_py:
            errors.append(
                "p2p must gate on p2p_mempool_negative_nonce_refuse (v1.3.185)"
            )
        if "p2p_mempool_negative_nonce_refuse" not in (
            ROOT / "runtime" / "config.py"
        ).read_text(encoding="utf-8"):
            errors.append(
                "config must expose p2p_mempool_negative_nonce_refuse (v1.3.185)"
            )
        if "abs_p2p_native_mempool_negative_nonce_refuse" not in (
            ROOT / "observability" / "metrics.py"
        ).read_text(encoding="utf-8"):
            errors.append(
                "metrics must export abs_p2p_native_mempool_negative_nonce_refuse (v1.3.185)"
            )
        # v1.3.186 — mempool negative-fee refuse before validate
        if "fee_negative" not in p2p_py:
            errors.append(
                "p2p must refuse fee<0 before validate (v1.3.186)"
            )
        if "p2p_mempool_negative_fee_refuse" not in p2p_py:
            errors.append(
                "p2p must gate on p2p_mempool_negative_fee_refuse (v1.3.186)"
            )
        if "p2p_mempool_negative_fee_refuse" not in (
            ROOT / "runtime" / "config.py"
        ).read_text(encoding="utf-8"):
            errors.append(
                "config must expose p2p_mempool_negative_fee_refuse (v1.3.186)"
            )
        if "abs_p2p_native_mempool_negative_fee_refuse" not in (
            ROOT / "observability" / "metrics.py"
        ).read_text(encoding="utf-8"):
            errors.append(
                "metrics must export abs_p2p_native_mempool_negative_fee_refuse (v1.3.186)"
            )
        # v1.3.187 — mempool negative-gas refuse before validate
        if "gas_negative" not in p2p_py:
            errors.append(
                "p2p must refuse gas<0 before validate (v1.3.187)"
            )
        if "p2p_mempool_negative_gas_refuse" not in p2p_py:
            errors.append(
                "p2p must gate on p2p_mempool_negative_gas_refuse (v1.3.187)"
            )
        if "p2p_mempool_negative_gas_refuse" not in (
            ROOT / "runtime" / "config.py"
        ).read_text(encoding="utf-8"):
            errors.append(
                "config must expose p2p_mempool_negative_gas_refuse (v1.3.187)"
            )
        if "abs_p2p_native_mempool_negative_gas_refuse" not in (
            ROOT / "observability" / "metrics.py"
        ).read_text(encoding="utf-8"):
            errors.append(
                "metrics must export abs_p2p_native_mempool_negative_gas_refuse (v1.3.187)"
            )
        # v1.3.188 — mempool empty-from refuse before validate
        if "from_empty" not in p2p_py:
            errors.append(
                "p2p must refuse empty from before validate (v1.3.188)"
            )
        if "p2p_mempool_empty_from_refuse" not in p2p_py:
            errors.append(
                "p2p must gate on p2p_mempool_empty_from_refuse (v1.3.188)"
            )
        if "p2p_mempool_empty_from_refuse" not in (
            ROOT / "runtime" / "config.py"
        ).read_text(encoding="utf-8"):
            errors.append(
                "config must expose p2p_mempool_empty_from_refuse (v1.3.188)"
            )
        if "abs_p2p_native_mempool_empty_from_refuse" not in (
            ROOT / "observability" / "metrics.py"
        ).read_text(encoding="utf-8"):
            errors.append(
                "metrics must export abs_p2p_native_mempool_empty_from_refuse (v1.3.188)"
            )
        # v1.3.189 — mempool empty-signature refuse before validate
        if "signature_empty" not in p2p_py:
            errors.append(
                "p2p must refuse empty signature before validate (v1.3.189)"
            )
        if "p2p_mempool_empty_sig_refuse" not in p2p_py:
            errors.append(
                "p2p must gate on p2p_mempool_empty_sig_refuse (v1.3.189)"
            )
        if "p2p_mempool_empty_sig_refuse" not in (
            ROOT / "runtime" / "config.py"
        ).read_text(encoding="utf-8"):
            errors.append(
                "config must expose p2p_mempool_empty_sig_refuse (v1.3.189)"
            )
        if "abs_p2p_native_mempool_empty_sig_refuse" not in (
            ROOT / "observability" / "metrics.py"
        ).read_text(encoding="utf-8"):
            errors.append(
                "metrics must export abs_p2p_native_mempool_empty_sig_refuse (v1.3.189)"
            )
        # v1.3.190 — mempool empty-pubkey refuse before validate
        if "pubkey_empty" not in p2p_py:
            errors.append(
                "p2p must refuse empty public_key before validate (v1.3.190)"
            )
        if "p2p_mempool_empty_pubkey_refuse" not in p2p_py:
            errors.append(
                "p2p must gate on p2p_mempool_empty_pubkey_refuse (v1.3.190)"
            )
        if "p2p_mempool_empty_pubkey_refuse" not in (
            ROOT / "runtime" / "config.py"
        ).read_text(encoding="utf-8"):
            errors.append(
                "config must expose p2p_mempool_empty_pubkey_refuse (v1.3.190)"
            )
        if "abs_p2p_native_mempool_empty_pubkey_refuse" not in (
            ROOT / "observability" / "metrics.py"
        ).read_text(encoding="utf-8"):
            errors.append(
                "metrics must export abs_p2p_native_mempool_empty_pubkey_refuse (v1.3.190)"
            )
        # v1.3.191 — mempool max-signature refuse before validate
        if "signature_too_large" not in p2p_py:
            errors.append(
                "p2p must refuse oversized signature before validate (v1.3.191)"
            )
        if "p2p_mempool_max_sig_refuse" not in p2p_py:
            errors.append(
                "p2p must gate on p2p_mempool_max_sig_refuse (v1.3.191)"
            )
        if "p2p_mempool_max_sig_refuse" not in (
            ROOT / "runtime" / "config.py"
        ).read_text(encoding="utf-8"):
            errors.append(
                "config must expose p2p_mempool_max_sig_refuse (v1.3.191)"
            )
        if "abs_p2p_native_mempool_max_sig_refuse" not in (
            ROOT / "observability" / "metrics.py"
        ).read_text(encoding="utf-8"):
            errors.append(
                "metrics must export abs_p2p_native_mempool_max_sig_refuse (v1.3.191)"
            )
        # v1.3.192 — mempool max-pubkey refuse before validate
        if "pubkey_too_large" not in p2p_py:
            errors.append(
                "p2p must refuse oversized public_key before validate (v1.3.192)"
            )
        if "p2p_mempool_max_pubkey_refuse" not in p2p_py:
            errors.append(
                "p2p must gate on p2p_mempool_max_pubkey_refuse (v1.3.192)"
            )
        if "p2p_mempool_max_pubkey_refuse" not in (
            ROOT / "runtime" / "config.py"
        ).read_text(encoding="utf-8"):
            errors.append(
                "config must expose p2p_mempool_max_pubkey_refuse (v1.3.192)"
            )
        if "abs_p2p_native_mempool_max_pubkey_refuse" not in (
            ROOT / "observability" / "metrics.py"
        ).read_text(encoding="utf-8"):
            errors.append(
                "metrics must export abs_p2p_native_mempool_max_pubkey_refuse (v1.3.192)"
            )
        # v1.3.193 — mempool non-finite value refuse before validate
        if "value_non_finite" not in p2p_py:
            errors.append(
                "p2p must refuse NaN/Inf value before validate (v1.3.193)"
            )
        if "p2p_mempool_nonfinite_value_refuse" not in p2p_py:
            errors.append(
                "p2p must gate on p2p_mempool_nonfinite_value_refuse (v1.3.193)"
            )
        if "p2p_mempool_nonfinite_value_refuse" not in (
            ROOT / "runtime" / "config.py"
        ).read_text(encoding="utf-8"):
            errors.append(
                "config must expose p2p_mempool_nonfinite_value_refuse (v1.3.193)"
            )
        if "abs_p2p_native_mempool_nonfinite_value_refuse" not in (
            ROOT / "observability" / "metrics.py"
        ).read_text(encoding="utf-8"):
            errors.append(
                "metrics must export abs_p2p_native_mempool_nonfinite_value_refuse (v1.3.193)"
            )
        # v1.3.194 — mempool non-finite fee refuse before validate
        if "fee_non_finite" not in p2p_py:
            errors.append(
                "p2p must refuse NaN/Inf fee before validate (v1.3.194)"
            )
        if "p2p_mempool_nonfinite_fee_refuse" not in p2p_py:
            errors.append(
                "p2p must gate on p2p_mempool_nonfinite_fee_refuse (v1.3.194)"
            )
        if "p2p_mempool_nonfinite_fee_refuse" not in (
            ROOT / "runtime" / "config.py"
        ).read_text(encoding="utf-8"):
            errors.append(
                "config must expose p2p_mempool_nonfinite_fee_refuse (v1.3.194)"
            )
        if "abs_p2p_native_mempool_nonfinite_fee_refuse" not in (
            ROOT / "observability" / "metrics.py"
        ).read_text(encoding="utf-8"):
            errors.append(
                "metrics must export abs_p2p_native_mempool_nonfinite_fee_refuse (v1.3.194)"
            )
        # v1.3.195 — mempool empty-to refuse before validate
        if "to_empty" not in p2p_py:
            errors.append(
                "p2p must refuse empty to before validate (v1.3.195)"
            )
        if "p2p_mempool_empty_to_refuse" not in p2p_py:
            errors.append(
                "p2p must gate on p2p_mempool_empty_to_refuse (v1.3.195)"
            )
        if "p2p_mempool_empty_to_refuse" not in (
            ROOT / "runtime" / "config.py"
        ).read_text(encoding="utf-8"):
            errors.append(
                "config must expose p2p_mempool_empty_to_refuse (v1.3.195)"
            )
        if "abs_p2p_native_mempool_empty_to_refuse" not in (
            ROOT / "observability" / "metrics.py"
        ).read_text(encoding="utf-8"):
            errors.append(
                "metrics must export abs_p2p_native_mempool_empty_to_refuse (v1.3.195)"
            )
        # v1.3.196 — mempool empty-hash refuse before validate
        if "hash_empty" not in p2p_py:
            errors.append(
                "p2p must refuse empty hash before validate (v1.3.196)"
            )
        if "p2p_mempool_empty_hash_refuse" not in p2p_py:
            errors.append(
                "p2p must gate on p2p_mempool_empty_hash_refuse (v1.3.196)"
            )
        if "p2p_mempool_empty_hash_refuse" not in (
            ROOT / "runtime" / "config.py"
        ).read_text(encoding="utf-8"):
            errors.append(
                "config must expose p2p_mempool_empty_hash_refuse (v1.3.196)"
            )
        if "abs_p2p_native_mempool_empty_hash_refuse" not in (
            ROOT / "observability" / "metrics.py"
        ).read_text(encoding="utf-8"):
            errors.append(
                "metrics must export abs_p2p_native_mempool_empty_hash_refuse (v1.3.196)"
            )
        # v1.3.197 — mempool max-hash refuse before validate
        if "hash_too_large" not in p2p_py:
            errors.append(
                "p2p must refuse oversized hash before validate (v1.3.197)"
            )
        if "p2p_mempool_max_hash_refuse" not in p2p_py:
            errors.append(
                "p2p must gate on p2p_mempool_max_hash_refuse (v1.3.197)"
            )
        if "p2p_mempool_max_hash_refuse" not in (
            ROOT / "runtime" / "config.py"
        ).read_text(encoding="utf-8"):
            errors.append(
                "config must expose p2p_mempool_max_hash_refuse (v1.3.197)"
            )
        if "abs_p2p_native_mempool_max_hash_refuse" not in (
            ROOT / "observability" / "metrics.py"
        ).read_text(encoding="utf-8"):
            errors.append(
                "metrics must export abs_p2p_native_mempool_max_hash_refuse (v1.3.197)"
            )
        # v1.3.198 — mempool max-from refuse before validate
        if "from_too_large" not in p2p_py:
            errors.append(
                "p2p must refuse oversized from before validate (v1.3.198)"
            )
        if "p2p_mempool_max_from_refuse" not in p2p_py:
            errors.append(
                "p2p must gate on p2p_mempool_max_from_refuse (v1.3.198)"
            )
        if "p2p_mempool_max_from_refuse" not in (
            ROOT / "runtime" / "config.py"
        ).read_text(encoding="utf-8"):
            errors.append(
                "config must expose p2p_mempool_max_from_refuse (v1.3.198)"
            )
        if "abs_p2p_native_mempool_max_from_refuse" not in (
            ROOT / "observability" / "metrics.py"
        ).read_text(encoding="utf-8"):
            errors.append(
                "metrics must export abs_p2p_native_mempool_max_from_refuse (v1.3.198)"
            )
        # v1.3.199 — mempool max-to refuse before validate
        if "to_too_large" not in p2p_py:
            errors.append(
                "p2p must refuse oversized to before validate (v1.3.199)"
            )
        if "p2p_mempool_max_to_refuse" not in p2p_py:
            errors.append(
                "p2p must gate on p2p_mempool_max_to_refuse (v1.3.199)"
            )
        if "p2p_mempool_max_to_refuse" not in (
            ROOT / "runtime" / "config.py"
        ).read_text(encoding="utf-8"):
            errors.append(
                "config must expose p2p_mempool_max_to_refuse (v1.3.199)"
            )
        if "abs_p2p_native_mempool_max_to_refuse" not in (
            ROOT / "observability" / "metrics.py"
        ).read_text(encoding="utf-8"):
            errors.append(
                "metrics must export abs_p2p_native_mempool_max_to_refuse (v1.3.199)"
            )
        # v1.3.200 — mempool max-nonce refuse before validate
        if "nonce_too_high" not in p2p_py:
            errors.append(
                "p2p must refuse oversized nonce before validate (v1.3.200)"
            )
        if "p2p_mempool_max_nonce_refuse" not in p2p_py:
            errors.append(
                "p2p must gate on p2p_mempool_max_nonce_refuse (v1.3.200)"
            )
        if "p2p_mempool_max_nonce_refuse" not in (
            ROOT / "runtime" / "config.py"
        ).read_text(encoding="utf-8"):
            errors.append(
                "config must expose p2p_mempool_max_nonce_refuse (v1.3.200)"
            )
        if "abs_p2p_native_mempool_max_nonce_refuse" not in (
            ROOT / "observability" / "metrics.py"
        ).read_text(encoding="utf-8"):
            errors.append(
                "metrics must export abs_p2p_native_mempool_max_nonce_refuse (v1.3.200)"
            )
        # v1.3.201 — mempool max-fee refuse before validate
        if "fee_too_high" not in p2p_py:
            errors.append(
                "p2p must refuse oversized fee before validate (v1.3.201)"
            )
        if "p2p_mempool_max_fee_refuse" not in p2p_py:
            errors.append(
                "p2p must gate on p2p_mempool_max_fee_refuse (v1.3.201)"
            )
        if "p2p_mempool_max_fee_refuse" not in (
            ROOT / "runtime" / "config.py"
        ).read_text(encoding="utf-8"):
            errors.append(
                "config must expose p2p_mempool_max_fee_refuse (v1.3.201)"
            )
        if "abs_p2p_native_mempool_max_fee_refuse" not in (
            ROOT / "observability" / "metrics.py"
        ).read_text(encoding="utf-8"):
            errors.append(
                "metrics must export abs_p2p_native_mempool_max_fee_refuse (v1.3.201)"
            )
        # v1.3.202 — mempool max-value refuse before validate
        if "value_too_high" not in p2p_py:
            errors.append(
                "p2p must refuse oversized value before validate (v1.3.202)"
            )
        if "p2p_mempool_max_value_refuse" not in p2p_py:
            errors.append(
                "p2p must gate on p2p_mempool_max_value_refuse (v1.3.202)"
            )
        if "p2p_mempool_max_value_refuse" not in (
            ROOT / "runtime" / "config.py"
        ).read_text(encoding="utf-8"):
            errors.append(
                "config must expose p2p_mempool_max_value_refuse (v1.3.202)"
            )
        if "abs_p2p_native_mempool_max_value_refuse" not in (
            ROOT / "observability" / "metrics.py"
        ).read_text(encoding="utf-8"):
            errors.append(
                "metrics must export abs_p2p_native_mempool_max_value_refuse (v1.3.202)"
            )
        # v1.3.203 — mempool unparseable-gas refuse before validate
        if "gas_unparseable" not in p2p_py:
            errors.append(
                "p2p must refuse unparseable gas before validate (v1.3.203)"
            )
        if "p2p_mempool_unparseable_gas_refuse" not in p2p_py:
            errors.append(
                "p2p must gate on p2p_mempool_unparseable_gas_refuse (v1.3.203)"
            )
        if "p2p_mempool_unparseable_gas_refuse" not in (
            ROOT / "runtime" / "config.py"
        ).read_text(encoding="utf-8"):
            errors.append(
                "config must expose p2p_mempool_unparseable_gas_refuse (v1.3.203)"
            )
        if "abs_p2p_native_mempool_unparseable_gas_refuse" not in (
            ROOT / "observability" / "metrics.py"
        ).read_text(encoding="utf-8"):
            errors.append(
                "metrics must export abs_p2p_native_mempool_unparseable_gas_refuse (v1.3.203)"
            )
        # v1.3.204 — mempool unparseable-value refuse before validate
        if "value_unparseable" not in p2p_py:
            errors.append(
                "p2p must refuse unparseable value before validate (v1.3.204)"
            )
        if "p2p_mempool_unparseable_value_refuse" not in p2p_py:
            errors.append(
                "p2p must gate on p2p_mempool_unparseable_value_refuse (v1.3.204)"
            )
        if "p2p_mempool_unparseable_value_refuse" not in (
            ROOT / "runtime" / "config.py"
        ).read_text(encoding="utf-8"):
            errors.append(
                "config must expose p2p_mempool_unparseable_value_refuse (v1.3.204)"
            )
        if "abs_p2p_native_mempool_unparseable_value_refuse" not in (
            ROOT / "observability" / "metrics.py"
        ).read_text(encoding="utf-8"):
            errors.append(
                "metrics must export abs_p2p_native_mempool_unparseable_value_refuse (v1.3.204)"
            )
        # v1.3.205 — mempool unparseable-nonce refuse before validate
        if "nonce_unparseable" not in p2p_py:
            errors.append(
                "p2p must refuse unparseable nonce before validate (v1.3.205)"
            )
        if "p2p_mempool_unparseable_nonce_refuse" not in p2p_py:
            errors.append(
                "p2p must gate on p2p_mempool_unparseable_nonce_refuse (v1.3.205)"
            )
        if "p2p_mempool_unparseable_nonce_refuse" not in (
            ROOT / "runtime" / "config.py"
        ).read_text(encoding="utf-8"):
            errors.append(
                "config must expose p2p_mempool_unparseable_nonce_refuse (v1.3.205)"
            )
        if "abs_p2p_native_mempool_unparseable_nonce_refuse" not in (
            ROOT / "observability" / "metrics.py"
        ).read_text(encoding="utf-8"):
            errors.append(
                "metrics must export abs_p2p_native_mempool_unparseable_nonce_refuse (v1.3.205)"
            )
    except Exception as exc:
        errors.append(f"fail-loud v1.3.28..205 honesty inspect failed: {exc}")
    try:
        metrics_py = (ROOT / "observability" / "metrics.py").read_text(encoding="utf-8")
        if "abs_sync_wire_probe_probed" not in metrics_py:
            errors.append("metrics.py must export abs_sync_wire_probe_probed")
        if "-1=never probed" not in metrics_py and "never probed" not in metrics_py.lower():
            errors.append("metrics.py must document abs_sync_wire_probe_ok=-1 as never-probed")
        if "return -1" not in metrics_py:
            errors.append("metrics.py must emit abs_sync_wire_probe_ok=-1 when never probed")
        alerts = (ROOT / "deploy" / "prometheus" / "alerts.yml").read_text(encoding="utf-8")
        if "AbsoluteSyncWireProbeNeverProbed" not in alerts:
            errors.append("alerts.yml missing AbsoluteSyncWireProbeNeverProbed")
        if "AbsoluteProdSqliteEngine" not in alerts:
            errors.append("alerts.yml missing AbsoluteProdSqliteEngine")
    except Exception as exc:
        errors.append(f"fail-loud metrics/alerts inspect failed: {exc}")
    try:
        from core.blockchain import Blockchain

        gen_src = inspect.getsource(Blockchain._ensure_genesis)
        if "genesis meta write failed" not in gen_src:
            errors.append("Blockchain._ensure_genesis must log genesis meta failures")
        if "except Exception:\n                pass" in gen_src and "set_meta" in gen_src:
            # still allow other passes elsewhere in function; only fail if set_meta still bare-pass
            if "except Exception:\n                pass\n            try:\n                self.db.set_meta" in gen_src:
                errors.append("Blockchain._ensure_genesis still silent-passes tokenomics meta")
        add_src = inspect.getsource(Blockchain.add_block)
        if "record_state_root_mismatch failed" not in add_src:
            errors.append("Blockchain.add_block must log mismatch audit failures")
        tx_from = inspect.getsource(
            __import__("core.blockchain", fromlist=["Transaction"]).Transaction.from_dict
        )
        if "parse_rpc_value_abs" not in tx_from:
            errors.append("Transaction.from_dict must parse value via parse_rpc_value_abs")
        if "value=float(" in tx_from:
            errors.append("Transaction.from_dict must not float() value")
    except Exception as exc:
        errors.append(f"fail-loud blockchain inspect failed: {exc}")
    try:
        main_py = (ROOT / "main.py").read_text(encoding="utf-8")
        if "self.db.set_balance(addr, float(amount))" in main_py:
            errors.append("Node genesis alloc must not float() balances")
        if "self.db.set_balance(addr, int(amount))" not in main_py:
            errors.append("Node genesis alloc must mint integer ABS amounts")
    except Exception as exc:
        errors.append(f"fail-loud main.py inspect failed: {exc}")
    try:
        bc_py = (ROOT / "core" / "blockchain.py").read_text(
            encoding="utf-8", errors="replace"
        )
        if "amount_abs = int(amount)" not in bc_py:
            errors.append("Blockchain._ensure_genesis must mint integer ABS amounts")
        if "set_balance(addr, float(" in bc_py:
            errors.append("Blockchain._ensure_genesis must not float() genesis balances")
        db_py_bal = (ROOT / "storage" / "database.py").read_text(
            encoding="utf-8", errors="replace"
        )
        if "account_balance_abs" not in db_py_bal:
            errors.append("Database.get_balance must display via account_balance_abs")
        if 'float(row["balance"])' in db_py_bal:
            errors.append("Database.get_balance must not return raw float(row['balance'])")
        if "account_satoshi(out)" not in db_py_bal:
            errors.append("Database.get_account must derive balance from satoshi authority")
        if "bool is not an amount" not in db_py_bal:
            errors.append("SQLite Database.set_balance/save_account must refuse bool amounts")
        if "amount_satoshi" not in (
            ROOT / "bridge" / "ports.py"
        ).read_text(encoding="utf-8", errors="replace"):
            errors.append("InboundEnvelope must carry amount_satoshi")
        if "get_balance_satoshi" not in (
            ROOT / "api" / "query_facade.py"
        ).read_text(encoding="utf-8", errors="replace"):
            errors.append("QueryFacade must expose get_balance_satoshi (Phase C1)")
        p2p_py_stake = (ROOT / "network" / "p2p_node.py").read_text(
            encoding="utf-8", errors="replace"
        )
        if "stake_satoshi_required" not in p2p_py_stake:
            errors.append("p2p validator_register must require stake_satoshi")
        if "fee_gas_price_unset" not in p2p_py_stake:
            errors.append("P2P must refuse unset gas_price invent (Wave O)")
        adapter_py = (ROOT / "consensus" / "adapter.py").read_text(
            encoding="utf-8", errors="replace"
        )
        if 'field="stake"' not in adapter_py:
            errors.append("ConsensusAdapter stake resolve must use field=stake")
        if "total_active_stake failed" not in adapter_py:
            errors.append("ConsensusAdapter.get_total_stake must log registry failures")
        if "def get_total_stake(self) -> int" not in adapter_py:
            errors.append("ConsensusAdapter.get_total_stake must return int satoshi")
        ss_py = (ROOT / "core" / "components" / "state_service.py").read_text(
            encoding="utf-8", errors="replace"
        )
        if "satoshi_store_required_credit" not in ss_py:
            errors.append("StateService._credit_sat must refuse float fallback")
    except Exception as exc:
        errors.append(f"fail-loud money-authority inspect failed: {exc}")
    try:
        http_py = (ROOT / "api" / "http.py").read_text(encoding="utf-8")
        if "parse_rpc_value_abs" not in http_py:
            errors.append("JSON-RPC/REST money must use parse_rpc_value_abs (no IEEE wei divide)")
        if "wei / 10**18" in http_py:
            errors.append("HTTP _parse_tx_value must not IEEE-divide wei by 10**18")
        if "def _http_abs" not in http_py:
            errors.append("HTTP bridge/REST money must use _http_abs (satoshi-quantized ABS)")
        if "peer_probe_error" not in http_py:
            errors.append("GET /chain/state-root/status must expose peer_probe_error")
        if "peer_probe_error" not in http_py or "state consistency harness peer probe failed" not in http_py:
            errors.append("state consistency harness must expose/log peer_probe_error")
        if "prices_error" not in http_py:
            errors.append("/oracles/all must expose prices_error on failure")
        if "repair_error" not in http_py:
            errors.append("POST /chain/consistency/repair must expose repair_error")
        if "Never greenwash consistency from harness alone" not in http_py:
            errors.append("POST /chain/consistency/repair must require sync_state (not harness alone)")
        if "Do not claim fully synced while tip state is inconsistent" not in http_py:
            errors.append("eth_syncing must stay syncing when peers + inconsistent state")
        if "never wire-probed" not in http_py:
            errors.append(
                "eth_syncing must stay syncing when peers + wire probe never ran"
            )
        if 'db_engine == "rocksdb"' not in http_py:
            errors.append("/metrics must not apply Rocks config_fallback on non-rocks engines")
        if "peer_probe_ok" not in http_py:
            errors.append("state consistency harness must include peer_probe_ok check")
        if "state_root_encoding_honest" not in http_py:
            errors.append("state consistency harness must include state_root_encoding_honest check")
        if "/chain/state-root/encoding" not in http_py:
            errors.append("GET /chain/state-root/encoding missing")
        if "Invalid block number:" not in http_py:
            errors.append("block URL handlers must fail-loud on invalid block number")
        if "module_probes" not in http_py:
            errors.append("GET /features must expose module_probes for wasm/plasma")
        feat_init = (ROOT / "features" / "__init__.py").read_text(encoding="utf-8")
        for name in ("lightning", "zk", "ai_agents", "mev", "pq"):
            if f'"{name}"' not in feat_init:
                errors.append(f"OPTIONAL_MODULE_PROBES must include {name}")
    except Exception as exc:
        errors.append(f"fail-loud http inspect failed: {exc}")
    # STRICT mesh P2P: late state_root stash, wire-probe gate, coalesced gather.
    # Source needles only (mirror Exp); mesh probe / soak are separate evidence.
    try:
        p2p_py = (ROOT / "network" / "p2p_node.py").read_text(encoding="utf-8")
        if "_stash_late_state_root" not in p2p_py:
            errors.append("P2PNode must stash late state_root replies after solicit timeout")
        if '== "late_state_root"' not in p2p_py:
            errors.append("timed-out state_root waiter must stash late_state_root payloads")
        if "_consume_late_state_root" not in p2p_py:
            errors.append("state_root retry must consume the late stash before a second RTT")
        if "Late stash even when retry=False" not in p2p_py:
            errors.append("state_root one-RTT flight must still consume the late stash")
        if "await asyncio.sleep(0.4)" not in p2p_py:
            errors.append("empty state_root gather must drain late stash inside HTTP 8s budget")
        if "_wait_wire_probe_gate" not in p2p_py:
            errors.append("coalesced state_root flight must wait apply-idle / post-forge hold")
        if "_apply_completed_wire_probe" not in p2p_py:
            errors.append("completed state_root flight must feed ConsistencyService after waiter timeout")
        if "coalesced wire probe task failed" not in p2p_py:
            errors.append("completed wire probe must log task failures")
        if "_coalesced_peer_state_roots" not in p2p_py:
            errors.append("P2PNode must coalesce concurrent state_root probes")
        if "inflight continues" not in p2p_py:
            errors.append("state_root sync waiter timeout must not cancel inflight probe")
        if "per_peer_timeout=6.5" not in p2p_py:
            errors.append("coalesced state_root flight must fit inside HTTP 8s STRICT budget")
        if "Coalesced state_root flight is one RTT" not in p2p_py:
            errors.append("coalesced state_root flight must not retry (HTTP 5s quick budget)")
        if "Isolated node: return immediately" not in p2p_py:
            errors.append("coalesced state_root probe must not join a stale flight on 0 peers")
        if "_native_write_bound" not in p2p_py:
            errors.append("native P2P writes must set SO_SNDTIMEO so wait_for cannot leak the IO lock")
        if "_global_catch_up_lock" not in p2p_py:
            errors.append("P2P must serialize PathA across peers")
        if "tip_safety defer skip-ahead" not in p2p_py:
            errors.append(
                "P2PNode must defer tip-safety skip-ahead while apply_queue is busy"
            )
        # Own-forge echo: tip-safety must not refuse the miner's NEW_BLOCK echo
        # against a stale AncestryWindow (tip_unknown_parent). Bounded to
        # last_forge / last_forge+1 — never the whole history.
        if "note_local_forge" not in p2p_py:
            errors.append("P2PNode must expose note_local_forge (post-forge hold + height)")
        if "tip_safety defer own-forge echo" not in p2p_py:
            errors.append("P2PNode must defer tip-safety for last locally forged height")
        if "cand_h in (last_forge, last_forge + 1)" not in p2p_py:
            errors.append(
                "tip-safety own-forge defer must be bounded to last_forge/last_forge+1"
            )
        if 'getattr(shadow, "note_local_forge", None)' not in p2p_py:
            errors.append("P2PNode.note_local_forge must propagate height to tip_safety shadow")
        shadow_py = (ROOT / "consensus" / "tip_safety" / "shadow.py").read_text(
            encoding="utf-8"
        )
        if "def note_local_forge" not in shadow_py or "last_local_forge_height" not in shadow_py:
            errors.append(
                "TipSafetyShadowObserver must record last_local_forge_height via note_local_forge"
            )
        tip_evidence_py = (
            ROOT / "network" / "p2p_dispatch" / "tip_evidence.py"
        ).read_text(encoding="utf-8")
        if "own_forge_echo" not in tip_evidence_py:
            errors.append("dispatcher tip-evidence must allow own-forge NEW_BLOCK echo")
        if "last_local_forge_height" not in tip_evidence_py:
            errors.append("dispatcher tip-evidence must read shadow.last_local_forge_height")
        main_forge_py = (ROOT / "main.py").read_text(encoding="utf-8")
        _note_at = main_forge_py.find("note(1.0, height=")
        if _note_at < 0:
            errors.append("mining must pass forged height into note_local_forge")
        elif _note_at > main_forge_py.find("await self.p2p._broadcast_block"):
            errors.append("mining must note_local_forge before NEW_BLOCK broadcast")
        if "def busy" not in (
            ROOT / "core" / "chain_apply_queue.py"
        ).read_text(encoding="utf-8"):
            errors.append("ChainApplyQueue must expose busy while dispatch is in-flight")
        if not (ROOT / "tests" / "unit" / "test_state_root_probe_coalesce.py").is_file():
            errors.append(
                "tests/unit/test_state_root_probe_coalesce.py missing "
                "(late_state_root + wire_probe_gate unit evidence)"
            )
        # Attestation own-echo + fingerprint dedup (same failure class as own_forge_echo).
        if "_attestation_fingerprint" not in p2p_py or "_attestation_already_seen" not in p2p_py:
            errors.append("P2PNode must fingerprint attestations for echo/dup drop")
        if "_attestation_echo_drops_total" not in p2p_py:
            errors.append("P2PNode must count own-attestation echo drops")
        if "claimed == our" not in p2p_py:
            errors.append("P2PNode must drop own-validator attestation echo before apply")
        # Parent lookup fail-closed (not soft-skip on store error).
        if "def _try_expected_parent" not in p2p_py:
            errors.append("P2PNode must expose _try_expected_parent fail-closed helper")
        if "local_parent_unreadable" not in p2p_py:
            errors.append("parent bind paths must refuse local_parent_unreadable")
        # SyncEngine PathA tip/peer-head probes (parity with live P2P PathA).
        se_py = (ROOT / "sync" / "sync_engine.py").read_text(encoding="utf-8")
        if "tip_probe_enabled=True" not in se_py or "peer_head_probe_enabled=True" not in se_py:
            errors.append("fast_sync CatchUpConfig must enable Path A tip/peer-head probes")
        eio_py = (ROOT / "sync" / "catchup" / "engine_io.py").read_text(encoding="utf-8")
        if "catch_up_peer_head_hash_mismatch" not in eio_py:
            errors.append("SyncEngineCatchUpIO must refuse peer-head hash mismatch")
        if "catch_up_tip_head_mismatch" not in eio_py:
            errors.append("SyncEngineCatchUpIO must refuse tip-head parent mismatch")
    except Exception as exc:
        errors.append(f"STRICT mesh P2P hardening inspect failed: {exc}")
    return errors, warnings


def _check_audit_pack_export() -> tuple[list[str], list[str]]:
    """Audit/CI pack must snapshot encoding contract and Rust hardening checks."""
    errors: list[str] = []
    warnings: list[str] = []
    try:
        ap = (ROOT / "scripts" / "export_audit_pack.py").read_text(encoding="utf-8")
        for needle in ("state_root_encoding.json", "state_root_encoding_status"):
            if needle not in ap:
                errors.append(f"export_audit_pack must include {needle}")
        main_py = (ROOT / "main.py").read_text(encoding="utf-8")
        if "genesis_founder meta read failed" not in main_py:
            errors.append("main.py must fail-loud on genesis_founder meta read")
        if "devnet manifest resolve failed" not in main_py:
            errors.append("main.py must fail-loud on devnet manifest resolve")
        stamp = (ROOT / "scripts" / "stamp_release_evidence.py").read_text(encoding="utf-8")
        if "require-soak-hours" not in stamp:
            errors.append("stamp_release_evidence must support --require-soak-hours")
        test_ci = (ROOT / ".github" / "workflows" / "test.yml").read_text(encoding="utf-8")
        for needle in (
            "Rust format check (abs_native + rust_bridge)",
            "cargo clippy --manifest-path native/abs_native/Cargo.toml",
            "cargo clippy --manifest-path bridge/rust_bridge/Cargo.toml",
        ):
            if needle not in test_ci:
                errors.append(f"test.yml missing Rust hardening step: {needle}")
        sec_ci = (ROOT / ".github" / "workflows" / "security-audit.yml").read_text(encoding="utf-8")
        for needle in (
            "Dependency audit (cargo-audit)",
            "cargo audit --file native/abs_native/Cargo.lock",
            "cargo audit --file bridge/rust_bridge/Cargo.lock",
        ):
            if needle not in sec_ci:
                errors.append(f"security-audit.yml missing Rust audit step: {needle}")
        native_lib = (ROOT / "native" / "abs_native" / "src" / "lib.rs").read_text(encoding="utf-8")
        consensus_src = (
            ROOT / "native" / "abs_native" / "src" / "consensus_select.rs"
        ).read_text(encoding="utf-8")
        p2p_wire_src = (
            ROOT / "native" / "abs_native" / "src" / "p2p_wire.rs"
        ).read_text(encoding="utf-8")
        amount_src = (
            ROOT / "native" / "abs_native" / "src" / "amount.rs"
        ).read_text(encoding="utf-8")
        storage_src = (
            ROOT / "native" / "abs_native" / "src" / "storage" / "mod.rs"
        ).read_text(encoding="utf-8")
        native_surface = (
            native_lib
            + "\n"
            + consensus_src
            + "\n"
            + p2p_wire_src
            + "\n"
            + amount_src
            + "\n"
            + storage_src
        )
        for needle in (
            "MAX_IMPORTED_BLOCKS",
            "MAX_PEER_HEADERS",
            "MAX_BLOCK_JSON_BYTES",
            "MAX_ACCOUNTS_JSON_BYTES",
            "MAX_STATE_ROOT_ACCOUNTS",
            "MAX_STATE_ROOT_BLOBS",
            "MAX_ACCOUNT_BLOB_BYTES",
            "too_many_blocks",
            "too_many_headers",
            "block_json_too_large",
            "too_many_account_blobs",
            "column_families",
            "rocksdb_missing_column_family",
            "account_blob_too_large",
            "MAX_CONSENSUS_VALIDATORS",
            "too_many_validators",
            "consensus_stake_weighted_proposer",
            "state_engine_root_from_accounts_json",
            "parse_p2p_wire_line",
            "encode_p2p_wire_message",
            "p2p_line_too_large",
            "verify_attestation_secp256k1",
            "hash_sorted_json",
            "amount_to_satoshi",
            "amount_apply_delta_satoshi",
            "state_engine_apply_transactions",
            "too_many_txs",
            "plan_transfer_fees",
            "can_afford_transfer",
            "validate_p2p_status_payload",
            "validate_p2p_attestation_payload",
            "validate_p2p_block_announce",
            "validate_p2p_state_root_request",
            "validate_p2p_state_root_response",
            "validate_p2p_handshake_payload",
            "validate_p2p_get_blocks_payload",
            "validate_p2p_wire_tx",
            "validate_p2p_mempool_batch",
            "validate_p2p_validator_register",
            "validate_p2p_peers_list",
            "validate_p2p_get_block",
            "validate_p2p_get_block_by_hash",
            "validate_p2p_blocks_batch",
            "validate_p2p_cross_shard_tx",
            "validate_p2p_cross_shard_ack",
            "validate_p2p_shard_migration",
        ):
            if needle not in native_surface:
                errors.append(f"abs_native lib missing fail-closed bound: {needle}")
    except Exception as exc:
        errors.append(f"audit pack export inspect failed: {exc}")
    return errors, warnings


def _check_balance_precision() -> tuple[list[str], list[str]]:
    """Satoshi dual-write surface for industrial money path."""
    errors: list[str] = []
    warnings: list[str] = []
    try:
        from runtime.amount import (
            SATOSHI_MULTIPLIER,
            apply_delta_satoshi,
            dual_write_balance,
            to_satoshi,
        )
    except ImportError as exc:
        errors.append(f"runtime.amount import failed: {exc}")
        return errors, warnings
    if SATOSHI_MULTIPLIER != 1_000_000:
        errors.append(f"SATOSHI_MULTIPLIER unexpected: {SATOSHI_MULTIPLIER}")
    if to_satoshi(1) != 1_000_000:
        errors.append("to_satoshi(1) != 1_000_000")
    row: dict = {}
    dual_write_balance(row, "1.5")
    if row.get("balance_satoshi") != 1_500_000:
        errors.append("dual_write_balance failed for 1.5 ABS")
    if apply_delta_satoshi(1_000_000, -0.5) != 500_000:
        errors.append("apply_delta_satoshi failed")
    from storage.database import Database

    if not hasattr(Database, "get_balance_satoshi"):
        errors.append("Database missing get_balance_satoshi")
    try:
        from storage.rocks_store import RocksChainStore

        if not hasattr(RocksChainStore, "get_balance_satoshi"):
            errors.append("RocksChainStore missing get_balance_satoshi")
        else:
            import inspect

            # Fail-closed: industrial wheel must expose CF opt-in surface.
            try:
                import abs_native as _abs

                if hasattr(_abs, "RocksEngine"):
                    sig = inspect.signature(_abs.RocksEngine)
                    if "column_families" not in sig.parameters:
                        errors.append("RocksEngine missing column_families kwarg")
            except ImportError:
                pass
    except ImportError as exc:
        warnings.append(f"RocksChainStore unavailable (optional for this host): {exc}")
    try:
        from runtime.state_truth import canonical_balance_satoshi
        from execution.state_engine import StateEngine

        eng = StateEngine()
        eng.create_genesis({"x": 1})
        if eng.get_balance_satoshi("x") != 1_000_000:
            errors.append("StateEngine create_genesis not storing satoshi")
        if canonical_balance_satoshi(None, "x") != 0:
            errors.append("canonical_balance_satoshi(None) should be 0")
        from blockchain.state_adapter import DatabaseStateAdapter
        from storage.database import Database as _DbCheck
        import tempfile, os

        _p = os.path.join(tempfile.mkdtemp(), "gate.db")
        _d = _DbCheck(_p)
        _d.initialize()
        _d.reset_accounts_from_alloc({"gate": 2})
        if _d.get_balance_satoshi("gate") != 2_000_000:
            errors.append("reset_accounts_from_alloc missing balance_satoshi")
        if DatabaseStateAdapter(_d).get_balance_satoshi("gate") != 2_000_000:
            errors.append("DatabaseStateAdapter not using satoshi path")
        # Wave C tip soak: v2 satoshi tip leaf + ceremony gate must remain honest.
        from runtime import state_root_encoding as sre
        import inspect

        enc_src = inspect.getsource(sre)
        if "b_satoshi" not in enc_src or "satoshi_b" not in enc_src:
            errors.append("tip encoding contract missing b_satoshi / satoshi_b (Wave C)")
        if "state_root_v2_ceremony_ok" not in enc_src:
            errors.append("tip encoding must gate v2 on state_root_v2_ceremony_ok")
        from crypto.native import _python_state_root_from_accounts

        tip_src = inspect.getsource(_python_state_root_from_accounts)
        if "encoding_version" not in tip_src or "build_tip_payload" not in tip_src:
            errors.append("tip state_root Python path must use versioned build_tip_payload")
        from blockchain.immutable_state import ImmutableStateManager

        if not hasattr(ImmutableStateManager, "reconcile_from_store"):
            errors.append("ImmutableStateManager missing reconcile_from_store")
        ims = ImmutableStateManager()
        ims.reconcile_from_store(_d, ["gate"])
        if ims.get_balance_satoshi("gate") != 2_000_000:
            errors.append("IMS reconcile_from_store did not mirror DB satoshi")
        # get_address_activity prefers satoshi
        act = _d.get_address_activity("gate")
        if int(act.get("balance_satoshi", -1)) != 2_000_000:
            errors.append("get_address_activity missing balance_satoshi")
    except Exception as exc:
        errors.append(f"state_truth/StateEngine check failed: {exc}")
    return errors, warnings


def _check_evm_depth_labs() -> tuple[list[str], list[str]]:
    """ADR 0010 Profile A EVM depth labs on pin (no Long-Range / Exp-only harnesses)."""
    errors: list[str] = []
    warnings: list[str] = []
    evm_runtime = ROOT / "execution" / "evm_runtime.py"
    if not evm_runtime.is_file():
        errors.append("EVM depth evm_runtime.py missing (Profile A lab honesty)")
    elif "evm_compat_honesty_snapshot" not in evm_runtime.read_text(encoding="utf-8"):
        errors.append("evm_runtime must expose evm_compat_honesty_snapshot")
    if not (ROOT / "scripts" / "evm_rpc_lab.py").is_file():
        errors.append("EVM depth evm_rpc_lab.py missing (wave-9 RPC lab)")
    else:
        rpc_lab = (ROOT / "scripts" / "evm_rpc_lab.py").read_text(encoding="utf-8")
        if "format_fee_history" not in rpc_lab or "estimateGas" not in rpc_lab:
            errors.append("evm_rpc_lab must cover estimateGas + feeHistory null-honesty")
        if "maxPriorityFeePerGas" not in rpc_lab:
            errors.append("evm_rpc_lab must cover maxPriorityFeePerGas null-honesty")
        if "eth_coinbase" not in rpc_lab or "eth_hashrate" not in rpc_lab:
            errors.append("evm_rpc_lab must cover coinbase/mining/hashrate honesty")
        if "eth_getCode" not in rpc_lab or "eth_getStorageAt" not in rpc_lab:
            errors.append("evm_rpc_lab must cover getCode/balance/storage honesty")
    for name, label in (
        ("evm_nested_lab.py", "wave-10 nested lab"),
        ("evm_reorg_lab.py", "wave-11 reorg lab"),
        ("evm_logs_lab.py", "wave-11 logs lab"),
        ("evm_filters_lab.py", "wave-11 filters lab"),
        ("evm_precompile_lab.py", "precompile lab"),
        ("evm_pre_48h_harness.py", "EVM pre-48h readiness"),
        ("verify_evm_depth_lab.ps1", "EVM depth lab verify"),
    ):
        if not (ROOT / "scripts" / name).is_file():
            errors.append(f"EVM depth {name} missing ({label})")
    http_py = (ROOT / "api" / "http.py").read_text(encoding="utf-8")
    if "/evm/status" not in http_py:
        errors.append("GET /evm/status missing (EVM compat honesty endpoint)")
    compat = ROOT / "docs" / "sprouts" / "EVM_COMPAT_MATRIX.md"
    if not compat.is_file():
        errors.append("docs/sprouts/EVM_COMPAT_MATRIX.md missing (EVM depth honesty)")
    else:
        body = compat.read_text(encoding="utf-8")
        if "Absolute-native" not in body:
            errors.append(
                "EVM_COMPAT_MATRIX.md must document Absolute-native opcode map honesty"
            )
    if not (ROOT / "tests" / "unit" / "test_evm_rpc_compat.py").is_file():
        errors.append("tests/unit/test_evm_rpc_compat.py missing (EVM RPC compat units)")
    return errors, warnings


def _check_native_wheel() -> tuple[list[str], list[str]]:
    """Require abs_native self-test and prod-critical exports when wheel is present."""
    errors: list[str] = []
    warnings: list[str] = []
    from crypto import native

    status = native.native_crypto_status(required=True)
    if not status.get("available"):
        errors.append(f"abs_native unavailable: {status.get('error') or 'import failed'}")
        return errors, warnings
    if not status.get("self_test"):
        errors.append("abs_native self_test failed")
    try:
        import abs_native as _abs

        for sym in (
            "RocksEngine",
            "evm_run_until_halt",
            "validate_imported_block_chain",
            "consensus_stake_weighted_proposer",
            "state_engine_root_from_accounts_json",
            "parse_p2p_wire_line",
            "verify_attestation_secp256k1",
            "amount_to_satoshi",
            "state_engine_apply_transactions",
            "plan_transfer_fees",
            "can_afford_transfer",
            "validate_p2p_status_payload",
            "validate_p2p_attestation_payload",
            "validate_p2p_block_announce",
            "validate_p2p_state_root_request",
            "validate_p2p_state_root_response",
            "validate_p2p_handshake_payload",
            "validate_p2p_get_blocks_payload",
            "validate_p2p_wire_tx",
            "validate_p2p_mempool_batch",
            "validate_p2p_validator_register",
            "validate_p2p_peers_list",
            "validate_p2p_get_block",
            "validate_p2p_get_block_by_hash",
            "validate_p2p_blocks_batch",
            "validate_p2p_cross_shard_tx",
            "validate_p2p_cross_shard_ack",
            "validate_p2p_shard_migration",
            "pubkey_to_eth_address",
            "rlp_encode",
            "rlp_decode_single",
        ):
            if not hasattr(_abs, sym):
                errors.append(f"abs_native missing export: {sym}")
    except ImportError as exc:
        errors.append(f"abs_native import failed: {exc}")
    return errors, warnings


def _check_rust_bridge_binary() -> tuple[list[str], list[str]]:
    """Smoke-test abs_bridge_bin when present; require if any live prod JSON enables bridge."""
    errors: list[str] = []
    warnings: list[str] = []
    from runtime.config import Config

    bridge_required = False
    for rel in (
        "docker/node.prod.mesh1.json",
        "docker/node.prod.mesh2.json",
        "docker/node.prod.mesh3.json",
        "docker/node.prod.json",
        "deploy/k8s/node.prod.k8s.json",
        "node.prod.example.json",
        "node.prod.mainnet-v1.example.json",
    ):
        path = ROOT / rel
        if not path.is_file():
            continue
        try:
            cfg_json = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if cfg_json.get("bridge_enabled") is True:
            bridge_required = True
            break

    cfg = Config()
    path = cfg.resolve_rust_bridge_path()
    if not path or not __import__("os").path.isfile(path):
        msg = f"abs_bridge_bin missing: {path or '(unset)'}"
        if bridge_required:
            errors.append(msg + " (required while prod JSON has bridge_enabled=true)")
        else:
            warnings.append(msg + " (OK while bridge OFF)")
        return errors, warnings
    from bridge.health import check_rust_bridge_binary

    result = check_rust_bridge_binary(path)
    if not result.get("ok"):
        errors.append(f"abs_bridge_bin smoke failed: {result.get('error')}")
    return errors, warnings


def run_industrial_gate(
    *,
    prod_smoke_spawn: bool = False,
    min_soak_hours: float = 0,
    ceremony_dir: str = "",
    require_ceremony_pin: bool = False,
    strict_audit: bool = False,
    bridge_cutover: bool = False,
    live_prod_mesh: bool = False,
    probe_l1: bool = False,
    probe_l1_rpc_only: bool = False,
    bridge_live: bool = False,
    fail_on_warnings: bool = False,
) -> int:
    import importlib.util

    native_errors, native_warnings = _check_native_wheel()
    bridge_errors, bridge_warnings = _check_rust_bridge_binary()
    p2p_errors, p2p_warnings = _check_p2p_hardening()
    balance_errors, balance_warnings = _check_balance_precision()
    fail_loud_errors, fail_loud_warnings = _check_fail_loud_surfaces()
    audit_pack_errors, audit_pack_warnings = _check_audit_pack_export()
    evm_depth_errors, evm_depth_warnings = _check_evm_depth_labs()
    soak_errors: list[str] = []
    ceremony_errors: list[str] = []
    ceremony_warnings: list[str] = []

    if ceremony_dir:
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "ceremony_preflight", ROOT / "scripts" / "ceremony_preflight.py"
        )
        cp = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(cp)
        ceremony_errors, ceremony_warnings, _meta = cp.run_ceremony_preflight(
            ceremony_dir,
            require_env_pin=require_ceremony_pin,
        )

    if min_soak_hours > 0:
        evidence_soaks = sorted(
            (ROOT / "docs" / "evidence" / "runs").glob("*/soak_report*.json"),
            key=lambda p: p.stat().st_mtime if p.is_file() else 0,
            reverse=True,
        )
        # Prefer packaged tip-v2 PASS (in-repo) over gitignored logs/ copies.
        soak_candidates = [
            ROOT / "docs" / "evidence" / "runs" / "375d14f" / "soak_report_tipv2_48h_rerun.json",
            *evidence_soaks,
            ROOT / "logs" / "soak_report_tipv2_48h_rerun.json",
            ROOT / "logs" / "soak_report_48h.json",
            ROOT / "logs" / "soak_report.json",
        ]
        # De-dupe while preserving order.
        seen: set[str] = set()
        ordered: list[Path] = []
        for p in soak_candidates:
            key = str(p.resolve()) if p.exists() else str(p)
            if key in seen:
                continue
            seen.add(key)
            ordered.append(p)
        soak_path = next((p for p in ordered if p.is_file()), ordered[0])
        if not soak_path.is_file():
            soak_errors.append(
                f"soak_report missing: {soak_path} (need {min_soak_hours}h prod soak)"
            )
        else:
            try:
                soak = json.loads(soak_path.read_text(encoding="utf-8"))
                # Skip historical FAIL packs when a newer PASS exists later in candidates.
                if not soak.get("passed"):
                    alt = next(
                        (
                            p
                            for p in ordered
                            if p.is_file()
                            and p != soak_path
                            and bool(
                                json.loads(p.read_text(encoding="utf-8")).get("passed")
                            )
                        ),
                        None,
                    )
                    if alt is not None:
                        soak_path = alt
                        soak = json.loads(soak_path.read_text(encoding="utf-8"))
                hrs = float(soak.get("hours_requested", 0) or 0)
                if hrs < min_soak_hours:
                    soak_errors.append(f"soak_report hours_requested={hrs} < {min_soak_hours}")
                elapsed = soak.get("hours_elapsed")
                if elapsed is None:
                    try:
                        started = datetime.fromisoformat(
                            str(soak.get("started_at", "")).replace("Z", "+00:00")
                        )
                        ended = datetime.fromisoformat(
                            str(soak.get("ended_at", "")).replace("Z", "+00:00")
                        )
                        elapsed = (ended - started).total_seconds() / 3600.0
                    except (TypeError, ValueError, OSError):
                        elapsed = None
                if elapsed is not None and float(elapsed) < float(min_soak_hours) * 0.95:
                    soak_errors.append(
                        f"soak_report hours_elapsed={float(elapsed):.2f} < "
                        f"{min_soak_hours}*0.95 (wall-clock duration short)"
                    )
                if not soak.get("passed"):
                    soak_errors.append(f"soak_report passed=false (see {soak_path})")
            except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
                soak_errors.append(f"soak_report unreadable: {exc}")

    spec = importlib.util.spec_from_file_location(
        "mainnet_readiness", ROOT / "scripts" / "mainnet_readiness.py"
    )
    mr = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mr)

    errors, warnings, sections = mr.run_gate(
        live=False,
        live_prod_mesh=live_prod_mesh,
        strict_audit=strict_audit,
        ceremony_dir=ceremony_dir,
        bridge_cutover=bridge_cutover,
        probe_l1=probe_l1,
        probe_l1_rpc_only=probe_l1_rpc_only,
        bridge_live=bridge_live,
    )
    errors.extend(soak_errors)
    errors.extend(native_errors)
    errors.extend(bridge_errors)
    errors.extend(p2p_errors)
    errors.extend(balance_errors)
    errors.extend(fail_loud_errors)
    errors.extend(audit_pack_errors)
    errors.extend(evm_depth_errors)
    errors.extend(ceremony_errors)
    warnings.extend(native_warnings)
    warnings.extend(bridge_warnings)
    warnings.extend(p2p_warnings)
    warnings.extend(balance_warnings)
    warnings.extend(fail_loud_warnings)
    warnings.extend(audit_pack_warnings)
    warnings.extend(evm_depth_warnings)
    warnings.extend(ceremony_warnings)
    report = {
        "ok": not errors,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "errors": errors,
        "warnings": warnings,
        "sections": sections,
        "native_wheel": not native_errors,
        "p2p_hardening": not p2p_errors,
        "balance_precision": not balance_errors,
        "fail_loud_surfaces": not fail_loud_errors,
    }

    if prod_smoke_spawn:
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "verify_p2p_ci", ROOT / "scripts" / "verify_p2p_ci.py"
        )
        mod = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(mod)
        rc = mod.run_prod_smoke_spawn()
        report["prod_smoke_spawn_rc"] = rc
        if rc != 0:
            errors.append(f"prod_smoke_spawn exited {rc}")

    for label, (script, attr) in (
        ("runbook", ("runbook_check.py", "main")),
        ("evm_opcode_parity", ("evm_opcode_parity_gate.py", "main")),
        ("prod_gate", ("prod_gate.py", "main")),
        ("bridge_off_audit", ("bridge_off_audit_gate.py", "main")),
    ):
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            label, ROOT / "scripts" / script
        )
        mod = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(mod)
        rc = int(getattr(mod, attr)())
        report[f"{label}_rc"] = rc
        if rc != 0:
            errors.append(f"{label} gate exited {rc}")

    out = ROOT / "data" / "industrial_gate.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    report["ok"] = not errors
    report["errors"] = errors
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")

    if errors:
        print("FAIL: industrial gate")
        for err in errors:
            print(f"  - {err}")
        return 1
    print("OK: industrial gate")
    if warnings:
        print(f"  ({len(warnings)} warning(s) — see {out})")
        for w in warnings[:12]:
            print(f"  warn: {w}")
        if len(warnings) > 12:
            print(f"  warn: ... +{len(warnings) - 12} more")
        if fail_on_warnings:
            print("FAIL: industrial gate (--fail-on-warnings)")
            return 1
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Industrial code gate (no strict audit)")
    parser.add_argument(
        "--prod-smoke-spawn",
        action="store_true",
        help="Run isolated verify_p2p_ci --mode prod-smoke after static checks",
    )
    parser.add_argument(
        "--min-soak-hours",
        type=float,
        default=0,
        help="Require logs/soak_report.json with passed=true and hours_requested >= N (0=skip)",
    )
    parser.add_argument(
        "--ceremony-dir",
        default="",
        help="Run ceremony_preflight on this dir before static checks (empty=skip)",
    )
    parser.add_argument(
        "--require-ceremony-pin",
        action="store_true",
        help="With --ceremony-dir, require GENESIS_CEREMONY_HASH to match",
    )
    parser.add_argument("--json", action="store_true", help="Print report path only")
    parser.add_argument(
        "--fail-on-warnings",
        action="store_true",
        help="Exit non-zero when warnings are present (release strict mode)",
    )
    parser.add_argument(
        "--bridge-cutover",
        action="store_true",
        help="Include bridge L1 cutover static gate",
    )
    parser.add_argument(
        "--probe-l1",
        action="store_true",
        help="With --bridge-cutover, probe L1 RPC and contract bytecode",
    )
    parser.add_argument(
        "--probe-l1-rpc-only",
        action="store_true",
        help="With --bridge-cutover, probe ETH_RPC_URL only",
    )
    parser.add_argument(
        "--bridge-live",
        action="store_true",
        help="With --bridge-cutover, live checks on bridge-enabled prod node",
    )
    args = parser.parse_args()
    rc = run_industrial_gate(
        prod_smoke_spawn=args.prod_smoke_spawn,
        min_soak_hours=args.min_soak_hours,
        ceremony_dir=args.ceremony_dir,
        require_ceremony_pin=args.require_ceremony_pin,
        bridge_cutover=args.bridge_cutover,
        probe_l1=args.probe_l1,
        probe_l1_rpc_only=args.probe_l1_rpc_only,
        bridge_live=args.bridge_live,
        fail_on_warnings=args.fail_on_warnings,
    )
    if args.json:
        print(str(ROOT / "data" / "industrial_gate.json"))
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
