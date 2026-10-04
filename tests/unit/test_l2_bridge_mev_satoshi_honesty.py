"""Lightning/Plasma amount_satoshi thread + MEV/multisig honesty paint."""

from __future__ import annotations

import os
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime.amount import to_satoshi


def test_lightning_open_pay_prefer_capacity_satoshi():
    from features.lightning import LightningNetwork
    from storage.database import Database

    tmp = tempfile.mkdtemp()
    db = Database(os.path.join(tmp, "ln.db"))
    db.initialize()
    alice = "0x" + "a" * 40
    bob = "0x" + "b" * 40
    db.set_balance(alice, 100.0)

    ln = LightningNetwork(node_address=alice, db=db)
    cap_sat = int(to_satoshi(15.0))
    cid = ln.open_channel(bob, 15.0, capacity_satoshi=cap_sat)
    assert cid
    assert int(to_satoshi(ln.channels[cid].capacity)) == cap_sat

    pay_sat = int(to_satoshi(3.0))
    pid = ln.send_payment(cid, bob, 3.0, amount_satoshi=pay_sat)
    assert pid
    assert db.get_balance_satoshi(alice) == int(to_satoshi(100.0)) - cap_sat


def test_lightning_htlc_amount_satoshi_mismatch_refuses():
    from features.l2_crypto import payment_hash
    from features.lightning import LightningNetwork
    from storage.database import Database

    tmp = tempfile.mkdtemp()
    db = Database(os.path.join(tmp, "htlc.db"))
    db.initialize()
    alice = "0x" + "c" * 40
    bob = "0x" + "d" * 40
    db.set_balance(alice, 50.0)
    ln = LightningNetwork(node_address=alice, db=db)
    cid = ln.open_channel(bob, capacity=10.0, capacity_satoshi=int(to_satoshi(10.0)))
    assert cid
    ph = payment_hash("secret")
    assert (
        ln.add_htlc(
            cid,
            bob,
            2.0,
            ph,
            expiry=int(time.time()) + 60,
            amount_satoshi=int(to_satoshi(3.0)),
        )
        is None
    )


def test_plasma_deposit_exit_amount_satoshi_authority():
    from features.plasma import PlasmaChain
    from storage.database import Database

    tmp = tempfile.mkdtemp()
    db = Database(os.path.join(tmp, "pl.db"))
    db.initialize()
    user = "0x" + "1" * 40
    db.set_balance(user, 100.0)
    pl = PlasmaChain(chain_id="sat", db=db)
    amt_sat = int(to_satoshi(12.5))
    did = pl.deposit(user, 12.5, amount_satoshi=amt_sat)
    assert did
    dep = pl.deposits[did]
    assert dep["amount_satoshi"] == amt_sat
    assert db.get_balance_satoshi(user) == int(to_satoshi(100.0)) - amt_sat

    eid = pl.request_exit(did, user)
    assert eid
    assert pl.exit_requests[eid]["amount_satoshi"] == amt_sat
    assert pl.finalize_exit(eid, force=True)
    assert db.get_balance_satoshi(user) == int(to_satoshi(100.0))


def test_bridge_enqueue_l1_incoming_carries_amount_satoshi(tmp_path):
    from bridge.abs_bridge import RustBridge
    from bridge.l1_rpc import load_l1_queue
    from types import SimpleNamespace

    queue_path = tmp_path / "bridge_l1_queue.json"
    cfg = SimpleNamespace(
        bridge_l1_queue_path=str(queue_path),
        bridge_mode="simulator",
        bridge_fee_rate=0.0,
        min_bridge_amount=0.0,
        max_bridge_amount=1_000_000.0,
    )
    br = object.__new__(RustBridge)
    br.config = cfg
    sat = int(to_satoshi(7.0))
    RustBridge.enqueue_l1_incoming(
        br,
        "0xabc",
        "0x" + "e" * 40,
        7.0,
        "ethereum",
        amount_satoshi=sat,
    )
    q = load_l1_queue(str(queue_path))
    incoming = q.get("incoming") or []
    assert incoming
    assert incoming[0]["amount_satoshi"] == sat


def test_mev_statistics_simulation_only():
    from features.mev_analyzer import MEVAnalyzer

    stats = MEVAnalyzer().get_statistics()
    assert stats["simulation_only"] is True
    assert stats["consensus_wired"] is False
    assert stats["executed"] is False


def test_source_needles_l2_http_passes_satoshi():
    http_src = (ROOT / "api" / "http.py").read_text(encoding="utf-8")
    assert "capacity_satoshi=int(capacity_sat)" in http_src
    assert "amount_satoshi=int(amount_sat)" in http_src
    assert "mev_simulation_only" in http_src
    assert "execution_bound\": False" in http_src or "execution_bound': False" in http_src
    ln_src = (ROOT / "features" / "lightning.py").read_text(encoding="utf-8")
    assert "amount_satoshi: int | None = None" in ln_src
    pl_src = (ROOT / "features" / "plasma.py").read_text(encoding="utf-8")
    assert "amount_satoshi: int | None = None" in pl_src
