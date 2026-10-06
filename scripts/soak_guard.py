#!/usr/bin/env python3
"""Refuse host-side mesh hammering while a soak monitor is ALIVE.

Mid-soak invariant: full_audit / verify --hard / Max suite must not starve
the live prod mesh (:18180–18182). Disk units and industrial_gate remain OK.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_SOAK_CMD_RE = re.compile(
    r"soak_monitor\.ps1|health_watch\.ps1|start_soak_",
    re.IGNORECASE,
)


def list_soak_monitor_pids() -> list[int]:
    """Return PIDs of host soak/health_watch PowerShell monitors (Windows)."""
    if os.name != "nt":
        return []
    ps = (
        "Get-CimInstance Win32_Process -Filter \"Name='powershell.exe'\" "
        "-ErrorAction SilentlyContinue | "
        "Where-Object { $_.CommandLine -and "
        "($_.CommandLine -match 'soak_monitor\\.ps1|health_watch\\.ps1') } | "
        "Select-Object -ExpandProperty ProcessId"
    )
    try:
        out = subprocess.check_output(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                ps,
            ],
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=15,
        )
    except (subprocess.SubprocessError, OSError, TimeoutError):
        return []
    pids: list[int] = []
    for line in (out or "").splitlines():
        line = line.strip()
        if line.isdigit():
            pids.append(int(line))
    return pids


def soak_active_marker() -> dict | None:
    path = ROOT / "logs" / "soak_active.json"
    if not path.is_file():
        return None
    try:
        import json

        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def refuse_live_mesh_if_soak_alive(*, force: bool = False, context: str = "") -> None:
    """Exit 2 if soak monitor is ALIVE and force is false.

    Exit 2 matches verify_full_blockchain live-mesh-unreachable class
    (operator must choose --force / --skip-live, not paint green).
    """
    if force or os.environ.get("DUP_FORCE_MESH_DURING_SOAK", "").strip() in (
        "1",
        "true",
        "yes",
    ):
        print(
            "WARN: soak-alive guard bypassed "
            f"(force={force} env=DUP_FORCE_MESH_DURING_SOAK) {context}".strip()
        )
        return
    pids = list_soak_monitor_pids()
    if not pids:
        return
    marker = soak_active_marker() or {}
    log_name = marker.get("log_file") or "logs/soak_*.log"
    print("FAIL: soak monitor ALIVE — refuse live mesh hammering")
    print(f"  pids: {', '.join(str(p) for p in pids)}")
    print(f"  active: {log_name}")
    if context:
        print(f"  context: {context}")
    print("  stop:   .\\scripts\\stop_soak_monitors.ps1 -Force")
    print("  status: .\\scripts\\check_soak.ps1")
    print("  bypass: --force-during-soak  OR  DUP_FORCE_MESH_DURING_SOAK=1")
    print("  honesty: mid-soak host Max/full_audit starved API → tip HOL FAIL")
    raise SystemExit(2)


def main() -> int:
    pids = list_soak_monitor_pids()
    marker = soak_active_marker()
    print(f"soak_monitor_pids={pids}")
    print(f"soak_active_json={marker}")
    if pids:
        print("state=ALIVE")
        return 0
    print("state=none")
    return 0


if __name__ == "__main__":
    sys.exit(main())
