"""Exp mid-soak: consensus engines refuse invent stake=100."""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def test_lmd_add_validator_requires_stake():
    from consensus.lmd import LMDTable

    t = LMDTable()
    with pytest.raises(ValueError, match="stake_required"):
        t.add_validator("v1")
    with pytest.raises(ValueError, match="stake_required"):
        t.add_validator("v1", 0)
    t.add_validator("v1", 1000)
    assert t.validator_stake["v1"] == 1000


def test_engine_add_validator_requires_stake():
    from consensus.engine_beacon import ConsensusEngineBeacon
    from consensus.engine_casper import ConsensusEngineCasper
    from consensus.engine_slashing import ConsensusEngineSlashing

    for Eng in (ConsensusEngineBeacon, ConsensusEngineCasper, ConsensusEngineSlashing):
        eng = Eng()
        with pytest.raises(ValueError, match="stake_required"):
            eng.add_validator("v1")
        eng.add_validator("v1", 500)
        assert eng.lmd.validator_stake["v1"] == 500


def test_main_lmd_uses_min_stake_needle():
    src = (ROOT / "main.py").read_text(encoding="utf-8")
    chunk = src.split("LMDTable")[1].split("ConsensusEngineCasper")[0]
    assert "min_stake" in chunk
    assert "add_validator(config.miner_address)" not in chunk


def test_engines_source_no_default_stake_100():
    for rel in (
        "consensus/lmd.py",
        "consensus/engine_beacon.py",
        "consensus/engine_casper.py",
        "consensus/engine_slashing.py",
    ):
        src = (ROOT / rel).read_text(encoding="utf-8")
        assert "stake: int = 100" not in src, rel
        assert "stake_required" in src, rel


def test_pq_status_no_invent_stats_enabled_dict():
    src = (ROOT / "api" / "http.py").read_text(encoding="utf-8")
    chunk = src.split('path == "/pq/status"')[1].split("elif path")[0]
    assert 'get_stats") else {"enabled": True}' not in chunk
