"""AI Agent Manager — trading agents with SQLite persistence (Wave 43).

Honesty: ADR 0016 sprout (``feature_ai_agents``). Prod mesh keeps the flag false.
Not consensus-wired. Not wallet custody. Money prefers integer satoshi.
"""

from crypto import native
import logging
import json
import time
from typing import Any, Callable, Dict, List, Optional

from runtime.amount import from_satoshi_float, to_satoshi

logger = logging.getLogger(__name__)

HONESTY = (
    "ai_agents sprout: lab/dev-test only — not consensus / not mainnet / "
    "prod feature_ai_agents=false"
)


class AIAgent:
    def __init__(self, agent_id: str, name: str, owner: str,
                 agent_type: str = "transformer",
                 status: str = "active",
                 created_at: int = None,
                 last_action: int = None,
                 performance_score: float = 0.0,
                 total_profit: float = 0.0,
                 total_profit_satoshi: Optional[int] = None,
                 actions_count: int = 0,
                 strategy: Dict = None,
                 memory: List[Dict] = None):
        self.agent_id = agent_id
        self.name = name
        self.owner = owner
        self.agent_type = agent_type
        self.status = status
        self.created_at = created_at if created_at is not None else int(time.time())
        self.last_action = last_action if last_action is not None else self.created_at
        self.performance_score = performance_score
        self.actions_count = actions_count
        self.strategy = strategy or {
            "type": "arbitrage",
            "risk_level": "medium",
            "max_position": 1000,
        }
        self.memory: List[Dict] = list(memory or [])
        if total_profit_satoshi is not None:
            self.total_profit_satoshi = max(0, int(total_profit_satoshi))
            self.total_profit = from_satoshi_float(self.total_profit_satoshi)
        else:
            self.total_profit_satoshi = int(to_satoshi(total_profit or 0))
            self.total_profit = from_satoshi_float(self.total_profit_satoshi)

    def predict(self, market_data: Dict) -> Dict:
        features = market_data.get("features") or market_data.get("prices", [])
        if not features:
            return {
                "prediction": 0,
                "confidence": None,
                "model_bound": False,
                "prediction_method": "none",
                "consensus_wired": False,
            }
        avg = sum(features) / len(features)
        return {
            "prediction": avg,
            # No ML model is bound — do not invent a confidence score.
            "confidence": None,
            "model_bound": False,
            "prediction_method": "feature_average",
            "agent_type": self.agent_type,
            "consensus_wired": False,
        }

    def analyze_market(self, data: List[Dict]) -> Dict:
        prices = [d.get("price", 0) for d in data if d.get("price")]
        if len(prices) < 2:
            return {
                "trend": "neutral",
                "confidence": None,
                "heuristic": True,
            }
        trend = (prices[-1] - prices[0]) / prices[0] if prices[0] > 0 else 0
        if trend > 0.05:
            direction = "bullish"
        elif trend < -0.05:
            direction = "bearish"
        else:
            direction = "neutral"
        recommendation = "buy" if trend > 0.02 else "sell" if trend < -0.02 else "hold"
        return {
            "success": True,
            "trend": direction,
            "trend_strength": abs(trend),
            "recommendation": recommendation,
            "price_change_pct": round(trend * 100, 2),
            "confidence": None,
            "heuristic": True,
            "consensus_wired": False,
        }

    def execute_trade(self, trade_type: str, amount: float,
                      price: float) -> Dict:
        return {"success": False, "error": "Trade execution backend not configured"}

    def record_executed_trade(
        self,
        trade_type: str,
        amount: float,
        price: float,
        execution: Dict[str, Any],
    ) -> Dict:
        if not isinstance(execution, dict) or not execution.get("success"):
            return {"success": False, "error": "Trade execution was not successful"}
        status = str(execution.get("status", "filled")).lower()
        if status not in ("filled", "executed", "settled"):
            return {"success": False, "error": f"Trade execution not final: {status}"}
        trade_id = str(execution.get("trade_id") or native.sha256_hex(
            f"{self.agent_id}_{trade_type}_{time.time_ns()}".encode()
        )[:16])
        pnl_sat = (
            int(execution["pnl_satoshi"])
            if execution.get("pnl_satoshi") is not None
            else int(to_satoshi(execution.get("pnl", 0.0)))
        )
        self.total_profit_satoshi = max(0, int(self.total_profit_satoshi) + pnl_sat)
        self.total_profit = from_satoshi_float(self.total_profit_satoshi)
        self.actions_count += 1
        self.last_action = int(time.time())
        self.performance_score = self.total_profit / max(1, self.actions_count)
        record = {
            "trade_id": trade_id,
            "type": trade_type,
            "amount": amount,
            "price": price,
            "pnl": from_satoshi_float(pnl_sat),
            "pnl_satoshi": pnl_sat,
            "venue": execution.get("venue", ""),
            "execution_status": execution.get("status", "filled"),
            "timestamp": int(time.time()),
        }
        self.memory.append(record)
        if len(self.memory) > 500:
            self.memory = self.memory[-500:]
        return {"success": True, **record}

    def to_dict(self) -> Dict:
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "owner": self.owner[:16] + "..." if len(self.owner) > 20 else self.owner,
            "agent_type": self.agent_type,
            "status": self.status,
            "performance_score": round(self.performance_score, 4),
            "total_profit": round(self.total_profit, 4),
            "total_profit_satoshi": int(self.total_profit_satoshi),
            "actions_count": self.actions_count,
            "created_at": self.created_at,
        }

    def to_db(self) -> Dict:
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "owner": self.owner,
            "agent_type": self.agent_type,
            "status": self.status,
            "created_at": self.created_at,
            "last_action": self.last_action,
            "performance_score": self.performance_score,
            "total_profit": self.total_profit,
            "total_profit_satoshi": int(self.total_profit_satoshi),
            "actions_count": self.actions_count,
            "strategy": self.strategy,
            "memory": self.memory,
        }


class AIAgentManager:
    """Manages AI trading agents — persisted in SQLite."""

    CREATE_FEE = 0.01

    def __init__(self, db=None, trade_executor: Optional[Callable[[Dict], Dict]] = None):
        self.db = db
        self.trade_executor = trade_executor
        self.agents: Dict[str, AIAgent] = {}
        self._load_from_db()
        print(f"[AIAgentManager] Initialized ({len(self.agents)} agents, "
              f"persisted={bool(db)})")

    def _load_from_db(self) -> None:
        if not self.db or not hasattr(self.db, "get_ai_agents"):
            return
        for row in self.db.get_ai_agents(limit=500):
            agent = AIAgent(
                agent_id=row["agent_id"],
                name=row["name"],
                owner=row["owner"],
                agent_type=row.get("agent_type", "transformer"),
                status=row.get("status", "active"),
                created_at=row.get("created_at"),
                last_action=row.get("last_action"),
                performance_score=row.get("performance_score", 0),
                total_profit=row.get("total_profit", 0),
                total_profit_satoshi=row.get("total_profit_satoshi"),
                actions_count=row.get("actions_count", 0),
                strategy=row.get("strategy"),
                memory=row.get("memory"),
            )
            self.agents[agent.agent_id] = agent

    def _persist(self, agent: AIAgent) -> None:
        if self.db and hasattr(self.db, "save_ai_agent"):
            self.db.save_ai_agent(agent.to_db())

    def _charge_create_fee(self, owner: str) -> bool:
        if not self.db or not owner:
            return False
        from runtime.amount import apply_store_delta_satoshi

        fee_sat = int(to_satoshi(self.CREATE_FEE))
        if hasattr(self.db, "get_balance_satoshi"):
            if int(self.db.get_balance_satoshi(owner) or 0) < fee_sat:
                return False
        elif hasattr(self.db, "get_balance"):
            if self.db.get_balance(owner) < self.CREATE_FEE:
                return False
        else:
            return False
        return bool(
            apply_store_delta_satoshi(
                self.db, owner, -fee_sat, allow_float_fallback=False
            )
        )

    def create_agent(self, name: str, owner: str,
                     agent_type: str = "transformer") -> Optional[str]:
        if not name or not owner:
            return None
        if not self._charge_create_fee(owner):
            return None
        agent_id = native.sha256_hex(
            f"{name}{owner}{time.time()}".encode()
        )[:16]
        agent = AIAgent(agent_id, name, owner, agent_type)
        self.agents[agent_id] = agent
        self._persist(agent)
        print(f"[AIAgentManager] Created agent '{name}' ({agent_id}) for {owner[:12]}...")
        return agent_id

    def get_agent(self, agent_id: str) -> Optional[AIAgent]:
        return self.agents.get(agent_id)

    def get_all_agents(self) -> List[Dict]:
        return [a.to_dict() for a in self.agents.values()]

    def get_user_agents(self, owner: str) -> List[Dict]:
        return [a.to_dict() for a in self.agents.values() if a.owner == owner]

    def predict(self, agent_id: str, market_data: Dict) -> Dict:
        agent = self.agents.get(agent_id)
        if not agent:
            return {"error": "Agent not found"}
        return agent.predict(market_data)

    def analyze(self, agent_id: str, price_history: List[Dict]) -> Dict:
        agent = self.agents.get(agent_id)
        if not agent:
            return {"error": "Agent not found"}
        return agent.analyze_market(price_history)

    def trade(
        self,
        agent_id: str,
        trade_type: str,
        amount: float,
        price: float,
        *,
        amount_satoshi: int | None = None,
        price_satoshi: int | None = None,
    ) -> Dict:
        from runtime.amount import resolve_amount_satoshi

        agent = self.agents.get(agent_id)
        if not agent:
            return {"success": False, "error": "Agent not found"}
        if agent.status != "active":
            return {"success": False, "error": "Agent is not active"}
        try:
            amt_sat, amount = resolve_amount_satoshi(amount, amount_satoshi)
            px_sat, price = resolve_amount_satoshi(
                price, price_satoshi, field="price"
            )
        except (TypeError, ValueError) as exc:
            return {"success": False, "error": str(exc) or "amount_satoshi_invalid"}
        if amt_sat <= 0 or px_sat <= 0:
            return {"success": False, "error": "Invalid trade parameters"}
        if not self.trade_executor:
            return {"success": False, "error": "Trade execution backend not configured"}
        execution = self.trade_executor({
            "agent_id": agent_id,
            "owner": agent.owner,
            "type": trade_type,
            "amount": amount,
            "amount_satoshi": int(amt_sat),
            "price": price,
            "price_satoshi": int(px_sat),
        })
        if not isinstance(execution, dict) or not execution.get("success"):
            error = execution.get("error", "Trade execution failed") if isinstance(execution, dict) else "Trade execution failed"
            return {"success": False, "error": error}
        result = agent.record_executed_trade(trade_type, amount, price, execution)
        if result.get("success"):
            self._persist(agent)
            if isinstance(result, dict):
                result = dict(result)
                result["amount_satoshi"] = int(amt_sat)
                result["price_satoshi"] = int(px_sat)
                result.setdefault("simulation_only", True)
        return result

    def deactivate(self, agent_id: str) -> bool:
        agent = self.agents.get(agent_id)
        if not agent or agent.status == "inactive":
            return False
        agent.status = "inactive"
        self._persist(agent)
        return True

    def get_stats(self) -> Dict:
        active = sum(1 for a in self.agents.values() if a.status == "active")
        total_profit_sat = sum(
            int(a.total_profit_satoshi) for a in self.agents.values()
        )
        executor_bound = self.trade_executor is not None
        return {
            "total_agents": len(self.agents),
            "active_agents": active,
            "total_profit": from_satoshi_float(total_profit_sat),
            "total_profit_satoshi": int(total_profit_sat),
            "total_trades": sum(a.actions_count for a in self.agents.values()),
            "persisted": bool(self.db),
            "create_fee": self.CREATE_FEE,
            "create_fee_satoshi": int(to_satoshi(self.CREATE_FEE)),
            "model_bound": False,
            "executor_bound": executor_bound,
            "operational": bool(executor_bound),
            "consensus_wired": False,
            "honesty": HONESTY,
            "note": (
                "agent registry"
                + (" + trade executor" if executor_bound else " — no trade executor")
            ),
        }
