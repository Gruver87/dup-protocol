#!/usr/bin/env python3
"""Tests for runtime.amount satoshi helpers."""

from decimal import Decimal

from runtime.amount import ABS_DECIMALS, SATOSHI_MULTIPLIER, from_satoshi, to_satoshi


def test_to_satoshi_junk_is_value_error_not_native_fallback():
    from runtime.amount import to_satoshi
    import pytest

    with pytest.raises(ValueError):
        to_satoshi("not-a-number")


def test_satoshi_round_trip_whole_abs():
    assert to_satoshi(1) == SATOSHI_MULTIPLIER
    assert from_satoshi(SATOSHI_MULTIPLIER) == Decimal("1")
    assert ABS_DECIMALS == 6


def test_to_satoshi_floors_dust():
    # 0.0000001 ABS -> 0 satoshi
    assert to_satoshi("0.0000001") == 0
    assert to_satoshi("1.9999999") == 1_999_999


def test_money_abs_refuses_bool_and_quantizes():
    from runtime.amount import money_abs
    import pytest

    assert money_abs(7.5) == 7.5
    assert money_abs("32") == 32.0
    with pytest.raises(TypeError, match="bool is not an amount"):
        money_abs(True)


def test_apply_delta_and_account_helpers():
    from runtime.amount import account_balance_abs, apply_delta_satoshi, dual_write_balance

    assert apply_delta_satoshi(1_000_000, -0.25) == 750_000
    row: dict = {}
    dual_write_balance(row, 2)
    assert account_balance_abs(row) == 2.0


def test_immutable_state_uses_shared_multiplier():
    from blockchain.immutable_state import SATOSHI_MULTIPLIER as ims_mult
    from runtime.amount import SATOSHI_MULTIPLIER as amt_mult

    assert ims_mult == amt_mult


def test_resolve_amount_satoshi_prefers_and_mismatch():
    from runtime.amount import resolve_amount_satoshi
    import pytest

    sat, abs_v = resolve_amount_satoshi(1.0, 1_000_000)
    assert sat == 1_000_000
    assert abs_v == 1.0
    assert resolve_amount_satoshi(None, 500_000)[0] == 500_000
    with pytest.raises(ValueError, match="amount_satoshi_mismatch"):
        resolve_amount_satoshi(2.0, 1_000_000)


def test_plan_transfer_fees_sat_is_integer_only():
    from runtime.amount import can_afford_transfer_sat, plan_transfer_fees_sat

    # 21000 * 1e-7 ABS = 0.0021 ABS = 2100 satoshi
    plan = plan_transfer_fees_sat(21000, 0.0000001, 0.5, 1.0)
    assert plan["fee_sat"] == 2100
    assert plan["burned_sat"] == 1050
    assert plan["miner_fee_sat"] == 1050
    assert plan["value_sat"] == 1_000_000
    assert plan["total_cost_sat"] == 1_002_100
    assert all(isinstance(v, int) for v in plan.values())
    assert can_afford_transfer_sat(1_002_100, plan["total_cost_sat"])
    assert not can_afford_transfer_sat(1_002_099, plan["total_cost_sat"])


def test_tx_money_abs_quantizes_and_refuses_bool():
    from runtime.amount import tx_money_abs
    import pytest

    money = tx_money_abs({"value": 7.5000003, "fee": 0.1, "burned": 0.02})
    assert money["value"] == 7.5
    assert money["fee"] == 0.1
    assert money["burned"] == 0.02
    money_amt = tx_money_abs({"amount": 42.5})
    assert money_amt["value"] == 42.5
    with pytest.raises(TypeError):
        tx_money_abs({"value": True})


def test_writeback_balance_abs_prefers_satoshi_and_refuses_bool():
    from runtime.amount import writeback_balance_abs
    import pytest

    assert writeback_balance_abs({"balance": 99.9, "balance_satoshi": 1_000_000}) == 1.0
    assert writeback_balance_abs({"balance": 7.5}) == 7.5
    assert writeback_balance_abs({"balance": 7.5000003}) == 7.5
    with pytest.raises(TypeError):
        writeback_balance_abs({"balance": True})


def test_save_validator_persists_stake_satoshi(tmp_path):
    from storage.database import Database

    db = Database(str(tmp_path / "stake.db"))
    db.save_validator("0xabc", 32.0, stake_satoshi=32_000_000)
    rows = db.get_validators(active_only=False)
    assert len(rows) == 1
    assert rows[0]["stake_satoshi"] == 32_000_000
    assert rows[0]["stake"] == 32.0


def test_feature_crypto_will_default_off():
    from runtime.config import Config

    cfg = Config()
    assert cfg.feature_crypto_will is False
    assert cfg.feature_nft is False
    assert cfg.feature_libp2p is False
    assert cfg.feature_long_range is False
