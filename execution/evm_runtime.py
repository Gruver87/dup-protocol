"""EVM depth runtime honesty (Profile A lab packaging, ADR 0016).

Single apply path — not a FEATURE_* sprout. Snapshot surfaces compat matrix
rows for HTTP / gates without claiming full geth or soak proof.
"""

from __future__ import annotations

from typing import Any, Dict, List, Mapping

# Mirror docs/sprouts/EVM_COMPAT_MATRIX.md — update both when a wave closes a row.
_COMPAT_ROWS: List[Dict[str, str]] = [
    {
        "area": "opcode_map_yellow_paper",
        "status": "absolute_native",
        "notes": (
            "Comparison/bitwise bytes remapped vs Yellow Paper "
            "(e.g. Absolute 0x10=AND, 0x16=LT; YP 0x10=LT, 0x16=AND). "
            "Not solc/geth drop-in. Remap is breaking ADR — not silent."
        ),
    },
    {"area": "transfer_fee_burn", "status": "supported", "notes": "Native apply + satoshi domain"},
    {
        "area": "create_create2_deploy_salt",
        "status": "partial",
        "notes": (
            "Inline CREATE2 EIP-1014 when armed; host deploy_contract string salt "
            "is keccak→word (Absolute), not raw EIP-1014 salt bytes. "
            "evm_require_deploy_salt on prod JSON"
        ),
    },
    {
        "area": "call_staticcall_host",
        "status": "partial",
        "notes": "Host-in-apply nested depth cap 4; sticky STATICCALL (EIP-214)",
    },
    {
        "area": "precompiles_0x01_0x09",
        "status": "partial",
        "notes": "execution/evm_precompiles.py on call + apply paths",
    },
    {"area": "eth_call", "status": "supported", "notes": "Hex ABI word encoding + precompile bytes"},
    {
        "area": "eth_estimateGas",
        "status": "supported_absolute",
        "notes": "Missing adapter → JSON null; Absolute honesty — not geth gas",
    },
    {
        "area": "eth_getTransactionReceipt",
        "status": "supported_absolute",
        "notes": "Null-honesty; no 21000 stub",
    },
    {"area": "eth_getLogs", "status": "supported_absolute", "notes": "Log index; missing fields → null"},
    {
        "area": "eth_getBlockByNumber",
        "status": "supported_absolute",
        "notes": "Absolute merkle roots; not Ethereum MPT",
    },
    {
        "area": "eth_feeHistory",
        "status": "supported_absolute",
        "notes": "baseFeePerGas/reward null (not EIP-1559)",
    },
    {
        "area": "eth_maxPriorityFeePerGas",
        "status": "supported_absolute",
        "notes": "Unset/0 → JSON null (not EIP-1559 tip market)",
    },
    {
        "area": "eth_coinbase_mining_hashrate",
        "status": "supported_absolute",
        "notes": "Empty coinbase null; mining mesh-honest; hashrate 0x0 (not ethash)",
    },
    {
        "area": "eth_getCode_balance_storage",
        "status": "supported_absolute",
        "notes": "Missing account: code 0x, balance/storage 0x0",
    },
    {
        "area": "eth_protocolVersion",
        "status": "supported_absolute",
        "notes": "Compat constant 0x41 — not eth/65 wire claim",
    },
    {
        "area": "eth_chainId_net_clientVersion",
        "status": "supported_absolute",
        "notes": "Config chain_id + Absolute/{node_version}/python client string",
    },
    {
        "area": "eth_syncing_net_peerCount",
        "status": "supported_absolute",
        "notes": "No adapter → false/0x0; mesh-bound when P2P wired",
    },
    {
        "area": "eth_gasPrice",
        "status": "supported_absolute",
        "notes": "JSON null by default; config floor only when advertise_config_gas_price=true",
    },
    {
        "area": "eth_getTransactionCount",
        "status": "supported_absolute",
        "notes": "Observed nonce; missing account 0x0",
    },
    {
        "area": "eth_getTransactionByHash",
        "status": "supported_absolute",
        "notes": "Missing tx null; format_tx null-honesty",
    },
    {
        "area": "eth_getBlockTransactionCount",
        "status": "supported_absolute",
        "notes": "Missing block null; observed count hex",
    },
    {
        "area": "eth_blockNumber_accounts_mempoolSize",
        "status": "supported_absolute",
        "notes": "Tip hex; accounts empty when unset; mempool 0x0 empty",
    },
    {
        "area": "eth_getTransactionByBlockNumberAndIndex",
        "status": "supported_absolute",
        "notes": "Missing block/index null",
    },
    {
        "area": "eth_getTransactionReceipt_rpc",
        "status": "supported_absolute",
        "notes": "Missing tx null; format_receipt null-honesty",
    },
    {
        "area": "eth_getLogs_rpc",
        "status": "supported_absolute",
        "notes": "Sparse fields null; empty filter []",
    },
    {
        "area": "eth_getBlockByNumber_rpc",
        "status": "supported_absolute",
        "notes": "Missing block null; sparse header null-honesty",
    },
    {
        "area": "eth_newFilter_polling",
        "status": "supported_absolute",
        "notes": "HTTP polling filters; unknown id []; not WS eth_subscribe",
    },
    {
        "area": "eth_subscribe_ws",
        "status": "not_claimed",
        "notes": "Code present (api/eth_ws_subscriptions.py) — not industrial / not EVM STRICT evidence",
    },
    {"area": "eip_4844_blobs", "status": "not_claimed", "notes": "Out of scope"},
    {"area": "eof", "status": "not_claimed", "notes": "Out of scope"},
    {"area": "full_geth_json_rpc", "status": "not_claimed", "notes": "Wave-gated methods only"},
]

_NOT_CLAIMED = ("eth_subscribe_ws", "eip_4844_blobs", "eof", "full_geth_json_rpc")


def compat_matrix_rows() -> List[Dict[str, str]]:
    """Return a copy of the honest compat matrix rows."""
    return [dict(r) for r in _COMPAT_ROWS]


def evm_compat_honesty_snapshot(config: Any | None = None) -> Dict[str, Any]:
    """Honesty surface for GET /evm/status (not full geth / not soak proof)."""
    enabled = bool(getattr(config, "evm_enabled", True)) if config else True
    mode = str(getattr(config, "deployment_mode", "") or "").strip().lower() if config else ""
    create2 = bool(getattr(config, "evm_create2_eip1014", False)) if config else False
    deploy_salt = bool(getattr(config, "evm_require_deploy_salt", False)) if config else False
    gas_limit = int(getattr(config, "evm_gas_limit", 8_000_000) or 8_000_000) if config else 8_000_000
    prod_hardened = mode in ("prod", "production", "staging") and create2 and deploy_salt

    supported_n = sum(
        1
        for r in _COMPAT_ROWS
        if r["status"] in ("supported", "supported_prod", "supported_absolute")
    )
    partial_n = sum(1 for r in _COMPAT_ROWS if r["status"] == "partial")
    not_claimed_n = sum(1 for r in _COMPAT_ROWS if r["status"] == "not_claimed")
    absolute_n = sum(1 for r in _COMPAT_ROWS if r["status"] == "supported_absolute")

    if not enabled:
        detail = "evm_disabled: execution VM off (unexpected on Profile A)"
    elif prod_hardened:
        detail = (
            f"evm_prod_profile: CREATE2+deploy_salt armed; gas_limit={gas_limit}; "
            "Absolute opcode map (not Yellow Paper LT/AND); Shanghai/Cancun subset labels — "
            "not full geth / not EIP-4844 / not solc drop-in"
        )
    elif mode in ("prod", "production", "staging"):
        detail = "evm_prod_incomplete: CREATE2 or deploy_salt not armed on config"
    else:
        detail = (
            f"evm_dev_profile: gas_limit={gas_limit}; "
            "Absolute opcode map (not Yellow Paper); "
            "lab waves 8–11 (precompile/rpc/nested/reorg/logs/filters); mesh smoke separate"
        )

    return {
        "evm_enabled": enabled,
        "deployment_mode": mode or "unknown",
        "evm_gas_limit": gas_limit,
        "evm_create2_eip1014": create2,
        "evm_require_deploy_salt": deploy_salt,
        "prod_hardened": bool(prod_hardened),
        "opcode_map_honesty": {
            "yellow_paper_compatible": False,
            "absolute_native_map": True,
            "example": {
                "absolute_0x10": "AND",
                "absolute_0x16": "LT",
                "yellow_paper_0x10": "LT",
                "yellow_paper_0x16": "AND",
            },
            "note": (
                "solc/geth bytecode is not drop-in; remap to Yellow Paper is a "
                "breaking ADR (Phase F) — not silent"
            ),
        },
        "compat_matrix": compat_matrix_rows(),
        "supported_count": supported_n,
        "supported_absolute_count": absolute_n,
        "partial_count": partial_n,
        "not_claimed_count": not_claimed_n,
        "not_claimed": list(_NOT_CLAIMED),
        "lab_scripts": [
            "scripts/evm_opcode_parity_gate.py",
            "scripts/evm_mempool_load_harness.py",
        ],
        "mesh_evidence_script": "scripts/prod_evm_smoke.py",
        "mesh_evidence_note": (
            "Live prod mesh deploy + eth_getStorageAt; requires Docker mesh — "
            "not a substitute for lab scripts. Experimental R&D labs "
            "(evm_*_lab.py) live on dup-protocol-experimental only."
        ),
        "strict_prep_note": (
            "EVM STRICT = start_soak_evm_mesh_48h_strict.ps1 after live evm_pre_48h_harness; "
            "not started from /evm/status; not EVM-only 48h"
        ),
        "detail": detail,
    }


def merge_compat_summary(existing: Mapping[str, Any] | None = None) -> Dict[str, Any]:
    """Merge opcode summary with compat honesty (for /evm/status enrichment)."""
    base = dict(existing or {})
    snap = evm_compat_honesty_snapshot(None)
    base["compat_honesty"] = {
        "supported_count": snap["supported_count"],
        "partial_count": snap["partial_count"],
        "not_claimed_count": snap["not_claimed_count"],
        "detail": snap["detail"],
    }
    return base
