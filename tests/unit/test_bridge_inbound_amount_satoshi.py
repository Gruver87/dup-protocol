"""Bridge inbound HTTP prefers amount_satoshi; prod refuses float-only."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime.amount import from_satoshi_float, to_satoshi


def test_inbound_envelope_prefers_amount_satoshi():
    from api.http import _inbound_envelope_from_body

    env = _inbound_envelope_from_body(
        {
            "tx_hash": "0xabc",
            "recipient": "0x" + "11" * 20,
            "amount": 99.0,
            "amount_satoshi": 1_000_000,
            "from_chain": "ethereum",
        },
        cfg=SimpleNamespace(deployment_mode="dev"),
    )
    assert env.amount_satoshi == 1_000_000
    assert env.amount == pytest.approx(1.0)


def test_inbound_envelope_prod_refuses_float_only(monkeypatch):
    from api.http import _inbound_envelope_from_body

    monkeypatch.delenv("DEPLOYMENT_MODE", raising=False)
    with pytest.raises(ValueError, match="amount_satoshi required"):
        _inbound_envelope_from_body(
            {
                "tx_hash": "0xabc",
                "recipient": "0x" + "11" * 20,
                "amount": 1.0,
                "from_chain": "ethereum",
            },
            cfg=SimpleNamespace(deployment_mode="prod"),
        )


def test_inbound_envelope_dev_float_derives_satoshi():
    from api.http import _inbound_envelope_from_body

    env = _inbound_envelope_from_body(
        {
            "tx_hash": "0xabc",
            "recipient": "0x" + "11" * 20,
            "amount": 2.5,
            "from_chain": "ethereum",
        },
        cfg=SimpleNamespace(deployment_mode="dev"),
    )
    assert env.amount_satoshi == int(to_satoshi(2.5))
    assert env.amount == pytest.approx(2.5)


def test_http_amount_abs_prod_refuses_float_only():
    from api.http import _http_amount_abs

    cfg = SimpleNamespace(deployment_mode="prod")
    with pytest.raises(ValueError, match="amount_satoshi required"):
        _http_amount_abs({"amount": 1.0}, cfg)


def test_http_amount_abs_prefers_satoshi():
    from api.http import _http_amount_abs

    cfg = SimpleNamespace(deployment_mode="dev")
    amt, sat = _http_amount_abs(
        {"amount": 99.0, "amount_satoshi": 2_500_000}, cfg
    )
    assert sat == 2_500_000
    assert amt == pytest.approx(2.5)


def test_save_bridge_lock_writes_amount_satoshi(tmp_path):
    from storage.database import Database
    from runtime.amount import to_satoshi

    db = Database(str(tmp_path / "bridge.db"))
    db.initialize()
    db.save_bridge_lock("0xfrom", "ethereum", "0xto", 5.0, "0xlock1")
    locks = db.get_bridge_locks()
    assert len(locks) == 1
    assert locks[0]["amount"] == 5.0
    assert locks[0]["amount_satoshi"] == int(to_satoshi(5.0))


def test_rust_bridge_estimate_fee_integer_bps():
    from bridge.abs_bridge import RustBridge

    class _FeeHost:
        BRIDGE_FEE_BPS = RustBridge.BRIDGE_FEE_BPS

    est = RustBridge.estimate_fee(_FeeHost(), "ethereum", 10.0)
    assert est["amount_satoshi"] == 10_000_000
    assert est["fee_satoshi"] == 100_000
    assert est["net_amount_satoshi"] == 9_900_000
    assert isinstance(est["fee_satoshi"], int)

