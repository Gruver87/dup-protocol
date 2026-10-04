"""Native apply / builder / slashing: satoshi twins, no invent defaults."""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def test_state_service_binds_amount_satoshi():
    src = (ROOT / "core" / "components" / "state_service.py").read_text(encoding="utf-8")
    assert "resolve_tx_value_satoshi" in src
    assert '"amount_satoshi"' in src
    assert "value_satoshi=" in src
    assert "_total_supply_satoshi" in src


def test_tx_builder_refuses_invent_gas():
    from core.tx_builder import TransactionBuilder

    with pytest.raises(ValueError, match="gas_price_required"):
        TransactionBuilder.create_transaction("0xa", "0xb", 1.0)
    with pytest.raises(ValueError, match="gas_limit_required"):
        TransactionBuilder.create_transaction("0xa", "0xb", 1.0, gas_price=1.0)
    tx = TransactionBuilder.create_transaction(
        "0xa", "0xb", 1.0, gas_price=1.0, gas_limit=21000
    )
    assert tx["gas"] == 21000
    assert int(tx["amount_satoshi"]) > 0


def test_block_builder_affordable_sat_needles():
    src = (ROOT / "execution" / "block_builder.py").read_text(encoding="utf-8")
    assert "_tx_affordable_sat" in src
    assert "amount_satoshi" in src
    assert "tx[\"gasPrice\"] * tx[\"gas\"]" not in src


def test_slashing_register_refuses_zero_stake():
    from consensus.slashing import SlashingEngine

    se = SlashingEngine()
    with pytest.raises(ValueError, match="stake_required"):
        se.register_validator("0xval", 0)
    se.register_validator("0xval", 1_000_000)
    assert se._stakes["0xval"] == 1_000_000
