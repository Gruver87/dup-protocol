#!/usr/bin/env python3
"""AI sprout lab — offline self-check (NOT soak / NOT prod flag flip / NOT consensus).

Verifies:
  - AIAgentManager create + satoshi profit dual-write
  - unbound predict honesty (model_bound=False)
  - optional ModelPort binding
  - AIValidatorEngine simulation_only
  - prod mesh JSON keeps feature_ai_*/feature_mev false

Usage:
  python scripts/ai_lab.py
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from features.ai_manager import AIAgentManager, HONESTY as AI_HONESTY
from features.ai_validator import AIValidatorEngine, HONESTY as VAL_HONESTY
from features.mev_analyzer import MEVAnalyzer, Transaction
from runtime.amount import to_satoshi
from storage.database import Database


def _fail(msg: str) -> int:
    print(f"FAIL: {msg}")
    return 1


class _AvgModel:
    """Lab-only ModelPort stand-in (not a real ML model)."""

    def predict(
        self,
        features: Sequence[float],
        *,
        context: Optional[Mapping[str, Any]] = None,
    ) -> Mapping[str, Any]:
        return {
            "prediction": sum(features) / len(features),
            "confidence": 0.5,
            "prediction_method": "lab_avg_model",
        }


def _check_prod_flags() -> Optional[str]:
    meshes = [
        ROOT / "docker" / "node.prod.mesh1.json",
        ROOT / "docker" / "node.prod.mesh2.json",
        ROOT / "docker" / "node.prod.mesh3.json",
    ]
    for path in meshes:
        if not path.is_file():
            return f"missing {path}"
        data = json.loads(path.read_text(encoding="utf-8"))
        for key in ("feature_ai_agents", "feature_ai_validator", "feature_mev"):
            if data.get(key) is not False:
                return f"{path.name}: {key} must be false (got {data.get(key)!r})"
    return None


def main() -> int:
    print("ai_lab — NOT soak / NOT mainnet / NOT consensus wire / NOT prod flag flip")
    print("honesty:", AI_HONESTY)
    print("honesty:", VAL_HONESTY)

    flag_err = _check_prod_flags()
    if flag_err:
        return _fail(flag_err)
    print("OK: prod mesh AI/MEV flags false")

    with tempfile.TemporaryDirectory() as tmp:
        db = Database(str(Path(tmp) / "ai_lab.db"))
        db.initialize()
        owner = "0x" + "a" * 40
        db.set_balance(owner, 10.0)

        mgr = AIAgentManager(db=db)
        stats0 = mgr.get_stats()
        if stats0.get("model_bound") is not False:
            return _fail("unbound manager must report model_bound=False")
        if stats0.get("consensus_wired") is not False:
            return _fail("consensus_wired must be False")
        if stats0.get("executor_bound") is not False:
            return _fail("unbound executor must be False")

        aid = mgr.create_agent("LabBot", owner)
        if not aid:
            return _fail("create_agent failed")

        pred = mgr.predict(aid, {"features": [1.0, 3.0, 5.0]})
        if pred.get("model_bound") is not False:
            return _fail("unbound predict must be model_bound=False")
        if pred.get("confidence") is not None:
            return _fail("unbound predict must not invent confidence")
        if pred.get("prediction") != 3.0:
            return _fail(f"feature average expected 3.0 got {pred.get('prediction')}")

        mgr.bind_model(_AvgModel())
        pred2 = mgr.predict(aid, {"features": [2.0, 4.0]})
        if pred2.get("model_bound") is not True:
            return _fail("bound predict must be model_bound=True")
        if pred2.get("confidence") != 0.5:
            return _fail("bound model confidence not surfaced")

        def executor(order):
            return {
                "success": True,
                "trade_id": "lab-1",
                "pnl_satoshi": int(to_satoshi(1.5)),
                "status": "filled",
                "venue": "lab",
            }

        mgr.trade_executor = executor
        out = mgr.trade(aid, "buy", 1.0, 100.0)
        if not out.get("success"):
            return _fail(f"trade failed: {out}")
        if out.get("pnl_satoshi") != int(to_satoshi(1.5)):
            return _fail("pnl_satoshi mismatch")

        agent = mgr.get_agent(aid)
        assert agent is not None
        if agent.total_profit_satoshi != int(to_satoshi(1.5)):
            return _fail("agent total_profit_satoshi mismatch")

        row = db.get_ai_agent(aid)
        if not row or int(row.get("total_profit_satoshi") or 0) != int(to_satoshi(1.5)):
            return _fail("persisted total_profit_satoshi mismatch")

        # validator sim
        eng = AIValidatorEngine()
        eng.add_validator("0xv1", stake_satoshi=int(to_satoshi(1000)))
        vst = eng.get_stats()
        if vst.get("consensus_wired") is not False:
            return _fail("validator must not be consensus_wired")
        if vst.get("total_stake_satoshi") != int(to_satoshi(1000)):
            return _fail("validator stake_satoshi mismatch")
        mev_stub = eng.detect_mev_opportunity([])
        if mev_stub.get("invented_numbers") is not False:
            return _fail("validator MEV stub must not invent numbers")

        # MEV analyzer heuristic (analysis sprout)
        mev = MEVAnalyzer(db=db)
        txs = [
            Transaction("0xh1", "0xa", "0xb", 10.0, 100, 1),
            Transaction("0xh2", "0xc", "0xd", 5.0, 50, 2),
        ]
        sig = mev.detect_sandwich_opportunity(txs)
        if sig.get("executed") is not False:
            return _fail("MEV signal must be executed=False")
        st = mev.get_statistics()
        if st.get("consensus_wired") is not False:
            return _fail("MEV analyzer must not claim consensus_wired")

        from features import ai_ops

        if "not consensus" not in ai_ops.HONESTY.lower():
            return _fail("ai_ops.HONESTY missing")
        findings = ai_ops.classify_anomaly(
            ready={"status": "not_ready", "checks": {"state_consistent": False}},
            status={},
        )
        if not findings:
            return _fail("ai_ops must flag not_ready")

        # Forge must not wire AI validator performance (source needle).
        main_py = (ROOT / "main.py").read_text(encoding="utf-8")
        if "ai_validator.update_performance" in main_py:
            return _fail("forge must not call ai_validator.update_performance")

        http_py = (ROOT / "api" / "http.py").read_text(encoding="utf-8")
        if "_ai_sprout_enabled" not in http_py:
            return _fail("HTTP must gate AI sprouts via _ai_sprout_enabled")
        if 'feature_attr="feature_ai_agents"' not in http_py:
            return _fail("HTTP /ai-agent/* must gate on feature_ai_agents")

        from features import FeatureFlags

        if not hasattr(FeatureFlags(), "ai_validator"):
            return _fail("FeatureFlags must include ai_validator")

        try:
            db.close()
        except Exception:
            pass

    print("OK: ai_lab agents + model port + validator + mev + ai_ops + HTTP gate honesty")
    print("RESULT: PASS ai_lab")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
