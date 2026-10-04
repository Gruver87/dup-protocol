# Fund / demo operator pack — industrial pin (honest)

**Date:** 2026-10-04 · **Repo tip:** run `git rev-parse --short HEAD`  
**Brand:** DUP Labs · DUP Protocol  
**Repo:** [`Gruver87/dup-protocol`](https://github.com/Gruver87/dup-protocol)  
**Not:** public audited mainnet · not firm pen-test PASS · not a new 48h soak claim.

Operator checklist after Exp→pin honesty merge layers. Pin transport remains **TCP+TLS** (libp2p stays Experimental / opt-in only).

---

## What is ready to show

| Layer | Status | Proof |
|-------|--------|-------|
| Industrial pin (TCP+TLS freeze) | Show for firm scope | tag `v1.3.1339-tip-v2-industrial` + current `master` honesty merges |
| Fail-closed satoshi / RPC honesty | Code + units + industrial_gate | `api/eth_format.py` observed_* · fund-prep needles |
| STRICT 48h scoreboard | Historical packs only | Do not claim soak on current HEAD unless a new pack exists |
| Showcase / diligence docs | On disk | [SHOWCASE](SHOWCASE.md) · [DILIGENCE_BRIEF](DILIGENCE_BRIEF.md) · [FUND_READINESS](FUND_READINESS.md) |

---

## Pre-meeting verify (operator)

```powershell
cd C:\Users\vovun\Desktop\Absolute_Blockchain_Ultimate_Hybrid

python -m pytest tests/unit/test_wave_n_rpc_honesty.py tests/unit/test_fund_prep_honesty_wave.py -q --tb=short
python scripts/industrial_gate.py

# Optional live mesh (only if Docker mesh already up)
.\scripts\probe_prod_mesh.ps1 -Quick
```

**Pass bar for deck:** industrial_gate OK · fund-prep units green · CI green on `master`.  
**Do not say:** “48h soak on this tip” unless a new pack exists for current HEAD.

---

## Demo path (15–60 min)

1. Open [SHOWCASE.md](SHOWCASE.md)  
2. Honesty: `/status` shows `mev_simulation_only`, L2 `*_execution_bound`, bridge OFF  
3. Gaps: [MAINNET_GAP_ANALYSIS.md](MAINNET_GAP_ANALYSIS.md) — say them first  
4. Narrative: **TCP+TLS** industrial pin — not Experimental libp2p as “audited”

---

## Closed in code (honesty merge)

- Observed RPC fields: hashes / miner / size / timestamp / receipt status / logs  
- Receipt cumulativeGasUsed · sha3Uncles = keccak(RLP []) · uncle-count null if missing  
- Block gasUsed / logsBloom from observed data · tx-count null if block missing  
- Pool-spend sat admit · no invent gas=21000 · bridge2/fee no invent amount=100  
- WASM nonzero value refused (pseudo host) · auto_sign `amount_satoshi`

---

## Still open (do not green-paint)

| Item | Notes |
|------|-------|
| External pen-test + L1 audit PDF | Org / Phase 6 |
| Bridge L1 contracts live | Keep bridge OFF on live mesh |
| Fresh 48h soak on current HEAD | Operator — after merge complete |
| ADR 0020 Exp libp2p vs pin TCP+TLS | Intentional — do not sell as pin parity |
| Long-Range / BLS | Lab-only / off in prod JSON |

---

## Fund one-liner (approved honesty)

> Ready for **technical diligence on an industrial private mesh / R&D L1**.  
> **Not** ready to claim **public audited mainnet**.
