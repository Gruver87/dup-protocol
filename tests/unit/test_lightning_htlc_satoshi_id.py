"""Lightning HTLC/payment identity must bind integer satoshi, not float ABS."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

ROOT = Path(__file__).resolve().parents[2]


def test_lightning_source_binds_amt_sat_in_ids():
    src = (ROOT / "features" / "lightning.py").read_text(encoding="utf-8")
    assert "{preimage_hash}{amt_sat}" in src or "{preimage_hash}{amt_sat}{" in src
    assert "{to_node}{amt_sat}" in src or "{to_node}{amt_sat}{" in src
    # Must not hash float display amount for HTLC id after resolve.
    add = src.split("def add_htlc")[1].split("def settle_htlc")[0]
    assert "{preimage_hash}{amount}" not in add
    assert "from_satoshi_float(amt_sat)" in add


def test_add_htlc_amount_is_satoshi_quantized():
    from features.lightning import LightningNetwork

    ln = LightningNetwork(db=None, node_address="0x" + "a" * 40)
    # Minimal open channel between node and peer.
    peer = "0x" + "b" * 40
    ch = MagicMock()
    ch.status = "open"
    ch.node1 = ln.node_address
    ch.node2 = peer
    ch.balance1 = 10.0
    ch.balance2 = 10.0
    ch.fee_rate = 0.0
    ch.state_version = 0
    ln.channels["ch1"] = ch
    ln._persist_channel = MagicMock()  # type: ignore[method-assign]
    ln._persist_htlc = MagicMock()  # type: ignore[method-assign]
    ln._persist_state = MagicMock()  # type: ignore[method-assign]

    hid = ln.add_htlc(
        "ch1",
        peer,
        amount=1.0,
        preimage_hash="ab" * 32,
        amount_satoshi=1_000_000,
    )
    assert hid
    htlc = ln.htlcs[hid]
    assert htlc.amount == 1.0
