"""Rocks stats_account_count must seed via get_stats and stay O(1) thereafter."""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

try:
    import abs_native  # type: ignore

    HAS_ROCKS = hasattr(abs_native, "RocksEngine")
except Exception:
    HAS_ROCKS = False

pytestmark = pytest.mark.skipif(not HAS_ROCKS, reason="abs_native.RocksEngine not built")


def test_get_stats_seeds_cached_account_count(tmp_path):
    from storage.rocks_store import RocksChainStore

    store = RocksChainStore(str(tmp_path / "chainstore"), synchronous="FULL")
    store.initialize()
    try:
        assert store.get_cached_account_count() is None
        store.set_balance("0x" + "a" * 40, 1.0)
        store.set_balance("0x" + "b" * 40, 2.0)
        # Bump no-ops until meta is seeded; get_stats seeds via prefix scan once.
        assert store.get_cached_account_count() is None
        stats = store.get_stats()
        assert stats["total_accounts"] == 2
        assert store.get_cached_account_count() == 2
        store.set_balance("0x" + "c" * 40, 3.0)
        assert store.get_cached_account_count() == 3
    finally:
        store.close()
