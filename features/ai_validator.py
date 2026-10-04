#!/usr/bin/env python3
"""AI VALIDATOR ENGINE — simulation / research surface (not consensus-wired)."""

import random
from dataclasses import dataclass
from typing import Dict, List, Any
from runtime.amount import from_satoshi_float, to_satoshi

HONESTY = (
    "ai_validator sprout: simulation_only — not consensus-wired / not mainnet / "
    "prod feature_ai_validator=false"
)


@dataclass
class Validator:
    address: str
    stake: float
    stake_satoshi: int = 0
    performance: float = 0.5
    reliability: float = 0.5
    rewards: float = 0
    rewards_satoshi: int = 0
    slashed: bool = False

    def __post_init__(self) -> None:
        if self.stake_satoshi:
            self.stake_satoshi = max(0, int(self.stake_satoshi))
            self.stake = from_satoshi_float(self.stake_satoshi)
        else:
            self.stake_satoshi = int(to_satoshi(self.stake or 0))
            self.stake = from_satoshi_float(self.stake_satoshi)
        if self.rewards_satoshi:
            self.rewards_satoshi = max(0, int(self.rewards_satoshi))
            self.rewards = from_satoshi_float(self.rewards_satoshi)
        else:
            self.rewards_satoshi = int(to_satoshi(self.rewards or 0))

class AIValidatorEngine:
    """Heuristic validator scoring — simulation_only, not bound to block production."""
    
    def __init__(self):
        self.validators: Dict[str, Validator] = {}
        self.history: List[Dict] = []
    
    def add_validator(self, address: str, stake: float = 0.0, *, stake_satoshi: int | None = None) -> None:
        self.validators[address] = Validator(
            address=address,
            stake=float(stake or 0),
            stake_satoshi=int(stake_satoshi) if stake_satoshi is not None else 0,
        )
    
    def calculate_score(self, validator: Validator) -> float:
        """Расчёт общей оценки валидатора"""
        score = (
            validator.performance * 0.4 +
            validator.reliability * 0.4 +
            (validator.stake / 10000) * 0.2
        )
        return min(1.0, score)
    
    def select_proposer(self) -> str:
        """Heuristic proposer pick — not used by consensus forge path."""
        scores = [(addr, self.calculate_score(v)) for addr, v in self.validators.items()]
        scores.sort(key=lambda x: x[1], reverse=True)
        
        # Топ-3 имеют преимущество
        if scores and random.random() < 0.7:
            return scores[0][0]
        elif len(scores) > 1:
            return scores[1][0]
        return scores[0][0] if scores else ""
    
    def update_performance(self, address: str, success: bool):
        if address in self.validators:
            val = self.validators[address]
            if success:
                val.performance = min(1.0, val.performance + 0.05)
                reward_sat = int(to_satoshi(100))
                val.rewards_satoshi += reward_sat
                val.rewards = from_satoshi_float(val.rewards_satoshi)
            else:
                val.performance = max(0, val.performance - 0.1)
    
    def detect_mev_opportunity(self, mempool: List) -> Dict:
        """
        Simulation-only MEV pattern stub.

        Does not claim measured profit or model-bound detection — returns
        heuristic placeholders labeled as such.
        """
        opportunities = []
        
        if len(mempool) >= 3:
            opportunities.append({
                "type": "sandwich",
                "probability": None,
                "profit": None,
                "heuristic": True,
                "invented_numbers": False,
                "note": "pattern stub only; no profit/probability invented",
            })
        
        if len(mempool) >= 2:
            opportunities.append({
                "type": "arbitrage",
                "probability": None,
                "profit": None,
                "heuristic": True,
                "invented_numbers": False,
                "note": "pattern stub only; no profit/probability invented",
            })
        
        return {
            "opportunities": opportunities,
            "total": len(opportunities),
            "simulation_only": True,
            "consensus_wired": False,
            "model_bound": False,
            "invented_numbers": False,
        }
    
    def get_stats(self) -> Dict:
        n = len(self.validators)
        total_stake_sat = sum(v.stake_satoshi for v in self.validators.values())
        total_rewards_sat = sum(v.rewards_satoshi for v in self.validators.values())
        return {
            "validators": n,
            "total_stake": from_satoshi_float(total_stake_sat),
            "total_stake_satoshi": int(total_stake_sat),
            "avg_performance": (
                sum(v.performance for v in self.validators.values()) / n if n else 0.0
            ),
            "total_rewards": from_satoshi_float(total_rewards_sat),
            "total_rewards_satoshi": int(total_rewards_sat),
            "simulation_only": True,
            "consensus_wired": False,
            "model_bound": False,
            "honesty": HONESTY,
            "note": "AI validator is a research/sim surface; not used for block proposer selection",
        }

def test_ai_validator():
    print("AI Validator Engine Test (simulation_only)")
    print("=" * 40)
    
    engine = AIValidatorEngine()
    
    for i in range(10):
        engine.add_validator(f"0xval_{i}", 100.0 + i * 50.0)
    
    stats = engine.get_stats()
    print(f"   Validators: {stats['validators']}")
    print(f"   Total stake: {stats['total_stake']:.0f}")
    print(f"   Avg performance: {stats['avg_performance']:.2f}")
    print(f"   consensus_wired={stats['consensus_wired']} model_bound={stats['model_bound']}")
    
    proposer = engine.select_proposer()
    print(f"   Heuristic proposer: {proposer[:16]}...")
    
    mev = engine.detect_mev_opportunity([])
    print(f"   MEV stub opportunities: {mev['total']} invented_numbers={mev['invented_numbers']}")
    
    return True

if __name__ == "__main__":
    test_ai_validator()
