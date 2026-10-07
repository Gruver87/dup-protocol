"""PBS/MEV fee paths must use abs_to_wei (not fee*1e9 float invent)."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_main_pbs_mev_uses_abs_to_wei_not_float_gwei():
    src = (ROOT / "main.py").read_text(encoding="utf-8")
    chunk = src.split("PBS fee-bid simulation")[1].split(
        "MempoolTransaction → Transaction"
    )[0]
    assert "abs_to_wei" in chunk
    assert "get_for_block" in chunk
    assert "* 1e9" not in chunk
    assert "fee * 1e9" not in chunk


def test_main_genesis_alloc_refuses_bool_amount():
    src = (ROOT / "main.py").read_text(encoding="utf-8")
    assert 'isinstance(amount, bool)' in src
    assert 'bool is not an amount' in src
    # Bound to the DB genesis alloc loop (not IMS seed).
    chunk = src.split("for addr, amount in alloc.items():")[1].split(
        "self.db.set_meta(\"genesis_alloc_applied\""
    )[0]
    assert 'isinstance(amount, bool)' in chunk


def test_http_contract_value_parse_abs_int():
    src = (ROOT / "api" / "http.py").read_text(encoding="utf-8")
    assert "parse_abs_int(body.get(\"value\", 0), field=\"value\")" in src
    assert "find_route(" in src
    assert "amount_satoshi=int(_amount_sat)" in src
