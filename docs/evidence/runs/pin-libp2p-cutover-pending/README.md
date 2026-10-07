# Pin libp2p industrial mesh — cutover evidence (`pin-libp2p-cutover-pending`)

**Kind:** ADR 0020 cutover  
**Status:** **Quick probe PASS packaged** · **48h soak PREP READY on HEAD** (see [`SOAK_PREP_READY_HEAD.md`](SOAK_PREP_READY_HEAD.md)) · soak **NOT started** · **NOT PASS**  
**Chain:** prod-profile `778888` · rust-libp2p (`feature_libp2p=true`, `p2p_tls_enabled=false`)

## Honesty

- Quick mesh probe (`probe_prod_mesh.ps1 -Quick`) → **RESULT: OK**
- `industrial_gate.py` → **OK** (external-audit warnings expected)
- **48h prep READY** on working tip (disk, image pin, libp2p preflight, catchup, miner harness ×5, midsoak honesty, sprout labs, Strict 1m `hard_fails=0`, STRICT preflight-only)
- Premature restart 2026-10-05 21:11 was **stopped** (`SOAK_STOPPED_PREMATURE.txt`) — not PASS
- **NOT** public mainnet · **NOT** external audit
- Do **not** cite Experimental libp2p soaks as pin evidence
- Freeze tag `v1.3.1339-tip-v2-industrial` / TCP+TLS tip-v2 packs remain **historical**

## Operator: start when ready

```powershell
cd C:\Users\vovun\Desktop\Absolute_Blockchain_Ultimate_Hybrid
# Sleep=Never on AC. Do NOT rebuild Docker until 48h ends.
.\scripts\start_soak_prod_mesh_48h_strict.ps1 -SkipRebuild
```

Only claim PASS when report has `passed=true` and `hard_fails=0` (STRICT: `mesh_warn=0`).

**Suggested release tag (after soak PASS + commit):** `v1.3.1340-libp2p-industrial-mesh`

## Prep stamp (this wave)

| File | Purpose |
|------|---------|
| [`SOAK_PREP_READY_HEAD.md`](SOAK_PREP_READY_HEAD.md) | Operator READY checklist |
| `soak_48h_prep.json` / `soak_preflight.json` | prepare_48h_soak + soak_preflight |
| `probe_prod_mesh_quick_prep_head.json` | Quick probe |
| `industrial_gate_prep_head.json` | Gate snapshot |
| `status_snapshot_prep_head.json` | Live tip/peers/libp2p |
| `hw_strict_smoke_1m_prep_head.log` | Strict 1m (`hard_fails=0`) |
| `strict_preflight_only_prep_head.log` | STRICT starter `-PreflightOnly` |
| `verify_sprout_labs_prep_head.json` | Sprout labs PASS |

## Still missing for industrial soak claim

| File | Purpose |
|------|---------|
| `soak_report*.json` | `passed=true`, `hard_fails=0` |
| `soak_monitor.log` / STRICT log | 48h run log |
| `manifest.json` | commit + sha256 bindings after soak |
