"""ConsensusAdapter DB bootstrap prefers validators.stake_satoshi (ADR 0021)."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from consensus.adapter import ConsensusAdapter
from runtime.amount import to_satoshi


def test_load_validators_from_db_prefers_stake_satoshi():
    adapter = ConsensusAdapter.__new__(ConsensusAdapter)
    adapter.db = MagicMock()
    adapter.db.get_validators.return_value = [
        {"address": "0x" + "ab" * 20, "stake": 32.0, "stake_satoshi": 32_000_000}
    ]
    adapter.engine = MagicMock()
    adapter.slashing_engine = None
    adapter.validator_registry = None
    registered: list[tuple] = []

    def _reg(address, stake, *, stake_satoshi=None):
        registered.append((address, stake, stake_satoshi))

    adapter._register_validator_all = _reg  # type: ignore[method-assign]
    ConsensusAdapter._load_validators_from_db(adapter)
    assert len(registered) == 1
    assert registered[0][2] == 32_000_000
    assert registered[0][1] == 32.0


def test_load_validators_from_db_mismatch_refuses(tmp_path):
    from storage.database import Database
    from runtime.config import Config

    db = Database(str(tmp_path / "stake.db"))
    addr = "0x" + "cd" * 20
    db.save_validator(addr, 32.0, stake_satoshi=int(to_satoshi(32)))
    # Corrupt twin after save — load must refuse mismatch via resolve_amount_satoshi.
    db.conn.execute(
        "UPDATE validators SET stake_satoshi=? WHERE address=?",
        (1, addr),
    )
    db.conn.commit()

    cfg = Config()
    cfg.deployment_mode = "dev"
    adapter = ConsensusAdapter.__new__(ConsensusAdapter)
    adapter.config = cfg
    adapter.db = db
    adapter.engine = MagicMock()
    adapter.engine.add_validator = MagicMock()
    adapter.slashing_engine = None
    adapter.validator_registry = None
    with pytest.raises(ValueError, match="amount_satoshi_mismatch"):
        ConsensusAdapter._load_validators_from_db(adapter)
