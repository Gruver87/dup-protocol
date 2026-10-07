"""AI sprout harden — model port, satoshi profit, validator honesty (not consensus)."""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from features.ai_manager import AIAgentManager
from features.ai_ports import UnboundModel, is_bound_model
from features.ai_validator import AIValidatorEngine
from runtime.amount import to_satoshi
from storage.database import Database


class _LabModel:
    def predict(self, features, *, context=None):
        return {
            "prediction": float(features[0]),
            "confidence": 0.9,
            "prediction_method": "lab",
        }


def test_unbound_model_sentinel():
    assert is_bound_model(None) is False
    assert is_bound_model(UnboundModel()) is False
    assert is_bound_model(_LabModel()) is True
    with pytest.raises(RuntimeError, match="model_unbound"):
        UnboundModel().predict([1.0])


def test_predict_unbound_no_invented_confidence():
    m = AIAgentManager(db=None)
    # bypass fee by injecting agent
    from features.ai_manager import AIAgent

    agent = AIAgent("id1", "n", "0x" + "1" * 40)
    m.agents[agent.agent_id] = agent
    out = m.predict("id1", {"features": [10.0, 20.0]})
    assert out["prediction"] == 15.0
    assert out["confidence"] is None
    assert out["model_bound"] is False
    assert out["consensus_wired"] is False


def test_predict_bound_model_port():
    m = AIAgentManager(db=None, model=_LabModel())
    from features.ai_manager import AIAgent

    agent = AIAgent("id2", "n", "0x" + "2" * 40, model=_LabModel())
    m.agents[agent.agent_id] = agent
    out = m.predict("id2", {"features": [7.0, 8.0]})
    assert out["prediction"] == 7.0
    assert out["confidence"] == 0.9
    assert out["model_bound"] is True


def test_profit_satoshi_persist_roundtrip():
    tmp = tempfile.mkdtemp()
    db = Database(os.path.join(tmp, "ai.db"))
    db.initialize()
    owner = "0x" + "a" * 40
    db.set_balance(owner, 5.0)

    def executor(_order):
        return {
            "success": True,
            "trade_id": "t1",
            "pnl_satoshi": int(to_satoshi(2.25)),
            "status": "filled",
            "venue": "t",
        }

    m = AIAgentManager(db=db, trade_executor=executor)
    aid = m.create_agent("Bot", owner)
    assert aid
    out = m.trade(aid, "buy", 1.0, 1.0)
    assert out["success"] is True
    assert out["pnl_satoshi"] == int(to_satoshi(2.25))
    stats = m.get_stats()
    assert stats["executor_bound"] is True
    assert stats["total_profit_satoshi"] == int(to_satoshi(2.25))
    assert stats["consensus_wired"] is False

    m2 = AIAgentManager(db=db)
    agent = m2.get_agent(aid)
    assert agent is not None
    assert agent.total_profit_satoshi == int(to_satoshi(2.25))


def test_validator_simulation_only_stake_satoshi():
    eng = AIValidatorEngine()
    eng.add_validator("0xv", stake_satoshi=1_500_000)
    st = eng.get_stats()
    assert st["total_stake_satoshi"] == 1_500_000
    assert st["consensus_wired"] is False
    assert st["simulation_only"] is True
    eng.update_performance("0xv", True)
    st2 = eng.get_stats()
    assert st2["total_rewards_satoshi"] == int(to_satoshi(100))


def test_prod_mesh_ai_flags_remain_false():
    for name in ("node.prod.mesh1.json", "node.prod.mesh2.json", "node.prod.mesh3.json"):
        path = ROOT / "docker" / name
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data.get("feature_ai_agents") is False
        assert data.get("feature_ai_validator") is False
        assert data.get("feature_mev") is False


def test_ops_anomaly_classifier():
    from features.ai_ops import classify_anomaly

    assert classify_anomaly(
        ready={"status": "ready", "checks": {"state_consistent": True}},
        status={"height": 10, "peer_count": 2, "mesh_min_peers": 2, "sync_stalled": False},
    ) == []
    findings = classify_anomaly(
        ready={"status": "not_ready", "checks": {"state_consistent": False}},
        status={"height": 0, "peer_count": 0, "mesh_min_peers": 2, "sync_stalled": True},
    )
    codes = {f["code"] for f in findings}
    assert "ready_not_ready" in codes
    assert "check_state_consistent_false" in codes
    assert "sync_stalled" in codes
