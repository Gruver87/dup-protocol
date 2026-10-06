"""Exp→pin ops: prepare_48h full preflight + secrets angle-bracket placeholders."""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _load_check_secrets():
    path = ROOT / "scripts" / "check_secrets.py"
    spec = importlib.util.spec_from_file_location("check_secrets", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def test_prepare_48h_full_preflight_surface():
    prep = (ROOT / "scripts" / "prepare_48h_soak.ps1").read_text(encoding="utf-8")
    for needle in (
        "MinFreeGb",
        "check_mesh_catchup",
        "probe_prod_mesh",
        "soak_48h_prep.json",
        "MinerHarnessSamples",
        "stop_soak_monitors",
        "--require-wire-probe",
        "--require-libp2p",
        "COMMITTED_STATE_ROOT_OK",
    ):
        assert needle in prep, needle


def test_check_secrets_angle_bracket_placeholder():
    mod = _load_check_secrets()
    assert mod._is_placeholder("<from staging .env>") is True
    assert mod._is_placeholder("changeme_secret") is True
    assert mod._is_placeholder("sk-live-abc123def456ghi789") is False


def test_soak_status_alive_and_glob():
    src = (ROOT / "scripts" / "soak_status.ps1").read_text(encoding="utf-8")
    assert 'LogGlob = "logs/soak_*h*.log"' in src
    assert "ALIVE pid=" in src
    assert "DEAD (monitor gone" in src
