"""Multisig + validator stake prefer amount/stake_satoshi authority."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from features.multisig import MultiSigWallet
from runtime.amount import to_satoshi


def test_multisig_create_prefers_amount_satoshi():
    ms = MultiSigWallet(["0xowner"], 1)
    out = ms.create_transaction("0xrecv", 1.0, amount_satoshi=1_000_000)
    assert out["success"] is True
    assert out["amount_satoshi"] == 1_000_000
    bad = ms.create_transaction("0xrecv", 2.0, amount_satoshi=1_000_000)
    assert bad["success"] is False
    assert "mismatch" in str(bad.get("error", ""))


def test_save_validator_stake_satoshi(tmp_path):
    from storage.database import Database

    db = Database(str(tmp_path / "v.db"))
    db.save_validator("0x" + "ab" * 20, 32.0, stake_satoshi=int(to_satoshi(32)))
    rows = db.get_validators(active_only=False)
    assert rows
    assert int(rows[0]["stake_satoshi"]) == int(to_satoshi(32))
    with pytest.raises(ValueError, match="amount_satoshi_mismatch"):
        db.save_validator("0x" + "cd" * 20, 32.0, stake_satoshi=1)


def test_http_multisig_and_validator_needles():
    http = (ROOT / "api" / "http.py").read_text(encoding="utf-8")
    assert "amount_satoshi=int(value_sat)" in http
    assert "stake_satoshi=int(stake_sat)" in http
    assert "register_validator(address, int(stake_sat))" in http
