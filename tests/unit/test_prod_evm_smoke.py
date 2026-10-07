#!/usr/bin/env python3
import os
import sys
from pathlib import Path

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from prod_evm_smoke import DEPLOY_BYTECODE, _storage_ok


def test_deploy_bytecode_non_empty():
    assert len(DEPLOY_BYTECODE) >= 8


def test_storage_ok_accepts_slot_one():
    assert _storage_ok(
        "0x0000000000000000000000000000000000000000000000000000000000000001"
    )


def test_storage_ok_rejects_zero():
    assert not _storage_ok(
        "0x0000000000000000000000000000000000000000000000000000000000000000"
    )


def test_prod_evm_smoke_satoshi_and_force_catchup_needles():
    src = Path("scripts/prod_evm_smoke.py").read_text(encoding="utf-8")
    assert '"amount_satoshi": 0' in src
    assert '"value_satoshi": 0' in src
    assert "_force_prod_mesh_catchup" in src
    assert "_mesh_tip_snapshot" in src
    assert "mesh tip snapshot failed after catchup" in src


def test_sync_engine_logger_honesty_needles():
    src = Path("sync/sync_engine.py").read_text(encoding="utf-8")
    assert "print(" not in src
    assert 'logger.warning(f"[Sync] Catch-up refused:' in src
    assert 'logger.warning("   [Sync] peer state_root wire probe failed: timeout/empty")' in src
    assert 'logger.warning("   [Sync] blockchain missing get_state_root — fail-closed")' in src
    assert 'logger.info("[Sync] Already in progress")' in src
