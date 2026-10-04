"""Faucet / pool-spend use integer satoshi store, not float update_balance."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def test_faucet_uses_apply_store_delta_satoshi():
    src = (ROOT / "api" / "http.py").read_text(encoding="utf-8")
    chunk = src.split('path == "/devnet/faucet"')[1].split("elif path")[0]
    assert "apply_store_delta_satoshi" in chunk
    assert "allow_float_fallback=False" in chunk
    assert "credited_satoshi" in chunk
    assert "balance_satoshi" in chunk
    assert "db.update_balance(address, amount)" not in chunk


def test_pool_spend_sat_admit_no_invent_21000():
    src = (ROOT / "api" / "http.py").read_text(encoding="utf-8")
    chunk = src.split("def _handle_devnet_pool_spend")[1].split("\ndef ")[0]
    assert "is_outgoing_allowed_sat" in chunk
    assert "record_outgoing_sat" in chunk
    assert "apply_store_delta_satoshi" in chunk
    assert '"gas": 21_000' not in chunk
    assert '"gas": 21000' not in chunk
    assert '"gas_used": 21_000' not in chunk
    assert '"gas_used": 21000' not in chunk
    assert '"amount_satoshi": amount_sat' in chunk
    assert '"gas": 1' in chunk


def test_pool_locks_satoshi_needles():
    src = (ROOT / "runtime" / "pool_locks.py").read_text(encoding="utf-8")
    assert "def is_outgoing_allowed_sat" in src
    assert "def record_outgoing_sat" in src
    assert "def spendable_balance_sat" in src
    assert "spent_satoshi" in src


def test_slashing_add_validator_no_invent_stake_32():
    src = (ROOT / "api" / "http.py").read_text(encoding="utf-8")
    chunk = src.split('path == "/slashing/add-validator"')[1].split("elif path")[0]
    assert "_http_stake_abs" in chunk
    assert 'stake", 32.0)' not in chunk
    assert "stake_satoshi" in chunk
