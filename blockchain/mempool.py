#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Mempool — пул неподтверждённых транзакций с приоритетом по комиссии.

Интегрирует:
  - Базовая сортировка по fee (System A)
  - Валидация адресов и сумм через middleware/validators.py
  - ECDSA проверка подписи через crypto/wallet.py
"""

import time
import threading
import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# --- Input validation (middleware/validators.py) ---
try:
    from middleware.validators import validate_address, validate_amount, validate_tx_data
    _VALIDATORS_AVAILABLE = True
except ImportError:
    _VALIDATORS_AVAILABLE = False

# --- ECDSA signature verification (crypto/wallet.py) ---
try:
    from crypto.wallet import verify_transaction_signature, verify_transaction_signatures_batch
    _ECDSA_AVAILABLE = True
except ImportError:
    _ECDSA_AVAILABLE = False


@dataclass
class MempoolTransaction:
    """Транзакция в мемпуле."""
    tx_hash: str
    from_addr: str
    to_addr: str
    amount: float
    fee: float
    nonce: int = 0
    signature: str = ""
    public_key: str = ""
    data: str = ""
    gas: int = 0  # explicit gas required on add (no invent 21000)
    timestamp: float = field(default_factory=time.time)
    amount_satoshi: int = -1
    fee_satoshi: int = -1

    def __post_init__(self) -> None:
        from runtime.amount import to_satoshi

        if int(self.amount_satoshi) < 0:
            self.amount_satoshi = int(to_satoshi(self.amount))
        if int(self.fee_satoshi) < 0:
            self.fee_satoshi = int(to_satoshi(self.fee))

    def has_valid_signature(self) -> bool:
        """ECDSA check; when require_signatures is on, empty signature fails."""
        require = getattr(self, "require_signatures", False)
        if not self.signature:
            return not require
        if not self.public_key:
            return False
        if not _ECDSA_AVAILABLE:
            return False
        try:
            tx_dict = {
                "from": self.from_addr,
                "to": self.to_addr,
                "value": int(self.amount) if self.amount == int(self.amount) else self.amount,
                "nonce": self.nonce,
                "chain_id": getattr(self, "_chain_id", None) or getattr(self, "chain_id", 1),
                "signature": self.signature,
                "public_key": self.public_key,
                "data": self.data or "",
                "gas_limit": int(self.gas),
            }
            return verify_transaction_signature(tx_dict)
        except Exception as exc:
            logger.warning("mempool signature verify error: %s", exc)
            return False


def _validate_mempool_tx(tx: MempoolTransaction, min_fee_satoshi: int) -> Tuple[bool, str]:
    """
    Полная валидация транзакции перед добавлением в мемпул.
    Использует middleware/validators.py если доступен.
    Min-fee gate is satoshi-integer (not float ABS).
    """
    if not tx.tx_hash:
        return False, "missing_hash"
    try:
        gas = int(tx.gas)
    except (TypeError, ValueError):
        return False, "gas_required"
    if gas <= 0:
        return False, "gas_required"
    fee_sat = int(getattr(tx, "fee_satoshi", -1))
    if fee_sat < 0:
        from runtime.amount import to_satoshi

        fee_sat = int(to_satoshi(tx.fee))
        tx.fee_satoshi = fee_sat
    if fee_sat < int(min_fee_satoshi):
        return False, f"fee_too_low (min_satoshi={int(min_fee_satoshi)})"

    if _VALIDATORS_AVAILABLE:
        # Validate addresses
        valid, err = validate_address(tx.from_addr)
        if not valid:
            # Allow non-0x addresses (internal/genesis) with basic check
            if len(tx.from_addr) < 5:
                return False, f"invalid_from: {err}"

        valid, err = validate_address(tx.to_addr)
        if not valid:
            if len(tx.to_addr) < 5:
                return False, f"invalid_to: {err}"

        # Validate amount (zero-value allowed for contract deploy/call)
        if tx.amount < 0:
            return False, "negative_amount"
        if tx.amount > 0:
            valid, err = validate_amount(tx.amount, min_amount=0.0)
            if not valid:
                return False, f"invalid_amount: {err}"

    elif tx.amount < 0:
        return False, "negative_amount"

    return True, "ok"


def _mempool_tx_verify_dict(tx: MempoolTransaction, chain_id: int) -> Dict:
    return {
        "from": tx.from_addr,
        "to": tx.to_addr,
        "value": int(tx.amount) if tx.amount == int(tx.amount) else tx.amount,
        "nonce": tx.nonce,
        "chain_id": chain_id,
        "signature": tx.signature,
        "public_key": tx.public_key,
        "data": tx.data or "",
        "gas_limit": int(tx.gas),
    }


def _tx_to_store_dict(tx: MempoolTransaction) -> Dict:
    """Serialize mempool tx for store/native roundtrip (ADR 0021 satoshi twins)."""
    from runtime.amount import from_satoshi_float, to_satoshi

    fee_sat = int(getattr(tx, "fee_satoshi", -1))
    if fee_sat < 0:
        fee_sat = int(to_satoshi(tx.fee))
        tx.fee_satoshi = fee_sat
    amount_sat = int(getattr(tx, "amount_satoshi", -1))
    if amount_sat < 0:
        amount_sat = int(to_satoshi(tx.amount))
        tx.amount_satoshi = amount_sat
    # Wave R / ADR 0021: ABS floats derived from satoshi (no raw float invent).
    return {
        "tx_hash": str(tx.tx_hash),
        "from_addr": str(tx.from_addr),
        "to_addr": str(tx.to_addr),
        "amount": from_satoshi_float(amount_sat),
        "amount_satoshi": int(amount_sat),
        "fee": from_satoshi_float(fee_sat),
        "fee_satoshi": int(fee_sat),
        "nonce": int(tx.nonce or 0),
        "signature": str(tx.signature or ""),
        "public_key": str(tx.public_key or ""),
        "data": str(tx.data or ""),
        "gas": int(tx.gas),
        "timestamp": float(tx.timestamp or 0.0),
    }


def _tx_from_store_dict(raw: Dict) -> MempoolTransaction:
    """Reload mempool tx from store dict; prefer satoshi twins over ABS floats."""
    from runtime.amount import from_satoshi_float, money_abs, to_satoshi

    raw_fee_sat = raw.get("fee_satoshi")
    if raw_fee_sat is None:
        fee_sat = int(to_satoshi(money_abs(raw.get("fee") or 0, field="fee")))
    else:
        fee_sat = int(raw_fee_sat)
    raw_amt_sat = raw.get("amount_satoshi")
    if raw_amt_sat is None:
        amount_sat = int(to_satoshi(money_abs(raw.get("amount") or 0, field="amount")))
    else:
        amount_sat = int(raw_amt_sat)
    # Do not invent gas=21000 when store row lacks/zeros gas.
    raw_gas = raw.get("gas")
    gas = int(raw_gas) if raw_gas is not None and str(raw_gas).strip() != "" else 0
    return MempoolTransaction(
        tx_hash=str(raw.get("tx_hash") or ""),
        from_addr=str(raw.get("from_addr") or ""),
        to_addr=str(raw.get("to_addr") or ""),
        amount=from_satoshi_float(amount_sat),
        fee=from_satoshi_float(fee_sat),
        nonce=int(raw.get("nonce") or 0),
        signature=str(raw.get("signature") or ""),
        public_key=str(raw.get("public_key") or ""),
        data=str(raw.get("data") or ""),
        gas=gas,
        timestamp=float(raw.get("timestamp") or 0.0),
        fee_satoshi=fee_sat,
        amount_satoshi=amount_sat,
    )


class Mempool:
    """Пул транзакций с сортировкой по комиссии и полной валидацией."""

    def __init__(self, max_size: int = 10000, min_fee: float = 0.0001):
        from runtime.amount import to_satoshi

        self.transactions: Dict[str, MempoolTransaction] = {}
        self.max_size = max_size
        self.min_fee = float(min_fee)
        self.min_fee_satoshi = int(to_satoshi(self.min_fee))
        self.lock = threading.RLock()
        self._rejected_count = 0
        self.blockchain = None
        self.chain_id = 1
        self.require_signatures = False

    def set_blockchain(self, blockchain) -> None:
        """Attach live chain for nonce/balance/signature checks."""
        self.blockchain = blockchain
        if blockchain and getattr(blockchain, "config", None):
            self.chain_id = blockchain.config.chain_id
            self.require_signatures = getattr(
                blockchain.config, "require_signatures", False
            )

    def add(
        self,
        tx: MempoolTransaction,
        signature_preverified: bool = False,
        chain_prevalidated: bool = False,
    ) -> bool:
        """Добавить транзакцию с полной валидацией.

        v1.3.143: chain_prevalidated skips a second blockchain.validate_transaction
        when the P2P path already validated (sig-before-DB). Soft DoS honesty only.
        """
        with self.lock:
            # Bind mempool identity to canonical payload hash (audit §7).
            # Value must match wallet signing encoding (int when whole ABS).
            try:
                from core.tx_identity import bind_identity_from_fields

                amt = tx.amount
                bind_value = (
                    int(amt) if isinstance(amt, (int, float)) and amt == int(amt) else amt
                )
                gas_i = int(getattr(tx, "gas", 0) or 0)
                if gas_i <= 0:
                    self._rejected_count += 1
                    return False
                bound, ts = bind_identity_from_fields(
                    tx.tx_hash,
                    from_addr=tx.from_addr,
                    to_addr=tx.to_addr,
                    value=bind_value,
                    nonce=int(tx.nonce or 0),
                    gas=gas_i,
                    data=getattr(tx, "data", "") or "",
                    timestamp=int(tx.timestamp or 0),
                    chain_id=int(getattr(self, "chain_id", 1) or 1),
                )
                tx.tx_hash = bound
                # Do not rewrite timestamp — signature / identity already bound to it.
                if int(tx.timestamp or 0) <= 0:
                    tx.timestamp = float(ts)
            except ValueError:
                self._rejected_count += 1
                return False

            if tx.tx_hash in self.transactions:
                return False

            # Full validation (min fee in satoshi)
            valid, reason = _validate_mempool_tx(tx, self.min_fee_satoshi)
            if not valid:
                self._rejected_count += 1
                return False

            tx._chain_id = self.chain_id
            tx.require_signatures = self.require_signatures

            # ECDSA signature check
            if not signature_preverified and not tx.has_valid_signature():
                self._rejected_count += 1
                return False

            if self.blockchain and not chain_prevalidated:
                from core.blockchain import Transaction
                gas_i = int(getattr(tx, "gas", 0) or 0)
                if gas_i <= 0:
                    self._rejected_count += 1
                    return False
                amt_sat = int(getattr(tx, "amount_satoshi", -1))
                chain_tx = Transaction(
                    from_addr=tx.from_addr,
                    to_addr=tx.to_addr,
                    value=tx.amount,
                    nonce=tx.nonce,
                    gas=gas_i,
                    data=getattr(tx, "data", "") or "",
                    tx_hash=tx.tx_hash,
                    signature=tx.signature,
                    public_key=tx.public_key,
                    timestamp=int(tx.timestamp or 0),
                    amount_satoshi=amt_sat if amt_sat >= 0 else None,
                )
                tx._chain_id = self.chain_id
                check = self.blockchain.validate_transaction(chain_tx)
                if not check.get("valid"):
                    self._rejected_count += 1
                    return False

            if len(self.transactions) >= self.max_size:
                self._cleanup()
            self.transactions[tx.tx_hash] = tx
            return True

    def verify_signatures_batch(self, txs: List[MempoolTransaction]) -> List[bool]:
        """Batch ECDSA gate for gossip/import bursts via native secp256k1."""
        results = [False for _ in txs]
        if not txs:
            return results

        require = self.require_signatures
        verify_payloads: List[Dict] = []
        verify_indexes: List[int] = []

        for index, tx in enumerate(txs):
            tx._chain_id = self.chain_id
            tx.require_signatures = require
            if not tx.signature:
                results[index] = not require
                continue
            if not tx.public_key:
                results[index] = False
                continue
            verify_payloads.append(_mempool_tx_verify_dict(tx, self.chain_id))
            verify_indexes.append(index)

        if verify_payloads and _ECDSA_AVAILABLE:
            verified = verify_transaction_signatures_batch(verify_payloads)
            for index, ok in zip(verify_indexes, verified):
                results[index] = bool(ok)

        return results

    def add_batch(
        self,
        txs: List[MempoolTransaction],
        *,
        chain_prevalidated: bool = False,
    ) -> Tuple[int, int, List[str]]:
        """Add many txs with one native signature batch verify pass.

        v1.3.143: chain_prevalidated skips second validate_transaction when the
        caller already validated each tx (P2P wire build path).
        """
        if not txs:
            return 0, 0, []

        signature_flags = self.verify_signatures_batch(txs)
        added = 0
        rejected = 0
        accepted_hashes: List[str] = []
        for tx, signature_ok in zip(txs, signature_flags):
            if not signature_ok:
                with self.lock:
                    self._rejected_count += 1
                rejected += 1
                continue
            if self.add(
                tx,
                signature_preverified=True,
                chain_prevalidated=chain_prevalidated,
            ):
                added += 1
                accepted_hashes.append(tx.tx_hash)
            else:
                rejected += 1
        return added, rejected, accepted_hashes

    def add_raw(self, tx: MempoolTransaction) -> bool:
        """Добавить транзакцию без строгой валидации адресов (для internal/genesis txs)."""
        with self.lock:
            if tx.tx_hash in self.transactions:
                return False
            fee_sat = int(getattr(tx, "fee_satoshi", -1))
            if fee_sat < 0:
                from runtime.amount import to_satoshi

                fee_sat = int(to_satoshi(tx.fee))
                tx.fee_satoshi = fee_sat
            if fee_sat < int(self.min_fee_satoshi):
                return False
            if len(self.transactions) >= self.max_size:
                self._cleanup()
            self.transactions[tx.tx_hash] = tx
            return True

    def get(self, limit: int = 100, min_fee: float = 0) -> List[MempoolTransaction]:
        """Получить транзакции для майнинга (сортировка по fee_satoshi)."""
        from runtime.amount import to_satoshi

        min_fee_sat = int(to_satoshi(min_fee)) if min_fee else 0
        with self.lock:
            sorted_txs = sorted(
                self.transactions.values(),
                key=lambda x: int(getattr(x, "fee_satoshi", 0) or 0),
                reverse=True,
            )
            return [
                tx
                for tx in sorted_txs
                if int(getattr(tx, "fee_satoshi", 0) or 0) >= min_fee_sat
            ][:limit]

    def get_sorted_transactions(self) -> List[Dict]:
        """Возвращает транзакции в формате dict (для BlockBuilder System C)."""
        with self.lock:
            sorted_txs = sorted(
                self.transactions.values(),
                key=lambda x: int(getattr(x, "fee_satoshi", 0) or 0),
                reverse=True,
            )
            return [
                {
                    "hash": tx.tx_hash,
                    "from": tx.from_addr,
                    "to": tx.to_addr,
                    "value": tx.amount,
                    "gasPrice": tx.fee,
                    "gas": int(tx.gas or 0),
                    "nonce": tx.nonce,
                    "data": tx.data or "",
                    "timestamp": tx.timestamp,
                    "fee_satoshi": int(getattr(tx, "fee_satoshi", 0) or 0),
                    "amount_satoshi": int(getattr(tx, "amount_satoshi", -1)),
                }
                for tx in sorted_txs
            ]

    def remove(self, tx_hash: str) -> bool:
        """Удалить транзакцию."""
        with self.lock:
            return self.transactions.pop(tx_hash, None) is not None

    def has_transaction(self, tx_hash: str) -> bool:
        with self.lock:
            return tx_hash in self.transactions

    def get_transaction(self, tx_hash: str) -> Optional[MempoolTransaction]:
        with self.lock:
            return self.transactions.get(tx_hash)

    def get_size(self) -> int:
        with self.lock:
            return len(self.transactions)

    def get_stats(self) -> dict:
        from runtime.amount import from_satoshi_float

        with self.lock:
            if not self.transactions:
                return {
                    "size": 0,
                    "total_fees": 0,
                    "avg_fee": 0,
                    "rejected": self._rejected_count,
                    "min_fee_satoshi": int(self.min_fee_satoshi),
                }
            fee_sats = [
                int(getattr(tx, "fee_satoshi", 0) or 0)
                for tx in self.transactions.values()
            ]
            total_sat = sum(fee_sats)
            avg_sat = total_sat / len(fee_sats) if fee_sats else 0
            return {
                "size": len(self.transactions),
                "total_fees": from_satoshi_float(total_sat),
                "avg_fee": from_satoshi_float(avg_sat),
                "total_fees_satoshi": int(total_sat),
                "avg_fee_satoshi": int(avg_sat),
                "min_fee_satoshi": int(self.min_fee_satoshi),
                "rejected": self._rejected_count,
                "validators_available": _VALIDATORS_AVAILABLE,
                "ecdsa_available": _ECDSA_AVAILABLE,
            }

    def _cleanup(self):
        """Удалить 10% самых дешёвых транзакций (by fee_satoshi)."""
        if len(self.transactions) < self.max_size * 0.8:
            return
        sorted_txs = sorted(
            self.transactions.values(),
            key=lambda x: int(getattr(x, "fee_satoshi", 0) or 0),
        )
        to_remove = int(len(self.transactions) * 0.1)
        for tx in sorted_txs[:to_remove]:
            del self.transactions[tx.tx_hash]
