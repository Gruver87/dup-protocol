# -*- coding: utf-8 -*-
"""Execution mempool compatibility layer for legacy tests."""
import os
import time
from dataclasses import dataclass
from typing import Dict, List, Union

from blockchain.mempool import Mempool as _BaseMempool, MempoolTransaction
MempoolTransaction = MempoolTransaction  # re-export for secure_mempool / legacy imports
from crypto import native


def _require_wire_satoshi() -> bool:
    """Prod/staging refuse float-only money on this legacy layer (ADR 0021).

    Honors ``ABS_DEPLOYMENT_MODE`` first, then ``DEPLOYMENT_MODE`` (same as
    ``runtime.config``). Unit tests that need lab float path must clear both.
    """
    mode = (
        os.environ.get("ABS_DEPLOYMENT_MODE")
        or os.environ.get("DEPLOYMENT_MODE")
        or ""
    ).strip().lower()
    return mode in ("prod", "production", "staging")


@dataclass
class Transaction:
    sender: str
    recipient: str
    amount: float
    gas_price: float = 0.0  # must be set positive by callers; 0 is invalid for add
    nonce: int = 0
    hash: str = ""
    amount_satoshi: int = -1

    def __post_init__(self):
        if not self.hash:
            raw = f"{self.sender}{self.recipient}{self.amount}{self.nonce}{self.gas_price}"
            self.hash = "0x" + native.sha256_hex(raw.encode())[:40]


def create_transaction(
    sender: str,
    recipient: str,
    amount: float,
    gas_price: float | None = None,
    nonce: int = 0,
    *,
    amount_satoshi: int | None = None,
) -> Transaction:
    # Refuse invent gas_price=1.0 when omitted.
    if gas_price is None:
        raise ValueError("gas_price_required")
    fee = float(gas_price)
    if fee <= 0:
        raise ValueError("gas_price_required")
    sat = -1 if amount_satoshi is None else int(amount_satoshi)
    return Transaction(sender, recipient, amount, fee, nonce, amount_satoshi=sat)


class Mempool(_BaseMempool):
    def add_transaction(self, tx: Union[Transaction, Dict]) -> Union[bool, str]:
        if isinstance(tx, dict):
            from blockchain.mempool_wire import WireMoneyMissing, resolve_wire_amount_sat
            from runtime.amount import from_satoshi_float

            sender = tx.get("from", tx.get("from_addr", ""))
            recipient = tx.get("to", tx.get("to_addr", ""))
            try:
                amount_sat, amount = resolve_wire_amount_sat(
                    tx, require_satoshi=_require_wire_satoshi()
                )
            except WireMoneyMissing:
                return False
            amount = float(from_satoshi_float(int(amount_sat))) if amount_sat is not None else float(amount)
            nonce = int(tx.get("nonce", 0))
            # Refuse invent fee=1 when gas_price/fee omitted.
            raw_fee = tx.get("gas_price", tx.get("gasPrice", tx.get("fee")))
            if raw_fee is None or raw_fee == "":
                return False
            try:
                fee = float(raw_fee)
            except (TypeError, ValueError):
                return False
            if fee <= 0:
                return False
            tx_hash = tx.get("hash") or (
                "0x" + native.sha256_hex(f"{sender}{recipient}{amount}{nonce}".encode())
            )
            raw_gas = tx.get("gas", tx.get("gas_limit", tx.get("gasLimit")))
            if raw_gas is None or raw_gas == "":
                return False
            try:
                gas_i = int(raw_gas)
            except (TypeError, ValueError):
                return False
            if gas_i <= 0:
                return False
            mempool_tx = MempoolTransaction(
                tx_hash=tx_hash,
                from_addr=sender,
                to_addr=recipient,
                amount=amount,
                fee=fee,
                nonce=nonce,
                gas=gas_i,
                timestamp=time.time(),
                amount_satoshi=int(amount_sat),
            )
            if self.add_raw(mempool_tx):
                return tx_hash
            return False

        from runtime.amount import to_satoshi

        amt_sat = int(getattr(tx, "amount_satoshi", -1))
        if amt_sat < 0:
            if _require_wire_satoshi():
                return False
            amt_sat = int(to_satoshi(tx.amount))
        gas_obj = int(getattr(tx, "gas", 0) or 0)
        if gas_obj <= 0:
            return False
        mempool_tx = MempoolTransaction(
            tx_hash=tx.hash,
            from_addr=tx.sender,
            to_addr=tx.recipient,
            amount=tx.amount,
            fee=tx.gas_price,
            nonce=tx.nonce,
            gas=gas_obj,
            timestamp=time.time(),
            amount_satoshi=amt_sat,
        )
        return self.add_raw(mempool_tx)

    def get_pending_count(self) -> int:
        return self.get_size()

    def get_transactions_for_block(self, limit: int = 100) -> List[Dict]:
        return self.get_sorted_transactions()[:limit]
