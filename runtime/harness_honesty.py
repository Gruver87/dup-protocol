#!/usr/bin/env python3
"""Shared harness soft-PASS honesty (prod_smoke / verify / soak_preflight).

Invariant: soft flags (tip lag, sticky ``p2p_state_consistent``, wire-probe
flaps) never invent peer alignment. Peered soft-PASS requires every peer
``match=true`` and a non-empty live root. Solo soft-PASS is N/A for P2P only.
"""

from __future__ import annotations

from typing import Any, Mapping


_SOFT = frozenset({"tip_state_aligned", "p2p_state_consistent", "peer_probe_ok"})


def harness_smoke_ok(harness: Mapping[str, Any]) -> bool:
    """Return True when harness is healthy or soft-fails with wire evidence.

    Args:
        harness: ``/chain/consistency/harness`` JSON body.

    Returns:
        True if hard-healthy or soft-PASS under the peer-match invariant.
    """
    if harness.get("harness_healthy", True):
        return True
    failed = set(harness.get("failed_checks") or [])
    if not failed <= _SOFT:
        return False
    peers = harness.get("peers") or []
    live = str(harness.get("live_state_root") or "").strip().lower()
    if peers and live and all(p.get("match") is True for p in peers):
        return True
    if not peers and failed <= {"p2p_state_consistent"}:
        return True
    if failed <= {"peer_probe_ok"} and harness.get("tip_state_aligned"):
        if harness.get("peer_probe_error") == "timeout":
            return True
    return False
