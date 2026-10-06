"""Exp→pin ops: grafana RocksDB/under-mesh/mempool demote panels + proposer hasattr."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_grafana_dashboard_has_ops_panels_27_37():
    dash = json.loads(
        (ROOT / "deploy" / "grafana" / "dashboard.json").read_text(encoding="utf-8")
    )
    by_id = {p.get("id"): p for p in dash.get("panels") or []}
    expected = {
        27: "abs_rocksdb_running_compactions",
        28: "abs_rocksdb_running_flushes",
        29: "abs_rocksdb_estimate_num_keys",
        30: "abs_p2p_under_mesh",
        31: "abs_p2p_sync_status",
        32: "abs_p2p_peer_sync_gap",
        33: "abs_p2p_mesh_min_peers",
        34: "abs_rocksdb_native_pack_fallbacks",
        35: "abs_mempool_store_demoted",
        36: "abs_mempool_store_demote_count",
        37: "abs_mempool_store_backend",
    }
    for pid, needle in expected.items():
        panel = by_id.get(pid)
        assert panel is not None, f"missing grafana panel id={pid}"
        exprs = " ".join(
            str(t.get("expr") or "") for t in (panel.get("targets") or [])
        )
        assert needle in exprs, f"panel {pid} missing expr {needle}"


def test_proposer_audit_count_hasattr_guarded():
    src = (ROOT / "api" / "http.py").read_text(encoding="utf-8")
    assert 'hasattr(db, "count_proposer_audit")' in src
    # stats + history both guarded (not bare db.count_proposer_audit() only)
    assert src.count('hasattr(db, "count_proposer_audit")') >= 2
