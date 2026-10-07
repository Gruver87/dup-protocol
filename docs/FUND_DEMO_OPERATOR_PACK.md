# Fund / demo operator pack — industrial pin (honest)

**Date:** 2026-10-05 (transport note refreshed for ADR 0020) · **Repo tip:** run `git rev-parse --short HEAD`  
**Brand:** DUP Labs · DUP Protocol  
**Repo:** [`Gruver87/dup-protocol`](https://github.com/Gruver87/dup-protocol)  
**Not:** public audited mainnet · not firm pen-test PASS · not a new 48h soak claim.

Operator checklist after Exp→pin honesty merge close. **Working-tip prod 3-node mesh** uses **rust-libp2p** (ADR 0020: `feature_libp2p=true`, `p2p_tls_enabled=false`). **TCP+TLS** remains the alternate profile (`node.prod.json` / ceremony). Freeze tag `v1.3.1339-tip-v2-industrial` is **historical TCP+TLS** evidence only. Pin libp2p soak/probe **not completed** — do not claim PASS.

---

## What is ready to show

| Layer | Status | Proof |
|-------|--------|-------|
| Industrial pin (freeze + working tip) | Show for firm scope | tag `v1.3.1339-tip-v2-industrial` (`0531995`) = **TCP+TLS** sealed evidence; working tip = ADR 0020 libp2p mesh JSON (soak pending) |
| Fail-closed satoshi / RPC / health honesty | Code + units + industrial_gate | Exp→pin merge CLOSED — see [EVIDENCE_MATRIX](EVIDENCE_MATRIX.md) CI row |
| STRICT 48h scoreboard | Historical packs only | Do not claim soak on current HEAD unless a new pack exists |
| Showcase / diligence docs | Pin local | [SHOWCASE](SHOWCASE.md) · [DILIGENCE_BRIEF](DILIGENCE_BRIEF.md) · [FUND_READINESS](FUND_READINESS.md) · [VERIFY_SUITE](VERIFY_SUITE.md) |
| Phase 6 firm prep | Prep only | [FIRM_KICKOFF_CHECKLIST](FIRM_KICKOFF_CHECKLIST.md) · [AUDITS.md](AUDITS.md) · [AUDIT_ENGAGEMENT_BRIEF](AUDIT_ENGAGEMENT_BRIEF.md) · `logs/audit_pack_20261004.zip` |

---

## Pre-meeting verify (operator)

```powershell
cd C:\Users\vovun\Desktop\Absolute_Blockchain_Ultimate_Hybrid

python -m pytest `
  tests/unit/test_committed_state_root.py `
  tests/unit/test_zk_proofs.py `
  tests/unit/test_bridge_lock_burn_fail_closed.py `
  tests/unit/test_lightning_fee_rate_finite.py `
  tests/unit/test_rocks_account_count_meta.py `
  -q --tb=short
python scripts/industrial_gate.py

# Optional live mesh (only if Docker mesh already up)
.\scripts\probe_prod_mesh.ps1 -Quick
```

**Pass bar for deck:** industrial_gate OK · honesty units green · CI green on `master`.  
**Do not say:** “48h soak on this tip” unless a new pack exists for current HEAD.

---

## Demo path (15–60 min)

1. Open [SHOWCASE.md](SHOWCASE.md)  
2. Honesty: `/status` tip_skew (not false inconsistent) · MEV `simulation_only` · bridge OFF  
3. Gaps: [MAINNET_GAP_ANALYSIS.md](MAINNET_GAP_ANALYSIS.md) — say them first  
4. Narrative: **pin prod mesh is libp2p (ADR 0020)** on working tip — freeze tag stays **TCP+TLS**; Experimental libp2p soaks are **not** pin evidence; external audit still **pending**

---

## Closed in code (honesty merge through `adc8547`)

- Observed RPC fields · satoshi money paths · ATXV/ATXR · EIP-214 STATICCALL  
- ZK range refuse · SPHINCS+ refuse · committed `get_state_root` · height-bounded eth_getLogs  
- `tip_skew` / prod P2P-null ready · harness cached counts · tip-head/tip-root refuse  
- Oracle/Lightning/AI `parse_finite_number` · Rocks obs count meta · bridge debit+burn  
- WASM nonzero value refused · auto_sign `amount_satoshi` · MEV simulation stamps

---

## Still open (do not green-paint)

| Item | Notes |
|------|-------|
| External pen-test + L1 audit PDF | Org / Phase 6 |
| Bridge L1 contracts live | Keep bridge OFF on live mesh |
| Fresh 48h soak on current HEAD | Operator — ADR 0020 libp2p cutover **not** soak-proven (`pin-libp2p-cutover-pending`) |
| Post-cutover mesh probe | Operator — `probe_prod_mesh.ps1 -Quick` not re-run as pin evidence pack |
| Experimental libp2p soaks (`3c801b87`, `lp2pstrict1`) | **Not** pin evidence — R&D on [`dup-protocol-experimental`](https://github.com/Gruver87/dup-protocol-experimental) only |
| Long-Range / BLS | Lab-only / off in prod JSON |

---

## Fund one-liner (approved honesty)

> Ready for **technical diligence on an industrial private mesh / R&D L1**.  
> **Not** ready to claim **public audited mainnet**.
