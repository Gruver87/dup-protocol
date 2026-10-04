# -*- coding: utf-8 -*-
"""Legacy transaction builder for integration scripts."""
import time
from typing import Dict, Optional

from crypto import native
from runtime.amount import to_satoshi


class TransactionBuilder:
    @staticmethod
    def create_transaction(
        from_addr: str,
        to_addr: str,
        value: float,
        nonce: int = 0,
        gas_price: float | None = None,
        gas_limit: int | None = None,
        data: str = "",
        *,
        amount_satoshi: Optional[int] = None,
    ) -> Dict:
        # Refuse invent gas_price=1 / gas_limit=21000 — callers must pass both.
        if gas_price is None:
            raise ValueError("gas_price_required")
        if gas_limit is None:
            raise ValueError("gas_limit_required")
        gas_price_f = float(gas_price)
        gas_limit_i = int(gas_limit)
        if gas_price_f <= 0:
            raise ValueError("gas_price_required")
        if gas_limit_i <= 0:
            raise ValueError("gas_limit_required")
        if amount_satoshi is not None:
            amt_sat = int(amount_satoshi)
            if amt_sat < 0:
                raise ValueError("value_negative")
            if int(to_satoshi(value)) != amt_sat:
                raise ValueError("value_satoshi_mismatch")
        else:
            amt_sat = int(to_satoshi(value))
        tx = {
            "from": from_addr,
            "to": to_addr,
            "value": value,
            "amount_satoshi": amt_sat,
            "value_satoshi": amt_sat,
            "nonce": nonce,
            "gasPrice": gas_price_f,
            "gas": gas_limit_i,
            "data": data,
            "timestamp": int(time.time()),
        }
        raw = f"{from_addr}{to_addr}{value}{nonce}{gas_price_f}"
        tx["hash"] = "0x" + native.sha256_hex(raw.encode())
        return tx

    @staticmethod
    def sign_transaction(tx: Dict, private_key: str) -> Dict:
        signed = dict(tx)
        signed["signature"] = native.sha256_hex((tx.get("hash", "") + private_key).encode())
        return signed
