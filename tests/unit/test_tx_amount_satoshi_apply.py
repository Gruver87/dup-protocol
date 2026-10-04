"""Transaction.amount_satoshi is apply money authority when present."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.blockchain import Transaction
from runtime.amount import plan_transfer_fees_sat, resolve_tx_value_satoshi, to_satoshi


def test_resolve_tx_value_prefers_amount_satoshi():
    tx = Transaction(
        "0xa",
        "0xb",
        value=1.0,
        nonce=0,
        gas=21000,
        amount_satoshi=1_000_000,
    )
    assert resolve_tx_value_satoshi(tx) == 1_000_000
    # Float-only fallback when twin absent.
    tx2 = Transaction("0xa", "0xb", value=2.0, nonce=0, gas=21000)
    assert resolve_tx_value_satoshi(tx2) == int(to_satoshi(2.0))


def test_transaction_init_refuses_value_satoshi_mismatch():
    with pytest.raises(ValueError, match="value_satoshi_mismatch"):
        Transaction(
            "0xa",
            "0xb",
            value=99.0,
            nonce=0,
            gas=21000,
            amount_satoshi=1_000_000,
        )


def test_from_dict_binds_amount_satoshi():
    tx = Transaction.from_dict(
        {
            "from": "0xa",
            "to": "0xb",
            "value": 1.0,
            "amount_satoshi": 1_000_000,
            "nonce": 0,
            "gas": 21000,
        }
    )
    assert tx.amount_satoshi == 1_000_000
    assert tx.value == pytest.approx(1.0)


def test_from_dict_mismatch_refused():
    with pytest.raises(ValueError, match="value_satoshi_mismatch"):
        Transaction.from_dict(
            {
                "from": "0xa",
                "to": "0xb",
                "value": 2.0,
                "amount_satoshi": 1_000_000,
                "nonce": 0,
                "gas": 21000,
            }
        )


def test_plan_transfer_fees_sat_value_satoshi_override():
    plan = plan_transfer_fees_sat(21000, 0.0000001, 0.5, value=9.0, value_satoshi=500_000)
    assert plan["value_sat"] == 500_000
    assert plan["total_cost_sat"] == 500_000 + plan["fee_sat"]


def test_to_dict_emits_amount_satoshi():
    tx = Transaction("0xa", "0xb", 1.0, nonce=0, gas=21000, amount_satoshi=int(to_satoshi(1)))
    d = tx.to_dict()
    assert d["amount_satoshi"] == 1_000_000
    assert d["value_satoshi"] == 1_000_000


def test_state_service_native_json_binds_amount_satoshi():
    """Native simple-block / host_effects JSON must carry amount_satoshi authority."""
    src = (ROOT / "core" / "components" / "state_service.py").read_text(encoding="utf-8")
    assert '"amount_satoshi": value_sat' in src or '"amount_satoshi": int(resolve_tx_value_satoshi(tx))' in src
    assert "value_satoshi=resolve_tx_value_satoshi(tx)" in src
    assert "value_satoshi=value_sat" in src
    # Must not leave native apply path as float-only authority.
    assert 'txs.append(' in src
    native_fn = src.split("def _apply_simple_block_native")[1].split("def ")[0]
    assert "amount_satoshi" in native_fn
    assert "resolve_tx_value_satoshi" in native_fn


def test_evm_adapter_resolves_amount_satoshi_over_float():
    from execution.evm_adapter import EVMAdapter

    class _DB:
        def get_balance_satoshi(self, _addr):
            return 10_000_000

    class _Cfg:
        evm_gas_limit = 100_000

    evm = EVMAdapter(_DB(), _Cfg())
    assert evm._resolve_call_value_sat(99.0, amount_satoshi=500_000) == 500_000
    assert evm._resolve_call_value_sat(1.0, amount_satoshi=None) == int(to_satoshi(1.0))


def test_block_validator_prefers_amount_satoshi():
    from execution.block_validator import BlockValidator

    ok, _ = BlockValidator(None, None)._validate_transaction_shape(
        {
            "hash": "0x1",
            "from": "0xa",
            "to": "0xb",
            "nonce": 0,
            "value": 0.5,
            "amount_satoshi": 500_000,
        }
    )
    assert ok is True


def test_tx_validator_refuses_value_satoshi_mismatch():
    from blockchain.tx_validator import TransactionValidator

    class _SM:
        def get_account(self, _a):
            return type("A", (), {"nonce": 0})()

        def get_balance_satoshi(self, _a):
            return 10_000_000

    ok, reason = TransactionValidator.validate(
        {
            "from": "0x" + "a" * 40,
            "to": "0x" + "b" * 40,
            "value": 2.0,
            "amount_satoshi": 1_000_000,
            "nonce": 0,
            "gas": 21000,
            "fee": 0.001,
            "fee_satoshi": 1000,
            "hash": "0x1",
        },
        _SM(),
        require_signature=False,
    )
    assert ok is False
    assert reason == "value_satoshi_mismatch"
