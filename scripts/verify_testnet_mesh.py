#!/usr/bin/env python3
"""Verify public testnet Docker mesh (seed + validators on :19080+)."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime.harness_honesty import harness_smoke_ok as _harness_smoke_ok

DEFAULT_SEED = "http://127.0.0.1:19080"
DEFAULT_MESH2 = ("http://127.0.0.1:19081",)
DEFAULT_MESH3 = (
    "http://127.0.0.1:19081",
    "http://127.0.0.1:19082",
)
EXPECTED_CHAIN_ID = 77777


def _api(url: str, timeout: float = 10.0) -> dict[str, Any]:
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def _probe_health(base_url: str, timeout: float = 5.0) -> bool:
    try:
        row = _api(f"{base_url.rstrip('/')}/health/ready", timeout=timeout)
        return str(row.get("status", "")).lower() == "ready"
    except (urllib.error.URLError, TimeoutError, OSError, ValueError, json.JSONDecodeError):
        return False


def verify_testnet_mesh(
    *,
    seed_url: str = DEFAULT_SEED,
    validator_urls: list[str] | None = None,
    wait_sec: int = 0,
) -> tuple[list[str], list[str], dict[str, Any]]:
    import time

    errors: list[str] = []
    warnings: list[str] = []
    followers = [u.rstrip("/") for u in (validator_urls or []) if u]
    urls = [seed_url.rstrip("/"), *followers]

    deadline = time.time() + max(0, wait_sec)
    reachable: list[str] = []
    while True:
        reachable = [u for u in urls if _probe_health(u)]
        if len(reachable) == len(urls):
            # Also wait for height catch-up when asked (Mesh3 after recreate).
            if wait_sec > 0 and len(reachable) >= 2:
                try:
                    heights = [
                        int((_api(f"{u}/status", timeout=8).get("height", 0) or 0))
                        for u in reachable
                    ]
                    if heights and max(heights) - min(heights) <= 1:
                        break
                except (urllib.error.URLError, TimeoutError, OSError, ValueError, json.JSONDecodeError):
                    pass
            else:
                break
        if time.time() >= deadline:
            break
        time.sleep(3)

    nodes: list[dict[str, Any]] = []
    roles = ["seed"] + [f"validator{i}" for i in range(1, len(followers) + 1)]
    for i, url in enumerate(urls):
        role = roles[i] if i < len(roles) else f"node{i}"
        row: dict[str, Any] = {"url": url, "role": role}
        if url not in reachable:
            errors.append(f"{role} not reachable at {url}")
            nodes.append(row)
            continue
        row["reachable"] = True
        try:
            st = _api(f"{url}/status", timeout=10)
            row["height"] = int(st.get("height", 0) or 0)
            row["peers"] = int(st.get("peers", st.get("peer_count", 0)) or 0)
            row["chain_id"] = int(st.get("chain_id", 0) or 0)
            if row["chain_id"] != EXPECTED_CHAIN_ID:
                errors.append(f"{role} chain_id={row['chain_id']} expected {EXPECTED_CHAIN_ID}")
        except (urllib.error.URLError, TimeoutError, OSError, ValueError, json.JSONDecodeError) as exc:
            errors.append(f"{role} /status: {exc}")
        try:
            harness = _api(f"{url}/chain/consistency/harness?quick=1&peer_timeout=5", timeout=25)
            row["harness_healthy"] = bool(harness.get("harness_healthy"))
            row["tip_state_aligned"] = bool(harness.get("tip_state_aligned"))
            row["harness_smoke_ok"] = _harness_smoke_ok(harness)
            if not row["harness_smoke_ok"]:
                failed = harness.get("failed_checks") or []
                errors.append(f"{role} harness unhealthy failed={failed}")
            elif not row["harness_healthy"]:
                warnings.append(
                    f"{role} harness soft-PASS (solo/soft P2P flags; "
                    f"failed={harness.get('failed_checks') or []})"
                )
        except (urllib.error.URLError, TimeoutError, OSError, ValueError, json.JSONDecodeError) as exc:
            warnings.append(f"{role} harness: {exc}")
        nodes.append(row)

    if len(reachable) >= 2:
        heights = [n.get("height", 0) for n in nodes if n.get("reachable")]
        if heights and max(heights) - min(heights) > 1:
            errors.append(f"height spread across mesh: {heights}")

    meta_mesh: dict[str, Any] = {}
    if reachable:
        leader = reachable[0]
        try:
            mesh = _api(f"{leader}/testnet/mesh", timeout=12)
            state_consistent = bool(mesh.get("state_consistent"))
            meta_mesh = {
                "peer_count": mesh.get("peer_count"),
                "expected_peers": mesh.get("expected_peers"),
                "mesh_healthy": mesh.get("mesh_healthy"),
                "height_aligned": mesh.get("height_aligned"),
                "state_consistent": state_consistent,
            }
            min_peers = len(urls) - 1
            peer_count = int(mesh.get("peer_count") or 0)
            height_aligned = bool(mesh.get("height_aligned"))
            if len(reachable) >= 2:
                if peer_count < min_peers or not height_aligned:
                    errors.append(
                        f"seed mesh incomplete peer_count={peer_count} "
                        f"expected_cfg={mesh.get('expected_peers')} "
                        f"height_aligned={height_aligned} "
                        f"(need >={min_peers} peers for {len(urls)}-node mesh)"
                    )
                elif not mesh.get("mesh_healthy"):
                    # Soft-PASS only when peers+heights OK *and* state roots agree.
                    # mesh_healthy=false with state_consistent=false is FAIL
                    # (do not greenwash tip/state divergence).
                    if state_consistent:
                        warnings.append(
                            f"seed mesh_healthy=false soft-PASS "
                            f"peer_count={peer_count} "
                            f"expected_cfg={mesh.get('expected_peers')} "
                            f"state_consistent=true "
                            f"height_aligned={height_aligned}"
                        )
                    else:
                        errors.append(
                            f"seed mesh_healthy=false and state_consistent=false "
                            f"peer_count={peer_count} "
                            f"expected_cfg={mesh.get('expected_peers')} "
                            f"height_aligned={height_aligned}"
                        )
            elif len(reachable) == 1:
                warnings.append("solo seed — start validator profile for mesh demo")
        except (urllib.error.URLError, TimeoutError, OSError, ValueError, json.JSONDecodeError) as exc:
            errors.append(f"seed /testnet/mesh: {exc}")

    meta: dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "chain_id": EXPECTED_CHAIN_ID,
        "nodes": nodes,
        "reachable": len(reachable),
        "expected": len(urls),
        "mesh": meta_mesh,
        "ready": not errors,
    }

    return errors, warnings, meta


def write_report(errors: list[str], warnings: list[str], meta: dict[str, Any]) -> Path:
    out = ROOT / "logs" / "testnet_mesh_verify.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = {"ok": not errors, "errors": errors, "warnings": warnings, **meta}
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify public testnet mesh (chain 77777)")
    parser.add_argument("--seed-url", default=DEFAULT_SEED)
    parser.add_argument("--validator-url", default="", help="Single extra node URL")
    parser.add_argument("--mesh", action="store_true", help="2-node mesh (:19081)")
    parser.add_argument("--mesh3", action="store_true", help="3-node mesh (:19081/:19082)")
    parser.add_argument("--wait", type=int, default=0, help="Seconds to wait for nodes")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    validator_urls: list[str] = []
    if args.mesh3:
        validator_urls = list(DEFAULT_MESH3)
    elif args.mesh:
        validator_urls = list(DEFAULT_MESH2)
    elif args.validator_url:
        validator_urls = [args.validator_url]

    errors, warnings, meta = verify_testnet_mesh(
        seed_url=args.seed_url,
        validator_urls=validator_urls,
        wait_sec=args.wait,
    )
    report = write_report(errors, warnings, meta)

    if args.json:
        print(json.dumps({"ok": not errors, "errors": errors, "warnings": warnings, "report": str(report), **meta}, indent=2))
    else:
        label = "3-node" if args.mesh3 else "2-node" if args.mesh or validator_urls else "solo"
        print("=" * 60)
        print(f"TESTNET MESH VERIFY ({label}, chain 77777)")
        print("=" * 60)
        if errors:
            print("RESULT: FAIL")
            for err in errors:
                print(f"  - {err}")
        else:
            print("RESULT: OK")
        for warn in warnings:
            print(f"  WARN: {warn}")
        print(f"Report: {report}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
