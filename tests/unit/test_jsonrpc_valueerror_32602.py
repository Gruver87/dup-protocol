"""Legacy JSON-RPC dispatcher maps ValueError to -32602 (invalid params)."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

from api.http import JSONRPCHandler


def test_dispatch_value_error_is_invalid_params():
    handler = JSONRPCHandler.__new__(JSONRPCHandler)
    handler.__class__.rpc_port = None
    handler._call = MagicMock(side_effect=ValueError("bad_param"))  # type: ignore[method-assign]
    out = JSONRPCHandler._dispatch(handler, {"jsonrpc": "2.0", "id": 7, "method": "x", "params": []})
    assert out["id"] == 7
    assert out["error"]["code"] == -32602
    assert "bad_param" in out["error"]["message"]


def test_dispatch_other_error_is_internal():
    handler = JSONRPCHandler.__new__(JSONRPCHandler)
    handler.__class__.rpc_port = None
    handler._call = MagicMock(side_effect=RuntimeError("boom"))  # type: ignore[method-assign]
    out = JSONRPCHandler._dispatch(handler, {"jsonrpc": "2.0", "id": 1, "method": "x", "params": []})
    assert out["error"]["code"] == -32603


def test_tx_validator_typeerror_gas_is_gas_required():
    from blockchain.tx_validator import TransactionValidator

    ok, reason = TransactionValidator.validate(
        {
            "from": "0x" + "a" * 40,
            "to": "0x" + "b" * 40,
            "amount": 1,
            "fee": 0.001,
            "nonce": 0,
            "gas": object(),  # int() raises TypeError
        },
        state_manager=SimpleNamespace(),
        require_signature=False,
    )
    assert ok is False
    assert reason == "gas_required"
