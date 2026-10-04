#!/usr/bin/env python3
"""MEV analysis engine: mempool fee-ordering and sandwich detection."""

from crypto import native
import time
from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass
class Transaction:
    hash: str
    from_addr: str
    to_addr: str
    value: float
    gas_price: int
    timestamp: int


class MEVAnalyzer:
    """MEV analysis from real mempool ordering, persisted in SQLite."""

    def __init__(self, db=None):
        self.db = db
        self.attack_history: List[Dict] = []
        self._load_from_db()
        print(
            f"[MEV] Analyzer initialized ({len(self.attack_history)} records, "
            f"persisted={bool(db)})"
        )

    def _load_from_db(self) -> None:
        if not self.db or not hasattr(self.db, "get_mev_simulations"):
            return
        for row in self.db.get_mev_simulations(limit=500):
            entry = {
                "sim_id": row["sim_id"],
                "type": row["sim_type"],
                "profit": row["profit"],
                **row.get("payload", {}),
            }
            self.attack_history.append(entry)

    def _record(self, sim_type: str, profit: float, payload: Dict) -> str:
        from runtime.amount import to_satoshi

        sim_id = native.sha256_hex(
            f"{sim_type}{profit}{time.time()}".encode()
        )[:16]
        profit_sat = int(payload.get("profit_satoshi", to_satoshi(profit)))
        entry = {
            "sim_id": sim_id,
            "type": sim_type,
            "profit": profit,
            "profit_satoshi": profit_sat,
            "timestamp": int(time.time()),
            "executed": False,
            "heuristic": True,
            **payload,
        }
        self.attack_history.append(entry)
        if len(self.attack_history) > 5000:
            self.attack_history = self.attack_history[-5000:]
        if self.db and hasattr(self.db, "save_mev_simulation"):
            self.db.save_mev_simulation({
                "sim_id": sim_id,
                "sim_type": sim_type,
                "profit": profit,
                "profit_satoshi": profit_sat,
                "payload": entry,
                "created_at": entry["timestamp"],
            })
        return sim_id

    def detect_sandwich_opportunity(self, txs: List[Transaction]) -> Dict:
        if len(txs) < 2:
            return {"opportunity": False}
        sorted_txs = sorted(txs, key=lambda tx: tx.gas_price, reverse=True)
        top_fee = sorted_txs[0].gas_price
        second_fee = sorted_txs[1].gas_price if len(sorted_txs) > 1 else 0
        if top_fee <= second_fee:
            return {"opportunity": False, "reason": "flat_fee_ordering"}
        victim = sorted_txs[1]
        spread = top_fee - second_fee
        profit = victim.value * min(0.05, spread / max(top_fee, 1))
        result = {
            "opportunity": True,
            "type": "sandwich",
            "victim": victim.hash[:16],
            "profit": round(profit, 6),
            "model_estimate": round(profit, 6),
            "fee_spread": spread,
            "probability": min(0.95, spread / max(top_fee, 1)),
            "executed": False,
            "source": "mempool_fee_order",
            "note": "heuristic signal — not a confirmed on-chain attack",
        }
        self._record("sandwich", profit, result)
        return result

    def detect_arbitrage(self, pairs: List) -> Dict:
        """Fee-spread arbitrage signal from ordered tx pairs."""
        if len(pairs) < 2:
            return {"opportunity": False}
        fees = []
        for item in pairs[:10]:
            if isinstance(item, dict):
                fees.append(int(item.get("gas_price", item.get("fee", 0)) or 0))
            elif hasattr(item, "gas_price"):
                fees.append(int(item.gas_price or 0))
        if len(fees) < 2:
            return {"opportunity": False}
        fees.sort(reverse=True)
        spread = fees[0] - fees[-1]
        if spread <= 0:
            return {"opportunity": False, "reason": "no_fee_spread"}
        profit = spread / 1_000_000_000.0
        result = {
            "opportunity": True,
            "type": "arbitrage",
            "profit": round(profit, 6),
            "model_estimate": round(profit, 6),
            "fee_spread": spread,
            "probability": min(0.9, spread / max(fees[0], 1)),
            "executed": False,
            "source": "mempool_fee_spread",
            "note": "heuristic signal — not a confirmed on-chain attack",
        }
        self._record("arbitrage", profit, result)
        return result

    def simulate_frontrun(self, target_tx: Transaction, bot_balance: float) -> Dict:
        if target_tx.value * 0.1 > bot_balance:
            return {"opportunity": False, "executed": False, "reason": "Insufficient balance"}
        estimated_profit = target_tx.value * min(0.05, target_tx.gas_price / 1_000_000_000.0)
        # Do not invent a default gas_used — only report when target carries explicit gas.
        raw_gas = getattr(target_tx, "gas", None)
        if raw_gas is None:
            raw_gas = getattr(target_tx, "gas_limit", None)
        try:
            gas_used = int(raw_gas) if raw_gas is not None else None
        except (TypeError, ValueError):
            gas_used = None
        if gas_used is not None and gas_used <= 0:
            gas_used = None
        result = {
            "opportunity": estimated_profit > 0,
            "executed": False,
            "estimated_profit": round(estimated_profit, 6),
            "strategy": "frontrun",
            "gas_used": gas_used,
            "source": "fee_priority_model",
            "model_only": True,
        }
        self._record("frontrun", estimated_profit, {
            "target": target_tx.hash[:16],
            **result,
        })
        return result

    def get_history(self, limit: int = 50) -> List[Dict]:
        return list(reversed(self.attack_history[-limit:]))

    def get_statistics(self) -> Dict[str, Any]:
        from runtime.amount import from_satoshi_float, to_satoshi

        n = len(self.attack_history)
        profit_sat = sum(
            int(a.get("profit_satoshi", to_satoshi(a.get("profit", 0))))
            for a in self.attack_history
        )
        model_est = from_satoshi_float(profit_sat)
        return {
            # Legacy key kept for API compatibility; prefer heuristic_signals.
            "total_attacks": n,
            "heuristic_signals": n,
            "estimated_profit": round(model_est, 4),
            "estimated_profit_satoshi": int(profit_sat),
            "model_estimate_profit": round(model_est, 4),
            "executed": False,
            "simulation_only": True,
            "consensus_wired": False,
            "attack_types": {
                "sandwich": sum(
                    1 for a in self.attack_history if a.get("type") == "sandwich"
                ),
                "arbitrage": sum(
                    1 for a in self.attack_history if a.get("type") == "arbitrage"
                ),
                "frontrun": sum(
                    1 for a in self.attack_history if a.get("type") == "frontrun"
                ),
            },
            "persisted": bool(self.db),
            "note": "heuristic mempool signals — not confirmed on-chain attacks",
        }
