"""Exp→pin ops: shard_devnet env pin + audit engagement surface."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_start_shard_devnet_restores_lab_env_pin():
    src = (ROOT / "scripts" / "start_shard_devnet.ps1").read_text(encoding="utf-8")
    assert "Restore-LabEnvPin" in src
    assert 'DEPLOYMENT_MODE = "dev"' in src or "$env:DEPLOYMENT_MODE = \"dev\"" in src
    assert "FEATURE_LONG_RANGE" in src
    assert "RESULT: FAIL shard devnet" in src
    assert "RESULT: PASS shard devnet" in src


def test_audit_phase_and_engagement_scripts_present():
    for rel in (
        "scripts/verify_audit_phase.ps1",
        "scripts/verify_audit_90d_all.ps1",
        "scripts/verify_audit_engagement_prep.ps1",
        "scripts/start_pre48h_maxload_2h.ps1",
        "docs/DILIGENCE_BRIEF.md",
        "docs/EXTERNAL_AUDIT_ENGAGEMENT.md",
        "docs/DEMO_RUNBOOK.md",
        "docs/CEREMONY_DRY_RUN.md",
        "docs/FIRM_OUTREACH_LETTER.md",
        "docs/adr/0023-absolute-vm-opcode-map.md",
    ):
        assert (ROOT / rel).is_file(), rel
    diligence = (ROOT / "docs" / "DILIGENCE_BRIEF.md").read_text(encoding="utf-8")
    assert "dup-protocol" in diligence
    # Pin libp2p soak disclosure: VOID (2026-10-08) or legacy deferred wording.
    dlow = diligence.lower()
    assert (
        ("void" in dlow and "libp2p" in dlow and "not pass" in dlow)
        or "libp2p 48h soak deferred" in dlow
        or "48h soak deferred" in dlow
    )
    assert "3c801b87" not in diligence  # Exp pack must not be cited as pin evidence
