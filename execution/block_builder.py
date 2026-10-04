# execution/block_builder.py
"""
Block Builder — creates blocks from mempool transactions
"""

import json
import time
from typing import List, Dict, Any, Optional

from crypto.merkle import merkle_root
from crypto import native


class BlockBuilder:
    """Builds blocks with deterministic ordering"""
    
    def __init__(self, mempool, state_engine):
        self.mempool = mempool
        self.state = state_engine
    
    def build_block(self, parent_block: dict, proposer: str = "validator") -> dict:
        """
        Build a new block from mempool transactions
        """
        # Get pending transactions
        pending_txs = self.mempool.get_sorted_transactions()
        
        # Filter valid transactions (satoshi balance / fee — not float ABS).
        valid_txs = []
        for tx in pending_txs:
            if self._tx_affordable_sat(tx):
                valid_txs.append(tx)
        
        # Limit block size
        max_txs = 100
        selected_txs = valid_txs[:max_txs]
        
        # Calculate block number
        block_number = parent_block.get("number", 0) + 1
        
        # Build transaction trie root
        tx_root = self._compute_tx_root(selected_txs)
        
        # Create block
        block = {
            "number": block_number,
            "parent_hash": parent_block.get("hash", "0" * 64),
            "timestamp": int(time.time()),
            "proposer": proposer,
            "transactions": [self._tx_to_dict(tx) for tx in selected_txs],
            "tx_root": tx_root,
            "state_root": None,  # Will be filled after execution
            "hash": None,  # Will be filled after execution
        }
        
        return block
    
    def _compute_tx_root(self, transactions) -> str:
        """Compute merkle root of transactions (same rules as core.blockchain.Block)."""
        if not transactions:
            return merkle_root(["empty"])
        tx_hashes: List[str] = []
        for tx in transactions:
            if isinstance(tx, dict):
                tx_hashes.append(str(tx.get("hash", "") or ""))
            else:
                tx_hashes.append(str(getattr(tx, "hash", "") or ""))
        return merkle_root(tx_hashes)
    
    def _tx_affordable_sat(self, tx: dict) -> bool:
        """True when sender covers amount+fee in satoshi (ADR 0021)."""
        from runtime.amount import to_satoshi

        from_addr = tx.get("from") or tx.get("from_addr") or ""
        if not from_addr:
            return False
        try:
            raw_amt = tx.get("amount_satoshi", tx.get("value_satoshi"))
            if raw_amt is not None and raw_amt != "":
                amount_sat = int(raw_amt)
                raw_abs = tx.get("value", tx.get("amount"))
                if raw_abs is not None and raw_abs != "":
                    if int(to_satoshi(raw_abs)) != amount_sat:
                        return False
            else:
                amount_sat = int(to_satoshi(tx.get("value", tx.get("amount", 0))))
            raw_fee = tx.get("fee_satoshi")
            if raw_fee is not None and raw_fee != "":
                fee_sat = int(raw_fee)
            elif tx.get("fee") is not None and tx.get("fee") != "":
                fee_sat = int(to_satoshi(tx.get("fee")))
            else:
                # Legacy eth-style gasPrice*gas is not L1 fee authority — refuse invent.
                fee_sat = 0
            if amount_sat < 0 or fee_sat < 0:
                return False
        except (TypeError, ValueError):
            return False
        if hasattr(self.state, "get_balance_satoshi"):
            bal_sat = int(self.state.get_balance_satoshi(from_addr) or 0)
        else:
            bal_sat = int(to_satoshi(self.state.get_balance(from_addr) or 0))
        return bal_sat >= amount_sat + fee_sat

    def _tx_to_dict(self, tx) -> dict:
        """Convert transaction to dict for inclusion in block (carry satoshi twins)."""
        from runtime.amount import to_satoshi

        if isinstance(tx, dict):
            value = tx.get("value", tx.get("amount", 0))
            out = {
                "hash": tx.get("hash", ""),
                "from": tx.get("from", ""),
                "to": tx.get("to", ""),
                "value": value,
                "gas_limit": int(tx.get("gas") or tx.get("gas_limit") or 0),
                "gas_price": tx.get("gasPrice", tx.get("gas_price", 0)),
                "nonce": tx.get("nonce", 0),
                "data": tx.get("data", ""),
                "timestamp": tx.get("timestamp", 0),
            }
            raw_amt = tx.get("amount_satoshi", tx.get("value_satoshi"))
            if raw_amt is not None and raw_amt != "":
                out["amount_satoshi"] = int(raw_amt)
                out["value_satoshi"] = int(raw_amt)
            else:
                out["amount_satoshi"] = int(to_satoshi(value or 0))
                out["value_satoshi"] = out["amount_satoshi"]
            if tx.get("fee_satoshi") is not None and tx.get("fee_satoshi") != "":
                out["fee_satoshi"] = int(tx["fee_satoshi"])
            elif tx.get("fee") is not None:
                out["fee"] = tx.get("fee")
                out["fee_satoshi"] = int(to_satoshi(tx.get("fee") or 0))
            return out
        value = getattr(tx, "value", getattr(tx, "amount", 0))
        amt_sat = getattr(tx, "amount_satoshi", None)
        if amt_sat is None or int(amt_sat) < 0:
            amt_sat = int(to_satoshi(value or 0))
        else:
            amt_sat = int(amt_sat)
        out = {
            "hash": str(getattr(tx, "hash", "") or ""),
            "from": getattr(tx, "from_addr", getattr(tx, "from", "")),
            "to": getattr(tx, "to_addr", getattr(tx, "to", "")),
            "value": value,
            "amount_satoshi": amt_sat,
            "value_satoshi": amt_sat,
            "gas_limit": int(getattr(tx, "gas", 0) or 0),
            "gas_price": getattr(tx, "gasPrice", getattr(tx, "gas_price", 0)),
            "nonce": getattr(tx, "nonce", 0),
            "data": (
                tx.data.hex()
                if isinstance(getattr(tx, "data", ""), bytes)
                else getattr(tx, "data", "")
            ),
            "timestamp": getattr(tx, "timestamp", 0),
        }
        fee_sat = getattr(tx, "fee_satoshi", None)
        if fee_sat is not None and int(fee_sat) >= 0:
            out["fee_satoshi"] = int(fee_sat)
        return out
    
    def finalize_block(self, block: dict, state_root: str) -> dict:
        """Finalize block with state root and hash"""
        block["state_root"] = state_root
        block["hash"] = self._compute_block_hash(block)
        return block
    
    def _compute_block_hash(self, block: dict) -> str:
        """Compute deterministic block hash via native canonical rules."""
        payload = json.dumps({
            "number": block["number"],
            "parent_hash": block["parent_hash"],
            "timestamp": block["timestamp"],
            "proposer": block["proposer"],
            "tx_root": block["tx_root"],
            "state_root": block["state_root"]
        }, sort_keys=True)
        return native.canonical_hash_json(payload)
