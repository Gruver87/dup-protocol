#!/usr/bin/env python3
"""Pin Long-Range host check (ADR 0017 step 2).

Runs the offline labs only. Does not start Docker, a soak, or prod mesh.
Prod JSON must keep feature_long_range false. The lab profile must stay off
chain 778888.

Usage (repo root)::

    python scripts/verify_long_range_host.py
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

PROD_JSON = (
    "docker/node.prod.mesh1.json",
    "docker/node.prod.mesh2.json",
    "docker/node.prod.mesh3.json",
    "docker/node.prod.json",
)

LABS = (
    "scripts/long_range_lab.py",
    "scripts/long_range_p2p_lab.py",
    "scripts/long_range_gossip_lab.py",
)


def _fail(msg: str) -> int:
    print(f"FAIL: {msg}", file=sys.stderr)
    return 1


def _check_profiles() -> str | None:
    for rel in PROD_JSON:
        path = ROOT / rel
        if not path.is_file():
            return f"missing {rel}"
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("feature_long_range") is not False:
            return f"{rel} feature_long_range must be false"
        if int(data.get("chain_id", 0) or 0) != 778888:
            return f"{rel} must stay chain 778888"
    lab = json.loads((ROOT / "node.long_range.lab.json").read_text(encoding="utf-8"))
    if str(lab.get("deployment_mode", "")).lower() != "dev":
        return "lab profile must be dev"
    if int(lab.get("chain_id", 0) or 0) == 778888:
        return "lab profile must not use chain 778888"
    if lab.get("feature_long_range") is not True:
        return "lab profile must arm feature_long_range"
    if lab.get("bridge_enabled") is not False:
        return "lab profile must keep bridge off"
    return None


def main() -> int:
    print("verify_long_range_host (no soak, no docker)", flush=True)
    err = _check_profiles()
    if err:
        return _fail(err)
    print("OK: prod 778888 feature_long_range=false; lab chain is not 778888")
    for rel in LABS:
        print(f">>> {rel}")
        proc = subprocess.run([sys.executable, str(ROOT / rel)], cwd=str(ROOT), check=False)
        if proc.returncode != 0:
            return _fail(f"{rel} exit {proc.returncode}")
        print(f"OK: {rel}")
    print("RESULT: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
