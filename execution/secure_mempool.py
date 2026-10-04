# -*- coding: utf-8 -*-
"""Secure mempool with nonce replay protection for legacy v49 tests."""
import time
from typing import Dict, Tuple, Union

from crypto import native
from execution.mempool import Mempool, MempoolTransaction, Transaction, _require_wire_satoshi


class SecureMempool(Mempool):
    def __init__(self, state_engine):
        super().__init__()
        self.state_engine = state_engine
        self._seen_nonces: Dict[str, set] = {}

    def add_transaction(self, tx: Union[Dict, Transaction]) -> Tuple[bool, str]:
        if isinstance(tx, dict):
            from blockchain.mempool_wire import WireMoneyMissing, resolve_wire_amount_sat
            from runtime.amount import from_satoshi_float

            try:
                amount_sat, amount = resolve_wire_amount_sat(
                    tx, require_satoshi=_require_wire_satoshi()
                )
            except WireMoneyMissing:
                return False, "amount_satoshi_required"
            amount = float(from_satoshi_float(int(amount_sat)))
            if amount < 0 or amount_sat < 0:
                return False, "negative_amount"
            sender = tx.get("from", tx.get("from_addr", ""))
            recipient = tx.get("to", tx.get("to_addr", ""))
            nonce = int(tx.get("nonce", 0))
            # Refuse invent fee=1 when gas_price/fee omitted.
            raw_fee = tx.get("gas_price", tx.get("fee"))
            if raw_fee is None or raw_fee == "":
                return False, "fee_required"
            try:
                fee = float(raw_fee)
            except (TypeError, ValueError):
                return False, "fee_required"
            if fee <= 0:
                return False, "fee_required"
            tx_hash = tx.get("hash") or (
                "0x" + native.sha256_hex(f"{sender}{recipient}{amount}{nonce}".encode())
            )
            seen = self._seen_nonces.setdefault(sender, set())
            if nonce in seen:
                return False, "duplicate_nonce"
            balance = self.state_engine.get_balance(sender) if self.state_engine else 0.0
            if balance < amount:
                return False, "insufficient_balance"
            mempool_tx = MempoolTransaction(
                tx_hash=tx_hash,
                from_addr=sender,
                to_addr=recipient,
                amount=amount,
                fee=fee,
                nonce=nonce,
                signature=tx.get("signature", ""),
                public_key=tx.get("public_key", ""),
                timestamp=time.time(),
                amount_satoshi=int(amount_sat),
            )
            if not self.add_raw(mempool_tx):
                return False, "mempool_rejected"
            seen.add(nonce)
            return True, "ok"

        if tx.amount < 0:
            return False, "negative_amount"
        if not super().add_transaction(tx):
            return False, "mempool_rejected"
        return True, "ok"
