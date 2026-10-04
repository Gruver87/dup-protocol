"""ADR 0021 wire money — amount_satoshi / fee_satoshi resolve (pin HTTP/P2P helpers)."""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from blockchain.mempool import MempoolTransaction
from blockchain.mempool_wire import (
    WireMoneyMismatch,
    WireMoneyMissing,
    mempool_tx_to_wire,
    resolve_wire_amount_sat,
    resolve_wire_fee_sat,
)
from runtime.amount import from_satoshi_float, to_satoshi


def test_mempool_tx_to_wire_emits_satoshi_canonical():
    amount_sat = int(to_satoshi(3.5))
    fee_sat = int(to_satoshi(0.01))
    tx = MempoolTransaction(
        tx_hash="0xwire1",
        from_addr="0x" + "1" * 40,
        to_addr="0x" + "2" * 40,
        amount=3.5,
        fee=0.01,
        amount_satoshi=amount_sat,
        fee_satoshi=fee_sat,
        nonce=0,
        signature="0xsig",
        public_key="0xpub",
        data="0x",
        gas=21000,
    )
    wire = mempool_tx_to_wire(tx)
    assert wire["amount_satoshi"] == amount_sat
    assert wire["fee_satoshi"] == fee_sat
    assert wire["amount"] == from_satoshi_float(amount_sat)
    assert wire["fee"] == from_satoshi_float(fee_sat)
    assert wire["value"] == wire["amount"]


def test_resolve_prefer_satoshi_matching_dual_write():
    amount_sat = 1_500_000
    fee_sat = 2_000
    a_sat, a_abs = resolve_wire_amount_sat(
        {"amount_satoshi": amount_sat, "value": from_satoshi_float(amount_sat)}
    )
    assert a_sat == amount_sat
    assert a_abs == from_satoshi_float(amount_sat)
    f_sat, f_abs = resolve_wire_fee_sat(
        {"fee_satoshi": fee_sat, "fee": from_satoshi_float(fee_sat)}
    )
    assert f_sat == fee_sat
    assert f_abs == from_satoshi_float(fee_sat)


def test_resolve_mismatch_amount_raises():
    try:
        resolve_wire_amount_sat({"amount_satoshi": 1000, "value": 2.0})
        assert False, "expected WireMoneyMismatch"
    except WireMoneyMismatch as exc:
        assert "value_satoshi_mismatch" in str(exc)


def test_resolve_float_only_raises_when_required():
    try:
        resolve_wire_amount_sat({"value": 1.0}, require_satoshi=True)
        assert False, "expected WireMoneyMissing"
    except WireMoneyMissing as exc:
        assert "amount_satoshi_required" in str(exc)


def test_resolve_float_only_ok_when_not_required():
    a_sat, _ = resolve_wire_amount_sat({"value": 1.25}, require_satoshi=False)
    assert a_sat == int(to_satoshi(1.25))


def test_send_tx_obj_prod_refuses_float_only():
    from api.http import _handle_send_tx_obj

    cfg = SimpleNamespace(
        deployment_mode="prod",
        is_production=True,
        chain_id=778888,
        base_gas_price=21000,
        gas_price_wei=1,
        node_id="t",
        require_signatures=False,
    )
    try:
        _handle_send_tx_obj(
            {
                "from": "0x" + "1" * 40,
                "to": "0x" + "2" * 40,
                "value": 1.0,
                "nonce": 0,
                "gas": 21000,
            },
            None,
            None,
            cfg,
        )
        assert False, "expected amount_satoshi_required"
    except ValueError as exc:
        assert "amount_satoshi_required" in str(exc)
