"""Bridge lock must refuse when burn credit fails after debit."""

from types import SimpleNamespace
from unittest.mock import MagicMock

from bridge.abs_bridge import RustBridge


def test_lock_requires_debit_and_burn_both_succeed(monkeypatch):
    calls = []

    def _delta(db, addr, delta, allow_float_fallback=False):
        calls.append((addr, int(delta), allow_float_fallback))
        # Debit ok, burn credit fails.
        return int(delta) < 0

    monkeypatch.setattr(
        "runtime.amount.apply_store_delta_satoshi",
        _delta,
    )

    class _Db:
        def get_balance_satoshi(self, _addr):
            return 10_000_000_000  # 100 ABS

        def save_bridge_lock(self, *args, **kwargs):
            raise AssertionError("must not persist lock when burn credit fails")

    cfg = SimpleNamespace(
        burn_address="0x" + "d" * 40,
        burn_rate=0.5,
        bridge_mode="simulator",
        bridge_enabled=False,
        bridge_require_l1_event=False,
        deployment_mode="dev",
        chain_id=778888,
    )
    br = RustBridge.__new__(RustBridge)
    br.config = cfg
    br.db = _Db()
    br.bus = None
    br._mode = "simulator"
    br._is_prod = False
    br._simulator = MagicMock()
    br._simulator.bridge.return_value = "0x" + "c" * 64
    br._enqueue_l1_outbound = MagicMock()

    out = br.lock_and_bridge(
        "0x" + "a" * 40,
        "ethereum",
        "0x" + "b" * 40,
        1.0,
    )
    assert out.get("error") == "satoshi_store_required"
    assert any(c[1] < 0 for c in calls)
    assert any(c[1] > 0 for c in calls)
