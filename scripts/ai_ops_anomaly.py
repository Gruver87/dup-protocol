#!/usr/bin/env python3
"""Off-node AI/ops anomaly helper — read-only status triage (NOT consensus / NOT soak).

Uses simple heuristics on node /status?probe=1 + /health/ready. Optional live mesh;
offline mode validates the classifier against fixtures.

Does **not** flip feature flags, does **not** submit txs, does **not** touch tip-safety.
"""

from __future__ import annotations

import argparse
import json
import socket
import sys
import urllib.request
from pathlib import Path
from typing import Any, Dict
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


from features.ai_ops import classify_anomaly


def _port_open(host: str, port: int, timeout: float = 0.4) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _http_get_json(url: str, timeout: float = 5.0) -> Dict[str, Any]:
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
    return json.loads(raw.decode("utf-8"))


def offline_self_check() -> int:
    """Fixture-driven classifier check (no network)."""
    ok_ready = {"status": "ready", "checks": {"state_consistent": True, "peers_alive": True}}
    ok_status = {"height": 100, "peer_count": 2, "mesh_min_peers": 2, "sync_stalled": False}
    if classify_anomaly(ready=ok_ready, status=ok_status):
        print("FAIL: healthy fixture should yield no findings")
        return 1

    bad = classify_anomaly(
        ready={
            "status": "not_ready",
            "checks": {"state_consistent": False, "peers_alive": False},
        },
        status={"height": 0, "peer_count": 0, "mesh_min_peers": 2, "sync_stalled": True},
    )
    codes = {f["code"] for f in bad}
    needed = {
        "ready_not_ready",
        "check_state_consistent_false",
        "check_peers_alive_false",
        "sync_stalled",
        "under_mesh",
        "height_zero",
    }
    if not needed.issubset(codes):
        print(f"FAIL: missing codes {needed - codes}; got {codes}")
        return 1
    print("OK: offline anomaly classifier")
    return 0


def live_probe(base_url: str) -> int:
    parsed = urlparse(base_url)
    host = parsed.hostname or "127.0.0.1"
    port = int(parsed.port or (443 if parsed.scheme == "https" else 80))
    if not _port_open(host, port):
        print(f"SKIP: live probe — {host}:{port} not open")
        return 0
    base = base_url.rstrip("/")
    try:
        ready = _http_get_json(f"{base}/health/ready")
        status = _http_get_json(f"{base}/status?probe=1")
    except Exception as exc:
        print(f"WARN: live fetch failed: {exc}")
        return 0
    findings = classify_anomaly(ready=ready, status=status)
    print(
        json.dumps(
            {
                "base_url": base,
                "height": status.get("height"),
                "peer_count": status.get("peer_count"),
                "ready": ready.get("status"),
                "findings": findings,
                "honesty": "ops anomaly helper — NOT soak / NOT consensus / NOT AI forge",
            },
            indent=2,
        )
    )
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="AI/ops anomaly helper (NOT soak)")
    ap.add_argument("--base-url", default="", help="optional live node base URL")
    ap.add_argument("--offline-only", action="store_true")
    args = ap.parse_args()
    print("ai_ops_anomaly — NOT soak / NOT mainnet / NOT consensus wire")
    rc = offline_self_check()
    if rc != 0:
        return rc
    if args.offline_only:
        print("RESULT: PASS ai_ops_anomaly (offline)")
        return 0
    if args.base_url.strip():
        live_probe(args.base_url.strip())
    else:
        for port in (18180, 18181, 18182):
            if _port_open("127.0.0.1", port):
                print(f"INFO: probing http://127.0.0.1:{port}")
                live_probe(f"http://127.0.0.1:{port}")
                break
        else:
            print("SKIP: no live mesh ports 18180–18182")
    print("RESULT: PASS ai_ops_anomaly")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
