"""AI/NFT/DAO honesty — satoshi twins, no invented quorum, no invented confidence."""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def test_ai_manager_honesty_and_profit_satoshi():
    from features.ai_manager import HONESTY, AIAgentManager
    from runtime.amount import to_satoshi
    from storage.database import Database

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
    assert stats["honesty"] == HONESTY

    m2 = AIAgentManager(db=db)
    agent = m2.get_agent(aid)
    assert agent is not None
    assert agent.total_profit_satoshi == int(to_satoshi(2.25))


def test_nft_stats_total_value_satoshi():
    from features.nft import NFTMarketplace

    nft = NFTMarketplace(db=None)
    st = nft.get_stats()
    assert isinstance(st["total_value_satoshi"], int)
    assert "mint_fee_satoshi" in st
    listed = sum(int(t.price_satoshi) for t in nft.tokens.values() if t.for_sale)
    assert st["total_value_satoshi"] == listed


def test_dao_vote_does_not_invent_one_validator():
    src = (ROOT / "runtime" / "pool_locks.py").read_text(encoding="utf-8")
    chunk = src.split("def dao_vote")[1].split("def get_status")[0]
    assert "total_validators = 1" not in chunk
    assert "total_validators <= 0" in chunk


def test_ai_validator_stake_satoshi():
    from features.ai_validator import HONESTY, AIValidatorEngine
    from runtime.amount import to_satoshi

    eng = AIValidatorEngine()
    eng.add_validator("0xv", stake_satoshi=1_500_000)
    st = eng.get_stats()
    assert st["total_stake_satoshi"] == 1_500_000
    assert st["honesty"] == HONESTY
    eng.update_performance("0xv", True)
    assert eng.get_stats()["total_rewards_satoshi"] == int(to_satoshi(100))
