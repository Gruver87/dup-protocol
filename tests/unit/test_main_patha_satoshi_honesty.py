#!/usr/bin/env python3
"""Needles: PathA ahead-refuse log + main stake satoshi / genesis prod raise."""

from pathlib import Path


def test_path_a_ahead_refuse_get_block_logged():
    src = Path("sync/catchup/path_a.py").read_text(encoding="utf-8")
    assert "[PathA] get_block(%s) for ahead-refuse failed" in src
    assert "[PathA] needs_genesis check failed" in src


def test_main_slashing_and_registry_register_via_to_satoshi():
    src = Path("main.py").read_text(encoding="utf-8")
    assert "to_satoshi as _to_sat_slash" in src
    assert "to_satoshi as _to_sat_reg" in src
    assert "int(_to_sat_slash(config.min_stake))" in src
    assert "int(_to_sat_reg(config.min_stake))" in src
    # Do not pass float ABS / bare int(min_stake) into satoshi stakes.
    assert "register_validator(config.miner_address, config.min_stake)" not in src
    assert "register_validator(\n                    config.miner_address, int(config.min_stake)\n                )" not in src


def test_main_genesis_allocation_prod_fail_closed():
    src = Path("main.py").read_text(encoding="utf-8")
    assert 'Genesis allocation failed: %s' in src
    assert 'deployment_mode", "")).lower() in' in src or 'deployment_mode", "")).lower() == "prod"' in src
    # Pin ADR 0015 SecretManager prod refuse must remain.
    assert "prod SecretManager init failed (fail-closed ADR 0015)" in src
