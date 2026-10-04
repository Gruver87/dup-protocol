"""Execution/secure mempool: prefer amount_satoshi; prod refuses float-only."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def test_execution_mempool_binds_amount_satoshi(monkeypatch):
    from execution.mempool import Mempool
    from runtime.amount import to_satoshi

    monkeypatch.delenv("ABS_DEPLOYMENT_MODE", raising=False)
    monkeypatch.delenv("DEPLOYMENT_MODE", raising=False)
    mp = Mempool()
    h = mp.add_transaction(
        {
            "from": "alice",
            "to": "bob",
            "value": 1,
            "amount_satoshi": int(to_satoshi(1)),
            "nonce": 0,
            "gas_price": 0.001,
            "gas": 21_000,
        }
    )
    assert isinstance(h, str) and h.startswith("0x")


def test_execution_mempool_prod_refuses_float_only(monkeypatch):
    from execution.mempool import Mempool

    monkeypatch.setenv("ABS_DEPLOYMENT_MODE", "prod")
    monkeypatch.delenv("DEPLOYMENT_MODE", raising=False)
    mp = Mempool()
    assert (
        mp.add_transaction(
            {
                "from": "alice",
                "to": "bob",
                "value": 1,
                "nonce": 0,
                "gas_price": 0.001,
            }
        )
        is False
    )


def test_secure_mempool_prod_amount_satoshi_required(monkeypatch):
    from execution.secure_mempool import SecureMempool

    class _State:
        def get_balance(self, _addr):
            return 100.0

    monkeypatch.setenv("ABS_DEPLOYMENT_MODE", "prod")
    monkeypatch.delenv("DEPLOYMENT_MODE", raising=False)
    sm = SecureMempool(_State())
    ok, reason = sm.add_transaction(
        {"from": "alice", "to": "bob", "value": 1, "nonce": 0, "gas_price": 0.001}
    )
    assert ok is False
    assert reason == "amount_satoshi_required"


def test_secure_mempool_accepts_amount_satoshi(monkeypatch):
    from execution.secure_mempool import SecureMempool
    from runtime.amount import to_satoshi

    class _State:
        def get_balance(self, _addr):
            return 100.0

    monkeypatch.delenv("ABS_DEPLOYMENT_MODE", raising=False)
    monkeypatch.delenv("DEPLOYMENT_MODE", raising=False)
    sm = SecureMempool(_State())
    ok, reason = sm.add_transaction(
        {
            "from": "alice",
            "to": "bob",
            "value": 1,
            "amount_satoshi": int(to_satoshi(1)),
            "nonce": 0,
            "gas_price": 0.001,
            "gas": 21_000,
        }
    )
    assert ok is True, reason
