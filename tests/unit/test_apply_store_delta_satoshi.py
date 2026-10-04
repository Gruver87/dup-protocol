#!/usr/bin/env python3
"""apply_store_delta_satoshi prefers integer satoshi writes."""

from __future__ import annotations

from runtime.amount import apply_store_delta_satoshi, to_satoshi


class _SatStore:
    def __init__(self) -> None:
        self.sats: dict[str, int] = {}

    def balance_delta_satoshi(self, address: str, delta_sat: int) -> None:
        self.sats[address] = int(self.sats.get(address, 0)) + int(delta_sat)


class _FloatStore:
    def __init__(self) -> None:
        self.deltas: list[tuple[str, float]] = []

    def update_balance(self, address: str, delta: float) -> float:
        self.deltas.append((address, float(delta)))
        return float(delta)


def test_apply_store_delta_satoshi_prefers_integer_path():
    store = _SatStore()
    assert apply_store_delta_satoshi(store, "0xa", 1_500_000) is True
    assert store.sats["0xa"] == 1_500_000


def test_apply_store_delta_satoshi_falls_back_to_update_balance():
    store = _FloatStore()
    assert (
        apply_store_delta_satoshi(
            store, "0xb", int(to_satoshi(2.5)), allow_float_fallback=True
        )
        is True
    )
    assert store.deltas and store.deltas[0][0] == "0xb"


def test_apply_store_delta_satoshi_default_refuses_float_fallback():
    store = _FloatStore()
    assert apply_store_delta_satoshi(store, "0xd", 1000) is False
    assert store.deltas == []


def test_apply_store_delta_satoshi_refuses_float_when_disallowed():
    store = _FloatStore()
    assert (
        apply_store_delta_satoshi(
            store, "0xc", 1000, allow_float_fallback=False
        )
        is False
    )
    assert store.deltas == []
