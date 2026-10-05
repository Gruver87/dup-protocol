# Pin libp2p industrial mesh — cutover evidence (`pin-libp2p-cutover-pending`)

**Kind:** ADR 0020 cutover  
**Status:** **Quick probe PASS packaged** · **48h soak DEFERRED** (operator: after full merge; premature 21:11 restart **stopped** — not PASS)  
**Chain:** prod-profile `778888` · rust-libp2p (`feature_libp2p=true`, `p2p_tls_enabled=false`)

## Honesty

- Quick mesh probe (`probe_prod_mesh.ps1 -Quick`) → **RESULT: OK** — see `probe_prod_mesh_quick.json` + `status_snapshot.jsonl` (peers=2, aligned tip, `libp2p.active` + `rust_backend`, honesty `ADR0020_experimental_libp2p_industrial_mesh`)
- `industrial_gate.py` → **OK** (see `industrial_gate.json`; external-audit warnings expected)
- Negative refuse notes: `NEGATIVE_REFUSE.txt`
- **48h soak deferred** until operator declares full Exp→pin merge complete. Premature restart 2026-10-05 21:11 tip `bd500c1` was **stopped** (see `SOAK_STOPPED_PREMATURE.txt` / `SOAK_IN_PROGRESS.txt`). **Do not claim PASS.**
- **NOT** public mainnet · **NOT** external audit
- Do **not** cite Experimental libp2p soaks (`3c801b87`, `lp2pstrict1`) as pin evidence
- Freeze tag `v1.3.1339-tip-v2-industrial` and sealed TCP+TLS packs remain **historical** — unchanged

## Operator: 48h soak still required

```powershell
cd C:\Users\vovun\Desktop\Absolute_Blockchain_Ultimate_Hybrid
.\scripts\soak_monitor.ps1 -ProdMesh -Hours 48
# only claim PASS when report has passed=true and hard_fails=0
```

**Suggested release tag (after soak PASS + commit):** `v1.3.1340-libp2p-industrial-mesh`  
(Not created on this cutover — working tree dirty; freeze tag untouched.)

## Packaged now

| File | Purpose |
|------|---------|
| `probe_prod_mesh_quick.json` | Quick probe PASS |
| `status_snapshot.jsonl` | Live `/status` from 18180–18182 |
| `industrial_gate.json` | Gate snapshot |
| `NEGATIVE_REFUSE.txt` | TLS+libp2p / `-P2pTls` / missing-swarm refuse |
| `MESH_PROBE_POST_STRICT.txt` | Outbound/class-rate Quick probe stamp |
| `MESH_PROBE_POST_FORGE_SOLICIT_PATHA.txt` | Own-forge + solicit + PathA Quick probe (h908) |
| `probe_prod_mesh_quick_forge_solicit_patha.json` | Probe JSON for forge/solicit/PathA wave |
| `industrial_gate_forge_solicit_patha.json` | Gate snapshot for that wave |
| `MESH_PROBE_POST_ATTEST_SYNC_PARENT.txt` | Attest-echo + SyncEngine probes + parent FC (h989) |
| `probe_prod_mesh_quick_attest_sync_parent.json` | Probe JSON for attest/sync/parent wave |
| `industrial_gate_attest_sync_parent.json` | Gate snapshot for that wave |
| `MESH_PROBE_POST_ROCKS_O1.txt` | Rocks O(1) + topology_deferred Quick probe (h1051) |
| `probe_prod_mesh_quick_rocks_o1.json` | Probe JSON for Rocks O(1) wave |
| `industrial_gate_rocks_o1.json` | Gate snapshot for that wave |
| `MESH_PROBE_POST_ROCKS_PAGES.txt` | Rocks page-scan leftovers Quick probe (h1101) |
| `probe_prod_mesh_quick_rocks_pages.json` | Probe JSON for Rocks pages wave |
| `industrial_gate_rocks_pages.json` | Gate snapshot for that wave |
| `MESH_PROBE_POST_APPLY_QUEUE.txt` | ChainApplyQueue wrap_future Quick probe (h1141) |
| `probe_prod_mesh_quick_apply_queue.json` | Probe JSON for apply-queue wave |
| `industrial_gate_apply_queue.json` | Gate snapshot for that wave |
| `MESH_PROBE_POST_MERGE_TIP_SOLICIT_BLOCKS.txt` | Tip-rebind + solicit lag + get_blocks + redial Quick probe (h1244) |
| `probe_prod_mesh_quick_merge_tip_solicit_blocks.json` | Probe JSON for tip/solicit/blocks/redial wave |
| `industrial_gate_merge_tip_solicit_blocks.json` | Gate snapshot for that wave |
| `README.md` | This honesty stamp |

## Still missing for industrial soak claim

| File | Purpose |
|------|---------|
| `soak_report*.json` | `passed=true`, `hard_fails=0` |
| `soak_monitor.log` | 48h run log |
| `manifest.json` | commit + sha256 bindings after soak |
