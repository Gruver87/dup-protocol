# Verify suite — industrial pin (operator)

**Brand:** DUP Labs · DUP Protocol  
**Repo:** [`Gruver87/dup-protocol`](https://github.com/Gruver87/dup-protocol)  
**Goal:** one place for pin working-surface checks.  
**Not:** 48h soak start · public mainnet claim · Experimental Long-Range / Exp soak packs as pin evidence.

Dual-repo Exp+pin verify (`verify_dup_suite`) lives only on [`dup-protocol-experimental`](https://github.com/Gruver87/dup-protocol-experimental).

---

## Daily / after a disk wave

```powershell
cd C:\Users\vovun\Desktop\Absolute_Blockchain_Ultimate_Hybrid

.\scripts\verify_project.ps1 -Mode Quick
# or:
.\scripts\verify_project.ps1 -Mode Standard
.\scripts\verify_project.ps1 -Mode Industrial
```

## Sprout / aux labs (Phase 5 — offline)

```powershell
.\scripts\verify_sprout_labs.ps1
# pieces:
.\scripts\verify_bridge_off_lab.ps1
.\scripts\verify_oracle_lab.ps1
.\scripts\verify_cross_shard_lab.ps1
.\scripts\verify_nft_marketplace.ps1 -SkipStaging
python scripts/ai_lab.py
python scripts/ai_ops_anomaly.py --offline-only
```

## Deep / live mesh (no soak start)

```powershell
python scripts/industrial_gate.py
.\scripts\verify_full_blockchain.ps1 -Hard          # needs live :18180–18182
.\scripts\verify_hard_all.ps1
.\scripts\probe_prod_mesh.ps1 -Quick                # only if mesh already up
```

## Fund / demo prep

```powershell
# see FUND_DEMO_OPERATOR_PACK.md
python scripts/industrial_gate.py
.\scripts\prepare_48h_soak.ps1   # does NOT start soak
```

---

## Honesty

| PASS means | Does **not** mean |
|------------|-------------------|
| Units / gate / lab offline green | Public mainnet |
| Quick mesh probe OK | 48h soak PASS |
| Sprout labs PASS | Prod `feature_nft` / oracles / sharding ON |
| Bridge OFF verify PASS | Bridge L1 cutover ready |

Reports: `logs/verify_*.json`, `data/industrial_gate.json`.
