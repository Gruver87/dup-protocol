"""Rocks tx/receipt persist dual-writes satoshi (Exp→pin)."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_rocks_insert_tx_uses_tx_money_satoshi():
    src = (ROOT / "storage" / "rocks_store.py").read_text(encoding="utf-8")
    chunk = src.split("def _insert_transaction")[1].split("def _insert_tx_indexes")[0]
    assert "tx_money_satoshi" in chunk
    assert "value_satoshi" in chunk
    assert 'tx.get("value", tx.get("amount", 0.0))' not in chunk


def test_rocks_receipt_and_metrics_honesty():
    src = (ROOT / "storage" / "rocks_store.py").read_text(encoding="utf-8")
    rcpt = src.split("def _insert_tx_receipt")[1].split("def save_transaction")[0]
    assert "fee_satoshi" in rcpt
    assert '"receipts_enabled": True' not in src
    assert 'startswith("rocks")' in src


def test_tx_money_satoshi_prefers_explicit_twin():
    from runtime.amount import tx_money_satoshi

    sat = tx_money_satoshi({"value": 1.5, "value_satoshi": 42, "fee": 0.1})
    assert sat["value_satoshi"] == 42
    assert sat["fee_satoshi"] > 0
