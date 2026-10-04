"""StateService._credit_sat refuses float update_balance fallback."""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.components.state_service import StateService


class _NoSatoshiStore:
    def balance_delta(self, *_a, **_k):
        raise AssertionError("float balance_delta must not be used")

    def update_balance(self, *_a, **_k):
        raise AssertionError("float update_balance must not be used")


class _SatoshiStore:
    def __init__(self) -> None:
        self.deltas = []

    def balance_delta_satoshi(self, address, delta):
        self.deltas.append((address, int(delta)))


def _host(store) -> SimpleNamespace:
    return SimpleNamespace(storage=store, config=SimpleNamespace())


def test_credit_sat_refuses_float_store():
    svc = StateService(_host(_NoSatoshiStore()))
    with pytest.raises(RuntimeError, match="satoshi_store_required_credit"):
        svc._credit_sat("0xabc", 1000, in_atomic=True)


def test_credit_sat_uses_balance_delta_satoshi():
    store = _SatoshiStore()
    svc = StateService(_host(store))
    svc._credit_sat("0xabc", 2500, in_atomic=True)
    assert store.deltas == [("0xabc", 2500)]


def test_state_service_source_has_no_float_credit_fallback():
    src = (ROOT / "core" / "components" / "state_service.py").read_text(encoding="utf-8")
    assert "satoshi_store_required_credit" in src
    assert "update_balance(address, abs_delta)" not in src
