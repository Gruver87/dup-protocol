"""AI sprout honesty — loaded instance must not paint enabled when flag off."""
from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def test_ai_sprout_helpers_fail_closed():
    from api.http import _AI_AGENT_HONESTY, _ai_sprout_enabled

    cfg = SimpleNamespace(feature_ai_agents=False, is_production=True)
    enabled, loaded = _ai_sprout_enabled(
        cfg, object(), feature_attr="feature_ai_agents"
    )
    assert enabled is False
    assert loaded is True
    assert "feature_ai_agents=false" in _AI_AGENT_HONESTY

    cfg2 = SimpleNamespace(feature_ai_validator=True, is_production=False)
    en2, ld2 = _ai_sprout_enabled(
        cfg2, object(), feature_attr="feature_ai_validator"
    )
    assert en2 is True and ld2 is True


def test_ai_http_source_honesty_needles():
    src = (ROOT / "api" / "http.py").read_text(encoding="utf-8")
    assert "_ai_sprout_enabled" in src
    assert "_AI_AGENT_HONESTY" in src
    assert "nft_enabled" in src
    assert "ai_validator_enabled" in src
    chunk = src.split('path == "/ai/validators"')[1].split('elif path == "/ai/proposer"')[0]
    assert "feature_ai_validator" in chunk or "_ai_sprout_enabled" in chunk
    assert "honesty" in chunk
    reg = src.split('path == "/ai/register-validator"')[1].split("elif path ==")[0]
    assert "_ai_sprout_enabled" in reg
    assert "feature_ai_validator" in reg
    agent = src.split('path == "/ai-agent/create"')[1].split('elif path == "/ai-agent/predict"')[0]
    assert "feature_ai_agents" in agent
    stats = src.split('path == "/ai-agent/stats"')[1].split("elif path ==")[0]
    assert "_ai_sprout_enabled" in stats
    deact = src.split('path == "/ai-agent/deactivate"')[1].split("elif path ==")[0]
    assert "_ai_sprout_enabled" in deact


def test_main_ai_nft_feature_defaults_fail_closed():
    src = (ROOT / "main.py").read_text(encoding="utf-8")
    assert 'getattr(config, "feature_nft", False)' in src
    assert 'getattr(config, "feature_ai_agents", False)' in src
    assert 'getattr(config, "feature_ai_validator", False)' in src
    assert 'getattr(config, "feature_nft", True)' not in src
    assert 'getattr(config, "feature_ai_agents", True)' not in src
    assert 'getattr(config, "feature_ai_validator", True)' not in src


def test_feature_flags_sprouts_default_off():
    from features import FeatureFlags

    flags = FeatureFlags()
    assert flags.evm is True
    assert flags.nft is False
    assert flags.ai_agents is False
    assert flags.ai_validator is False
    assert flags.mev is False
    src = (ROOT / "features" / "__init__.py").read_text(encoding="utf-8")
    assert 'getattr(config, "feature_nft", True)' not in src
    assert 'getattr(config, "feature_nft", False)' in src
    assert 'getattr(config, "feature_ai_agents", False)' in src


class _LabModel:
    def predict(self, features, *, context=None):
        return {
            "prediction": float(features[0]),
            "confidence": 0.9,
            "prediction_method": "lab",
        }


def test_unbound_model_sentinel():
    from features.ai_ports import UnboundModel, is_bound_model
    import pytest

    assert is_bound_model(None) is False
    assert is_bound_model(UnboundModel()) is False
    assert is_bound_model(_LabModel()) is True
    with pytest.raises(RuntimeError, match="model_unbound"):
        UnboundModel().predict([1.0])


def test_predict_unbound_no_invented_confidence():
    from features.ai_manager import AIAgent, AIAgentManager

    m = AIAgentManager(db=None)
    agent = AIAgent("id1", "n", "0x" + "1" * 40)
    m.agents[agent.agent_id] = agent
    out = m.predict("id1", {"features": [10.0, 20.0]})
    assert out["prediction"] == 15.0
    assert out["confidence"] is None
    assert out["model_bound"] is False
    assert out["consensus_wired"] is False
    assert m.get_stats()["model_bound"] is False


def test_predict_bound_model_port():
    from features.ai_manager import AIAgent, AIAgentManager

    m = AIAgentManager(db=None, model=_LabModel())
    agent = AIAgent("id2", "n", "0x" + "2" * 40, model=_LabModel())
    m.agents[agent.agent_id] = agent
    out = m.predict("id2", {"features": [7.0, 8.0]})
    assert out["prediction"] == 7.0
    assert out["confidence"] == 0.9
    assert out["model_bound"] is True
    assert m.get_stats()["model_bound"] is True
    m.bind_model(None)
    agent.bind_model(None)
    unbound = m.predict("id2", {"features": [7.0, 8.0]})
    assert unbound["model_bound"] is False
    assert unbound["confidence"] is None
