"""ZK + NFT sprout honesty (no invent demo value / enabled)."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_zk_range_no_invent_demo_42():
    src = (ROOT / "api" / "http.py").read_text(encoding="utf-8")
    chunk = src.split('path == "/zk/prove/range"')[1].split("elif path")[0]
    assert "do not invent demo 42" in chunk
    assert '"valid": True' not in chunk
    assert "educational_only" in chunk


def test_zk_prove_no_force_valid_true():
    src = (ROOT / "api" / "http.py").read_text(encoding="utf-8")
    chunk = src.split('path == "/zk/prove"')[1].split("elif path")[0]
    assert '"valid": True, **pd}' not in chunk
    assert "educational_only" in chunk


def test_nft_stats_no_invent_enabled():
    from features.nft_ports import NftMarketplaceAdapter

    class _Core:
        tokens = {}

        def get_stats(self):
            return {"execution_bound": False}

    stats = NftMarketplaceAdapter(_Core()).get_stats()
    assert stats["enabled"] is False
    assert NftMarketplaceAdapter(type("M", (), {"tokens": {}})()).get_stats()["enabled"] is False
