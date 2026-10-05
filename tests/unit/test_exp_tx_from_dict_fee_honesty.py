"""Exp mid-soak: Transaction.from_dict / execution mempool no invent gas/fee."""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def test_from_dict_source_no_invent_21000():
    src = (ROOT / "core" / "blockchain.py").read_text(encoding="utf-8")
    chunk = src.split("def from_dict", 1)[1].split("def __repr__", 1)[0]
    assert 'd.get("gas", 21_000)' not in chunk
    assert 'd.get("gas", 21000)' not in chunk
    assert "gas_required" in chunk


def test_from_dict_refuses_missing_and_zero_gas():
    from core.blockchain import Transaction

    with pytest.raises(ValueError, match="gas_required"):
        Transaction.from_dict(
            {
                "from": "0x" + "a" * 40,
                "to": "0x" + "b" * 40,
                "value": 1,
                "nonce": 0,
            }
        )
    with pytest.raises(ValueError, match="gas_required"):
        Transaction.from_dict(
            {
                "from": "0x" + "a" * 40,
                "to": "0x" + "b" * 40,
                "value": 1,
                "nonce": 0,
                "gas": 0,
            }
        )


def test_from_dict_binds_explicit_gas():
    from core.blockchain import Transaction

    tx = Transaction.from_dict(
        {
            "from": "0x" + "a" * 40,
            "to": "0x" + "b" * 40,
            "value": 1,
            "nonce": 0,
            "gas": 65000,
            "timestamp": 1,
        }
    )
    assert tx.gas == 65000


def test_execution_mempool_refuses_missing_fee(monkeypatch):
    from execution.mempool import Mempool

    # Lab float path — clear ambient prod shell env (operator mesh hosts).
    monkeypatch.delenv("ABS_DEPLOYMENT_MODE", raising=False)
    monkeypatch.delenv("DEPLOYMENT_MODE", raising=False)
    mp = Mempool()
    assert (
        mp.add_transaction(
            {
                "from": "alice",
                "to": "bob",
                "value": 1,
                "nonce": 0,
            }
        )
        is False
    )
    # Pin refuses invent gas=21000 — fee alone is not enough.
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
    h = mp.add_transaction(
        {
            "from": "alice",
            "to": "bob",
            "value": 1,
            "nonce": 0,
            "gas_price": 0.001,
            "gas": 21000,
        }
    )
    assert isinstance(h, str) and h.startswith("0x")


def test_secure_mempool_fee_required(monkeypatch):
    from execution.secure_mempool import SecureMempool

    class _State:
        def get_balance(self, _addr):
            return 100.0

    monkeypatch.delenv("ABS_DEPLOYMENT_MODE", raising=False)
    monkeypatch.delenv("DEPLOYMENT_MODE", raising=False)
    sm = SecureMempool(_State())
    ok, reason = sm.add_transaction(
        {"from": "alice", "to": "bob", "value": 1, "nonce": 0}
    )
    assert ok is False
    assert reason == "fee_required"
