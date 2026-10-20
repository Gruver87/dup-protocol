# v1.3.1340 — libp2p industrial mesh (working tip)

**Tag:** `v1.3.1340-libp2p-industrial-mesh`  
**Purpose:** mark the clean-commit ADR 0020 rust-libp2p STRICT 48h PASS on the industrial pin.

## What this tag proves

| Claim | Evidence |
|-------|----------|
| rust-libp2p STRICT **48h soak PASS** (clean git) | [`docs/evidence/runs/pin-libp2p-strict-48h/`](docs/evidence/runs/pin-libp2p-strict-48h/) · `passed=true` · `hours_elapsed=48.0004` · `hard_fails=0` · `mesh_warn=0` · `warn_lines=0` |
| Soak start git | `c5ac635c` · `git_dirty=false` |
| Soak image | `sha256:83d7e19ef3e9632e79ac04f27bd8651f550f0d4607306f69c82a2b034f1f922e` |
| Window | 2026-10-18 09:59+03 → 2026-10-20 09:59+03 |
| Working-tip mesh transport | ADR 0020 · `feature_libp2p=true` · Noise/Yamux |

## What this tag does **not** claim

- Public mainnet / listed ABS  
- External firm audit complete  
- Bridge ON on live mesh  
- Prod Long-Range armed (`feature_long_range` stays false)  
- That freeze tag `v1.3.1339-tip-v2-industrial` is libp2p (it stays **TCP+TLS** historical)

## Prior windows (honesty)

- 2026-10-08 power-off — **VOID** (not PASS)  
- 2026-10-11 short window — not PASS (44.2h)  
- 2026-10-15–17 STRICT PASS on dirty git — archived [`pin-libp2p-strict-48h-dirty-c1c281f`](docs/evidence/runs/pin-libp2p-strict-48h-dirty-c1c281f/)

## Verify

```powershell
python scripts/industrial_gate.py --min-soak-hours 48
python scripts/bridge_off_audit_gate.py
.\scripts\check_soak.ps1
```

`industrial_gate` may exit 0 with warnings for the two firm-owned audit tracker items and the bridge cutover **example** JSON — expected.
