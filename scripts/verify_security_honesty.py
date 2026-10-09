#!/usr/bin/env python3
"""Operator check for security-honesty waves (cf6d236a / 434c143a).

Does NOT start soak or Docker mesh. Static needles + unit tests;
optional ``--gate`` runs industrial_gate.

Usage:
  python scripts/verify_security_honesty.py
  python scripts/verify_security_honesty.py --gate
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

UNIT_TESTS = (
    "tests/unit/test_harness_honesty.py",
    "tests/unit/test_verify_testnet_mesh.py",
    "tests/unit/test_verify_p2p_tls_mesh.py",
    "tests/unit/test_verify_prod_mesh_probe.py",
    "tests/unit/test_prod_smoke.py",
)

# (relpath, must-contain substrings)
NEEDLES: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "runtime/harness_honesty.py",
        ("def harness_smoke_ok", 'all(p.get("match") is True'),
    ),
    (
        "scripts/verify_testnet_mesh.py",
        (
            "from runtime.harness_honesty import",
            "if state_consistent:",
            "state_consistent=false",
        ),
    ),
    (
        "scripts/verify_p2p_tls_mesh.py",
        (
            'block.get("feature_libp2p") is True',
            'meta["ready"] = False',
            'meta["not_applicable"] = True',
        ),
    ),
    (
        "scripts/verify_prod_mesh_probe.py",
        ("from runtime.harness_honesty import", "harness_smoke_ok"),
    ),
    (
        "scripts/verify_p2p_ci.py",
        ("from runtime.harness_honesty import", "harness_smoke_ok"),
    ),
    (
        "scripts/soak_preflight.py",
        ("from runtime.harness_honesty import", "harness_smoke_ok"),
    ),
    (
        "scripts/prod_smoke.py",
        ("from runtime.harness_honesty import",),
    ),
    (
        "api/http.py",
        ('"p2p_flag_consistent"', '"wire_consistent"'),
    ),
    (
        "scripts/industrial_gate.py",
        (
            "SOAK_VOID_HOST_POWEROFF_2026-10-08.txt",
            "runtime/harness_honesty.py",
            "verify_testnet_mesh soft-PASS must require state_consistent",
        ),
    ),
    (
        "scripts/health_watch_core.ps1",
        ("function Test-HarnessSmokeOk", "HarnessSmokeOk"),
    ),
    (
        "scripts/health_watch.ps1",
        ("HarnessSmokeOk",),
    ),
)

VOID_PACK = (
    ROOT
    / "docs"
    / "evidence"
    / "runs"
    / "pin-libp2p-cutover-pending"
    / "SOAK_VOID_HOST_POWEROFF_2026-10-08.txt"
)


def _check_needles() -> list[str]:
    errors: list[str] = []
    for rel, needles in NEEDLES:
        path = ROOT / rel
        if not path.is_file():
            errors.append(f"missing file: {rel}")
            continue
        text = path.read_text(encoding="utf-8")
        for needle in needles:
            if needle not in text:
                errors.append(f"{rel}: missing needle {needle!r}")
    if not VOID_PACK.is_file():
        errors.append(f"missing VOID pack: {VOID_PACK.relative_to(ROOT)}")
    return errors


def _run_pytest() -> int:
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        *UNIT_TESTS,
        "-q",
        "--tb=line",
    ]
    print(">>>", " ".join(cmd))
    return int(subprocess.call(cmd, cwd=str(ROOT)))


def _run_gate() -> int:
    cmd = [sys.executable, str(ROOT / "scripts" / "industrial_gate.py")]
    print(">>>", " ".join(cmd))
    return int(subprocess.call(cmd, cwd=str(ROOT)))


def _demo_harness_smoke() -> list[str]:
    """Live import smoke of the shared helper (no network)."""
    sys.path.insert(0, str(ROOT))
    from runtime.harness_honesty import harness_smoke_ok

    errors: list[str] = []
    if not harness_smoke_ok({"harness_healthy": True}):
        errors.append("harness_smoke_ok(healthy) expected True")
    if harness_smoke_ok(
        {
            "harness_healthy": False,
            "failed_checks": ["p2p_state_consistent"],
            "peers": [{"match": False}],
            "live_state_root": "abc",
        }
    ):
        errors.append("peered soft without match must be False")
    if not harness_smoke_ok(
        {
            "harness_healthy": False,
            "failed_checks": ["p2p_state_consistent"],
            "peers": [{"match": True}],
            "live_state_root": "abc",
        }
    ):
        errors.append("peered soft with match must be True")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify security-honesty harden (no soak)"
    )
    parser.add_argument(
        "--gate",
        action="store_true",
        help="Also run python scripts/industrial_gate.py",
    )
    parser.add_argument(
        "--needles-only",
        action="store_true",
        help="Skip pytest (static needles + import demo only)",
    )
    args = parser.parse_args()

    def _out(msg: str = "") -> None:
        print(msg, flush=True)

    _out("=" * 60)
    _out("SECURITY HONESTY VERIFY (pin / no soak)")
    _out("=" * 60)

    errors = _check_needles()
    errors.extend(_demo_harness_smoke())
    if errors:
        _out("RESULT: FAIL (needles / import)")
        for err in errors:
            _out(f"  - {err}")
        return 1
    _out("OK: needles + harness_smoke_ok import demo")

    if not args.needles_only:
        rc = _run_pytest()
        if rc != 0:
            _out(f"RESULT: FAIL (pytest rc={rc})")
            return rc
        _out("OK: unit tests")

    if args.gate:
        rc = _run_gate()
        if rc != 0:
            _out(f"RESULT: FAIL (industrial_gate rc={rc})")
            return rc
        _out("OK: industrial_gate")

    _out("RESULT: PASS")
    _out("Note: soak not run; VOID pack presence checked only.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
