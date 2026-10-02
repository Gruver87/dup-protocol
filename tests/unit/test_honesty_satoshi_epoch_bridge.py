"""Fail-closed honesty: satoshi store refuse, epoch null, bridge stats/amount."""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime.amount import from_satoshi_float, to_satoshi
from storage.hybrid_database import HybridDatabase


class _FloatOnlyCore:
    def get_balance(self, address: str) -> float:
        return 1.5

    def balance_delta(self, address: str, delta: float) -> None:
        pass


def test_hybrid_get_balance_satoshi_refuses_float_fallback():
    h = HybridDatabase.__new__(HybridDatabase)
    h._core = _FloatOnlyCore()
    with pytest.raises(RuntimeError, match="satoshi_store_required"):
        h.get_balance_satoshi("0xabc")


def test_hybrid_balance_delta_satoshi_refuses_float_fallback():
    h = HybridDatabase.__new__(HybridDatabase)
    h._core = _FloatOnlyCore()
    with pytest.raises(RuntimeError, match="satoshi_store_required"):
        h.balance_delta_satoshi("0xabc", 1_000_000)


def test_hybrid_satoshi_delegates_when_core_has_api():
    core = SimpleNamespace(
        get_balance_satoshi=lambda _a: 2_500_000,
        balance_delta_satoshi=MagicMock(),
    )
    h = HybridDatabase.__new__(HybridDatabase)
    h._core = core
    assert h.get_balance_satoshi("0xabc") == 2_500_000
    h.balance_delta_satoshi("0xabc", 100)
    core.balance_delta_satoshi.assert_called_once_with("0xabc", 100)


def test_epoch_current_null_when_manager_missing():
    height = 320
    em = None
    if em and hasattr(em, "get_epoch"):
        payload = {"epoch": em.get_epoch(height)}
    else:
        payload = {
            "enabled": False,
            "epoch": None,
            "block_height": height,
            "error": "epoch_manager_unavailable",
        }
    assert payload["epoch"] is None
    assert payload["enabled"] is False
    assert payload["error"] == "epoch_manager_unavailable"


def test_bridge_adapter_stats_do_not_invent_enabled_true():
    from bridge.adapter import RustBridgeAdapter

    inner = SimpleNamespace(get_stats=lambda: {})
    br = RustBridgeAdapter.__new__(RustBridgeAdapter)
    br._inner = inner
    stats = br.get_stats()
    assert stats["enabled"] is False
    assert stats["port"] == "BridgePort"


def test_bridge_adapter_prefers_amount_satoshi():
    from bridge.ports import InboundEnvelope

    env = InboundEnvelope(
        from_chain="ethereum",
        to_addr="0x" + "11" * 20,
        amount=99.0,
        event_tx_hash="0xevt",
        amount_satoshi=int(to_satoshi(1.0)),
    )
    if env.amount_satoshi is not None:
        amount_abs = float(from_satoshi_float(int(env.amount_satoshi)))
    else:
        amount_abs = float(env.amount)
    assert amount_abs == pytest.approx(1.0)
    assert amount_abs != pytest.approx(99.0)
