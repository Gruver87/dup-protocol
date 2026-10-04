"""Bridge adapter always binds amount_satoshi before credit."""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bridge.adapter import RustBridgeAdapter
from bridge.ports import InboundEnvelope, InboundStatus
from bridge.validators import PassthroughInboundValidator
from runtime.amount import to_satoshi


class _Inner:
    def __init__(self):
        self.calls = []
        self.db = SimpleNamespace()  # satisfy BridgeStoreAdapter path if used

    def confirm_incoming(self, abs_tx, to_addr, amount, from_chain, **kw):
        self.calls.append(
            {
                "abs_tx": abs_tx,
                "to_addr": to_addr,
                "amount": amount,
                "from_chain": from_chain,
                **kw,
            }
        )
        return {"confirmed": True, "tx_hash": abs_tx}


def _adapter(inner=None):
    inner = inner or _Inner()
    return RustBridgeAdapter(
        inner,
        validator=PassthroughInboundValidator(),
        store=SimpleNamespace(),  # skip BridgeStoreAdapter(None)
    )


def test_coerce_legacy_positional_binds_satoshi():
    inner = _Inner()
    br = _adapter(inner)
    res = br.confirm_incoming("0xtx", "0xrecv", 3.0, "ethereum")
    assert res.ok
    assert inner.calls
    assert inner.calls[0]["amount"] == 3.0
    assert inner.calls[0]["amount_satoshi"] == int(to_satoshi(3.0))


def test_lock_and_bridge_passes_amount_satoshi():
    inner = _Inner()

    def _lock(from_addr, to_chain, to_addr, amount, **kw):
        inner.calls.append(
            {"from": from_addr, "amount": amount, **kw}
        )
        return {"tx_hash": "0xlock", "status": "pending"}

    inner.lock_and_bridge = _lock
    br = _adapter(inner)
    res = br.lock_and_bridge(
        "0xa", "ethereum", "0xb", 1.0, amount_satoshi=1_000_000
    )
    assert res.ok or res.detail.get("tx_hash") == "0xlock" or inner.calls
    assert inner.calls[-1]["amount_satoshi"] == 1_000_000


def test_coerce_envelope_object_without_satoshi_backfills():
    env = InboundEnvelope(
        from_chain="ethereum",
        to_addr="0xrecv",
        amount=2.0,
        event_tx_hash="0xev",
        amount_satoshi=None,
    )
    coerced = RustBridgeAdapter._coerce_envelope(env)
    assert coerced.amount_satoshi == int(to_satoshi(2.0))


def test_confirm_rejects_when_coerce_fails():
    inner = _Inner()
    br = _adapter(inner)
    res = br.confirm_incoming("0xtx", "0xrecv", "not-a-number", "ethereum")
    assert not res.ok
    assert res.status == InboundStatus.REJECTED.value
    assert not inner.calls
