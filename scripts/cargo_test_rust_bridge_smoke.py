#!/usr/bin/env python3
"""Run ``cargo test`` on the Rust bridge CLI crate — smoke-only honesty.

``bridge/rust_bridge`` is a [[bin]] crate (``abs_bridge_bin``). It has no
``[[test]]`` / ``tests/`` / ``#[test]`` modules. ``cargo test`` therefore
prints ``running 0 tests`` with exit 0 after a compile. That is **not**
behavioral verification.

CLI behavior is covered by Python ``tests/unit/test_rust_bridge_cli.py``
and ``tests/unit/test_rust_bridge_e2e.py`` (not this script).

Does not start soak. Does not rebuild Docker.

Usage (repo root)::

    python scripts/cargo_test_rust_bridge_smoke.py
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "bridge" / "rust_bridge" / "Cargo.toml"
SRC = ROOT / "bridge" / "rust_bridge" / "src" / "main.rs"


def main() -> int:
    print("Honesty: rust_bridge cargo test is CLI compile/harness smoke.")
    print("  Expected: running 0 tests (crate has no Rust unit tests).")
    print("  Not: lock/confirm/L1 proof coverage. See tests/unit/test_rust_bridge_*.py")
    if not MANIFEST.is_file() or not SRC.is_file():
        print("FAIL: rust_bridge manifest or src/main.rs missing")
        return 1
    toml = MANIFEST.read_text(encoding="utf-8")
    if "[[test]]" in toml:
        print("FAIL: Cargo.toml now has [[test]] — update this smoke script")
        return 1
    cargo = shutil.which("cargo")
    if cargo is None:
        print("FAIL: cargo not on PATH")
        return 127
    proc = subprocess.run(
        [cargo, "test", "--manifest-path", str(MANIFEST)],
        cwd=str(ROOT),
    )
    if proc.returncode != 0:
        print(f"FAIL: cargo test rust_bridge rc={proc.returncode}")
        return proc.returncode
    print("OK: rust_bridge cargo test smoke (0 crate tests expected; not verification)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
