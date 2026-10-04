"""Fund-demo max-prep honesty needles (pin merge from Exp)."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_bridge2_fee_no_invent_amount_100():
    src = (ROOT / "api" / "http.py").read_text(encoding="utf-8")
    chunk = src.split('path == "/bridge2/fee"')[1].split("elif path")[0]
    assert '["100"]' not in chunk
    assert "no invent amount=100" in chunk


def test_pool_spend_sat_admit_no_invent_21000():
    src = (ROOT / "api" / "http.py").read_text(encoding="utf-8")
    chunk = src.split("def _handle_devnet_pool_spend")[1].split("\ndef ")[0]
    assert "is_outgoing_allowed_sat" in chunk
    assert "record_outgoing_sat" in chunk
    assert '"gas": 21_000' not in chunk
    assert '"gas": 21000' not in chunk
    assert '"gas_used": 21_000' not in chunk
    assert '"gas_used": 21000' not in chunk
    assert '"amount_satoshi": amount_sat' in chunk
    assert '"gas": 1' in chunk


def test_auto_sign_passes_amount_satoshi():
    src = (ROOT / "api" / "http.py").read_text(encoding="utf-8")
    chunk = src.split("def _handle_send_tx_with_wallet")[1].split("\ndef ")[0]
    assert "amount_satoshi=int(_amount_sat)" in chunk


def test_wasm_nonzero_value_refused_needle():
    src = (ROOT / "api" / "http.py").read_text(encoding="utf-8")
    chunk = src.split('path == "/wasm/call"')[1].split("elif path")[0]
    assert "wasm call value not L1-bound" in chunk
    assert "l1_value_applied" in chunk


def test_status_l2_execution_bound_needles():
    src = (ROOT / "api" / "http.py").read_text(encoding="utf-8")
    assert "lightning_execution_bound" in src
    assert "plasma_execution_bound" in src
    assert "crypto_will_execution_bound" in src


def test_fund_demo_operator_pack_exists():
    path = ROOT / "docs" / "FUND_DEMO_OPERATOR_PACK.md"
    text = path.read_text(encoding="utf-8")
    assert "Not:** public audited mainnet" in text or "Not: public audited mainnet" in text
    assert "dup-protocol" in text
    assert "TCP+TLS" in text
