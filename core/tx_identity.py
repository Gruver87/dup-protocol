#!/usr/bin/env python3
"""Canonical tx identity hash binding (audit 2026-10-02 §7).

Client-supplied ``hash`` must never become an alternate mempool/chain identity.
Identity is always ``native.transaction_hash(...)``. A claim may be omitted,
equal the canonical identity, or equal the legacy wallet signing digest.
Any other claim is refused (``tx_hash_mismatch``).
"""
from __future__ import annotations

import json
import time
from typing import Any, Mapping, Optional


def compute_tx_identity_hash(
    *,
    from_addr: str,
    to_addr: str,
    value: Any,
    nonce: int,
    gas: int = 21_000,
    data: str = "",
    timestamp: int = 0,
) -> tuple[str, int]:
    """Return ``(canonical_hash, timestamp_used)``."""
    from crypto import native

    ts = int(timestamp or 0)
    if ts <= 0:
        ts = int(time.time())
    digest = native.transaction_hash(
        str(from_addr or ""),
        str(to_addr or ""),
        value,
        int(nonce or 0),
        int(gas or 21_000),
        str(data or ""),
        int(ts),
    )
    return str(digest), int(ts)


def wallet_signing_digest(
    *,
    from_addr: str,
    to_addr: str,
    value: Any,
    nonce: int,
    chain_id: int = 1,
    gas: int = 21_000,
    data: str = "",
) -> str:
    """Legacy Wallet.sign_transaction digest (not chain identity)."""
    from crypto import native
    from crypto.wallet import Wallet

    payload = Wallet._canonical_tx_for_hash(
        {
            "from": from_addr,
            "to": to_addr,
            "value": value,
            "nonce": int(nonce or 0),
            "chain_id": int(chain_id or 1),
            "data": data or "",
            "gas_limit": int(gas or 21_000),
        }
    )
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return str(native.hash_sorted_json(encoded))


def _looks_like_digest(claim: str) -> bool:
    """True when claim is a 64-hex digest (real client hash), not a harness label."""
    c = str(claim or "").strip().lower()
    if c.startswith("0x"):
        c = c[2:]
    return len(c) == 64 and all(ch in "0123456789abcdef" for ch in c)


def bind_tx_hash_claim(
    claimed: Optional[str],
    canonical: str,
    *,
    signing_digest: Optional[str] = None,
) -> str:
    """Refuse forged alternate identities; return canonical hash always.

    Non-digest labels (unit harness ``tx_hash='low'``) are treated as absent
    claims — identity is still rebound to canonical. Only a wrong 64-hex
    digest is ``tx_hash_mismatch``.
    """
    claim = str(claimed or "").strip()
    canon = str(canonical or "").strip()
    if not canon:
        raise ValueError("tx_hash_mismatch: empty canonical hash")
    if not claim or not _looks_like_digest(claim):
        return canon
    if claim.lower() == canon.lower() or (
        claim.startswith("0x") and claim[2:].lower() == canon.lower()
    ):
        return canon
    if signing_digest and claim.lower().removeprefix("0x") == str(
        signing_digest
    ).lower().removeprefix("0x"):
        # Legacy wallet put signing digest in ``hash`` — not identity.
        return canon
    raise ValueError("tx_hash_mismatch: client hash does not match payload")


def _normalize_identity_value(value: Any) -> Any:
    """Match Wallet.sign_transaction: whole ABS amounts are JSON ints, not 1.0.

    HTTP ``_parse_tx_value`` returns float; without this, signing-digest claims
    refuse as ``tx_hash_mismatch`` and prod signed-tx smoke fails.
    """
    if isinstance(value, bool):
        return value
    if isinstance(value, float) and value == int(value):
        return int(value)
    return value


def bind_identity_from_fields(
    claimed: Optional[str],
    *,
    from_addr: str,
    to_addr: str,
    value: Any,
    nonce: int,
    gas: int = 21_000,
    data: str = "",
    timestamp: int = 0,
    chain_id: int = 1,
) -> tuple[str, int]:
    """Compute canonical identity and validate optional client claim."""
    value = _normalize_identity_value(value)
    canonical, ts = compute_tx_identity_hash(
        from_addr=from_addr,
        to_addr=to_addr,
        value=value,
        nonce=nonce,
        gas=gas,
        data=data,
        timestamp=timestamp,
    )
    signing = wallet_signing_digest(
        from_addr=from_addr,
        to_addr=to_addr,
        value=value,
        nonce=nonce,
        chain_id=chain_id,
        gas=gas,
        data=data,
    )
    bound = bind_tx_hash_claim(claimed, canonical, signing_digest=signing)
    return bound, ts
