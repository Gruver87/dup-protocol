"""Exp mid-soak: no paint-green enabled/valid on status/ZK/sync surfaces."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

ROOT = Path(__file__).resolve().parents[2]


def test_zk_prove_no_forced_valid_true():
    src = (ROOT / "api" / "http.py").read_text(encoding="utf-8")
    range_chunk = src.split('path == "/zk/prove/range"')[1].split("elif path")[0]
    assert '"valid": True' not in range_chunk
    assert "educational_only" in range_chunk
    prove_chunk = src.split('path == "/zk/prove"')[1].split("elif path")[0]
    assert '"valid": True, **pd' not in prove_chunk
    assert "educational_only" in prove_chunk


def test_sync_fallback_enabled_false():
    from api.http import _build_sync_status

    p2p = MagicMock()
    p2p.get_peers_info.return_value = [{"height": 10}]
    p2p.sync_engine = None
    p2p.peer_count.return_value = 1
    cfg = SimpleNamespace(bootstrap_peers=[], state_root_strict_p2p=True)
    bc = MagicMock()
    bc.get_height.return_value = 5
    bc.get_state_root.return_value = "ab" * 32

    status = _build_sync_status(None, p2p, bc, cfg)
    assert status["source"] == "p2p_fallback"
    assert status["enabled"] is False
    assert status["sync_engine_missing"] is True


def test_multisig_wasm_use_http_amount_abs():
    src = (ROOT / "api" / "http.py").read_text(encoding="utf-8")
    for marker in ('path == "/multisig/create"', 'path == "/wasm/call"'):
        chunk = src.split(marker)[1].split("elif path")[0]
        assert "_http_amount_abs" in chunk, marker


def test_nft_ports_enabled_follows_execution_bound():
    from features.nft_ports import NftMarketplaceAdapter

    class _M:
        tokens = {}

        def get_stats(self):
            return {"token_count": 0}

    port = NftMarketplaceAdapter(_M())
    # Honesty: do not invent enabled=True without execution_bound/balance_backend.
    assert port.get_stats()["enabled"] is False

    class _M2:
        tokens = {}

        def get_stats(self):
            return {"token_count": 0, "execution_bound": True, "balance_backend": True}

    assert NftMarketplaceAdapter(_M2()).get_stats()["enabled"] is True


def test_rocks_metrics_receipts_capability_needle():
    src = (ROOT / "storage" / "rocks_store.py").read_text(encoding="utf-8")
    assert '"receipts_enabled": True' not in src
    assert "startswith(\"rocks\")" in src or "startswith('rocks')" in src
