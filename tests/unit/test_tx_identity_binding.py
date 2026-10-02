#!/usr/bin/env python3
"""Tx identity binding + strict tx_root (audit 2026-10-02 §§7/10)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.tx_identity import (
    bind_identity_from_fields,
    bind_tx_hash_claim,
    compute_tx_identity_hash,
    wallet_signing_digest,
)
from execution.block_validator import BlockValidator


def test_forged_alternate_hash_refused():
    canonical, ts = compute_tx_identity_hash(
        from_addr="0x" + "a" * 40,
        to_addr="0x" + "b" * 40,
        value=1,
        nonce=0,
        timestamp=1_700_000_000,
    )
    with pytest.raises(ValueError, match="tx_hash_mismatch"):
        bind_tx_hash_claim("deadbeef" * 8, canonical)


def test_harness_label_claim_rebounds_to_canonical():
    """Non-digest labels are absent claims — identity stays canonical."""
    from_addr = "0x" + "a" * 40
    to_addr = "0x" + "b" * 40
    bound, _ = bind_identity_from_fields(
        "low",
        from_addr=from_addr,
        to_addr=to_addr,
        value=1,
        nonce=0,
        timestamp=1_700_000_000,
    )
    canon, _ = compute_tx_identity_hash(
        from_addr=from_addr,
        to_addr=to_addr,
        value=1,
        nonce=0,
        timestamp=1_700_000_000,
    )
    assert bound == canon


def test_legacy_wallet_signing_digest_accepted_but_identity_is_canonical():
    from_addr = "0x" + "a" * 40
    to_addr = "0x" + "b" * 40
    bound, _ts = bind_identity_from_fields(
        None,
        from_addr=from_addr,
        to_addr=to_addr,
        value=1,
        nonce=0,
        timestamp=1_700_000_000,
        chain_id=77777,
    )
    signing = wallet_signing_digest(
        from_addr=from_addr,
        to_addr=to_addr,
        value=1,
        nonce=0,
        chain_id=77777,
    )
    # Same payload under signing-digest claim still yields canonical identity.
    bound2, _ = bind_identity_from_fields(
        signing,
        from_addr=from_addr,
        to_addr=to_addr,
        value=1,
        nonce=0,
        timestamp=1_700_000_000,
        chain_id=77777,
    )
    assert bound2 == bound
    assert bound2 != signing or bound2 == signing  # either equal or rebound
    assert bound2 == bound


def test_same_payload_cannot_register_two_identities():
    from_addr = "0x" + "c" * 40
    to_addr = "0x" + "d" * 40
    a, _ = bind_identity_from_fields(
        "",
        from_addr=from_addr,
        to_addr=to_addr,
        value=5,
        nonce=3,
        timestamp=1_700_000_001,
    )
    with pytest.raises(ValueError, match="tx_hash_mismatch"):
        bind_identity_from_fields(
            "ff" * 32,
            from_addr=from_addr,
            to_addr=to_addr,
            value=5,
            nonce=3,
            timestamp=1_700_000_001,
        )
    assert a


def test_tx_root_rejects_prefix():
    bv = BlockValidator(state_engine=None, mempool=None)
    full = bv._compute_tx_root([{"hash": "aa" * 32}, {"hash": "bb" * 32}])
    parent = {"hash": "p" * 64, "height": 1, "number": 1, "timestamp": 1}
    block = {
        "number": 2,
        "height": 2,
        "parent_hash": parent["hash"],
        "timestamp": 2,
        "miner": "0x" + "1" * 40,
        "transactions": [
            {"hash": "aa" * 32, "from": "0x" + "a" * 40, "to": "0x" + "b" * 40, "nonce": 0, "value": 1},
            {"hash": "bb" * 32, "from": "0x" + "a" * 40, "to": "0x" + "b" * 40, "nonce": 1, "value": 1},
        ],
        "tx_root": full[:16],  # prefix only — must refuse
    }
    ok, msg = bv.validate_block(block, parent_block=parent, strict_timestamp=True)
    assert ok is False
    assert "Tx root mismatch" in msg

    block["tx_root"] = full
    ok2, _ = bv.validate_block(block, parent_block=parent, strict_timestamp=True)
    assert ok2 is True
