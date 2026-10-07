"""Off-node AI/ops anomaly heuristics (read-only).

Not consensus-wired. Used by ``scripts/ai_ops_anomaly.py`` and unit tests.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

HONESTY = (
    "ai_ops sprout: off-node heuristic triage only — not consensus / "
    "not mainnet / simulation_only"
)


def classify_anomaly(
    *,
    ready: Optional[Dict[str, Any]] = None,
    status: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """Return list of anomaly findings (empty = no flags). Heuristic only."""
    findings: List[Dict[str, Any]] = []
    ready = ready or {}
    status = status or {}

    ready_status = str(ready.get("status", "")).lower()
    if ready and ready_status and ready_status not in ("ready", "ok"):
        findings.append(
            {
                "code": "ready_not_ready",
                "severity": "high",
                "detail": f"health/ready status={ready.get('status')!r}",
            }
        )

    checks = ready.get("checks") if isinstance(ready.get("checks"), dict) else {}
    for key in (
        "state_consistent",
        "peers_alive",
        "sync_not_stalled",
        "accepting_requests",
    ):
        if key in checks and checks[key] is False:
            findings.append(
                {
                    "code": f"check_{key}_false",
                    "severity": "high" if key == "state_consistent" else "medium",
                    "detail": f"ready.checks.{key}=false",
                }
            )

    if status.get("sync_stalled") is True:
        findings.append(
            {
                "code": "sync_stalled",
                "severity": "high",
                "detail": "status.sync_stalled=true",
            }
        )

    peer_count = status.get("peer_count")
    mesh_min = status.get("mesh_min_peers")
    if peer_count is not None and mesh_min is not None:
        try:
            if int(peer_count) < int(mesh_min):
                findings.append(
                    {
                        "code": "under_mesh",
                        "severity": "medium",
                        "detail": f"peer_count={peer_count} < mesh_min_peers={mesh_min}",
                    }
                )
        except (TypeError, ValueError):
            pass

    height = status.get("height")
    if height is not None:
        try:
            if int(height) <= 0:
                findings.append(
                    {
                        "code": "height_zero",
                        "severity": "medium",
                        "detail": f"height={height}",
                    }
                )
        except (TypeError, ValueError):
            findings.append(
                {
                    "code": "height_unreadable",
                    "severity": "low",
                    "detail": f"height={height!r}",
                }
            )

    return findings
