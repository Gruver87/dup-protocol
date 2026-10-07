# Pin libp2p 48h soak PREP READY — tip 61114f36434ee413267eea3e06a57cee44f79102

**Status:** PREFLIGHT **READY** · soak **NOT started** · **NOT PASS**
**Date:** 2026-10-07
**Chain:** 778888 · rust-libp2p (eature_libp2p=true, p2p_tls_enabled=false, eature_long_range=false)
**Image:** `sha256:be576392c01f2ba22bebebef1e4e486b7106ae373ebbbd3dedf1be5265bfa908`
**Git:** `61114f36434ee413267eea3e06a57cee44f79102` (commit prep stamp after this file lands)

## Bar for PASS (after 48h)

- report `passed=true` and `hard_fails=0`
- STRICT pack: also `mesh_warn=0` (soft peer_probe/harness_timeout WARN OK)
- Do **not** claim PASS from Quick / preflight / this stamp

## Preflight evidence (this wave)

| Check | Result |
|-------|--------|
| Disk free | >=15 GB (cleaned to ~32 GB) |
| Mesh healthy ×3 + redis | OK |
| Image pin == container | OK + COMMITTED_STATE_ROOT_OK |
| soak_preflight --require-libp2p --require-wire-probe | READY |
| probe_prod_mesh -Quick | RESULT: OK |
| check_mesh_catchup live | PASS (gap=0, consist/topo/wire) |
| miner harness ×5 | 5/5 healthy |
| industrial_gate | OK (3 external-audit warnings expected) |
| verify_midsoak_honesty -Quick | PASS |
| verify_sprout_labs | PASS |
| health_watch -Strict -DurationMin 1 | hard_fails=0 |
| start_soak_prod_mesh_48h_strict -PreflightOnly | PASS preflight-only |

## Operator start (when you say go)

**Recommended (STRICT / industrial claim path):**
```powershell
cd C:\Users\vovun\Desktop\Absolute_Blockchain_Ultimate_Hybrid
# Sleep=Never on AC. Do NOT rebuild Docker until 48h ends.
.\scripts\start_soak_prod_mesh_48h_strict.ps1 -SkipRebuild
```

**Alternate (default 48h scoring, IntervalSec=300):**
```powershell
.\scripts\start_soak_prod_mesh_48h.ps1 -Hours 48 -IntervalSec 300 -SkipRebuild
```

Check: `.\scripts\check_soak.ps1` · Stop: `.\scripts\stop_soak_monitors.ps1 -Force`

## Honesty

- Historical tip-v2 TCP+TLS pack `375d14f` unchanged
- Exp libp2p packs are **not** pin evidence
- Premature soak 2026-10-05 remains STOPPED (not PASS)
