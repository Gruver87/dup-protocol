"""Writeback must refuse underfunded transfer_value (no clamp-to-zero mint)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from crypto import native


def test_apply_transfer_insufficient_does_not_mint():
    accounts = {
        "0xfrom": {"address": "0xfrom", "balance_satoshi": 0, "balance": 0.0},
        "0xto": {"address": "0xto", "balance_satoshi": 0, "balance": 0.0},
    }
    ops = [{"op": "transfer_value", "from": "0xfrom", "to": "0xto", "value_wei": 10**18}]
    try:
        native.evm_apply_writeback_ops(accounts, ops)
        raise AssertionError("expected insufficient_writeback_value")
    except ValueError as exc:
        assert "insufficient_writeback_value" in str(exc)
    assert int(accounts["0xfrom"]["balance_satoshi"]) == 0
    assert int(accounts["0xto"]["balance_satoshi"]) == 0


def test_python_fallback_transfer_insufficient_does_not_mint():
    accounts = {"0xa": {"balance_satoshi": 0, "storage": "{}"}}
    ops = [{"op": "transfer_value", "from": "0xa", "to": "0xb", "value_wei": 10**18}]
    try:
        native._evm_apply_writeback_ops_py(accounts, ops)
        raise AssertionError("expected insufficient_writeback_value")
    except ValueError as exc:
        assert "insufficient_writeback_value" in str(exc)
    assert int(accounts["0xa"]["balance_satoshi"]) == 0


def test_bridge_pending_writeback_fails_closed():
    from execution.evm_adapter import EVMAdapter

    class _BadBS:
        def pop(self, *_a, **_k):
            raise TypeError("corrupt pending_writeback_ops")

    class _Ctx:
        def get(self, key, default=None):
            if key == "bridge_state":
                return _BadBS()
            return default

    adapter = EVMAdapter.__new__(EVMAdapter)
    try:
        adapter._take_bridge_pending_writeback(_Ctx())
        raise AssertionError("expected bridge_pending_writeback_failed")
    except RuntimeError as exc:
        assert "bridge_pending_writeback_failed" in str(exc)


def test_account_blob_require_mode_needle():
    src = (ROOT / "crypto" / "native.py").read_text(encoding="utf-8")
    chunk = src.split("def _account_blob_to_row")[1].split("\ndef ")[0]
    assert 'resolve_native_mode() == "require"' in chunk
    assert "account_blob_to_json failed under require" in chunk
