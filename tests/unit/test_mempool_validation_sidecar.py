"""Exp→pin ops: verify_p2p_ci flake honesty + mempool validation sidecar."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_verify_p2p_ci_prod_smoke_wallet_default():
    src = (ROOT / "scripts" / "verify_p2p_ci.py").read_text(encoding="utf-8")
    assert "def _default_prod_smoke_wallet" in src
    assert "data/prod_mesh/wallets/validator-1.wallet.json" in src
    assert "max_attempts = max(need * 12, need + 8)" in src
    assert "Surface body" in src
    assert "exc2" in src


def test_mempool_validation_sidecar_present():
    side = ROOT / "scripts" / "mempool_validation_sidecar.py"
    starter = ROOT / "scripts" / "start_mempool_validation_soak.ps1"
    assert side.is_file()
    assert starter.is_file()
    text = side.read_text(encoding="utf-8")
    assert "NOT 48h" in text
    assert "store_demoted" in text or "demoted" in text
    assert "_refuse_empty_tx" in text
    assert "_admit_smoke" in text
    ps1 = starter.read_text(encoding="utf-8")
    assert "mempool_validation_sidecar.py" in ps1
    assert "NOT 48h" in ps1
