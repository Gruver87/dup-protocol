# External audit engagement — Phase F3 / org Phase 6

**Org:** DUP Labs · **Product:** DUP Protocol  
**Repos:** industrial pin [`dup-protocol`](https://github.com/Gruver87/dup-protocol) · R&D [`dup-protocol-experimental`](https://github.com/Gruver87/dup-protocol-experimental)  
**Purpose:** Prep pack for a **firm** security review. This file is **not** an audit report and **not** a soak claim.

---

## What to hand the firm

| Artifact | Location / note |
|----------|-----------------|
| Industrial freeze tag | `v1.3.1339-tip-v2-industrial` on `dup-protocol` |
| Diligence brief | [`DILIGENCE_BRIEF.md`](DILIGENCE_BRIEF.md) |
| Evidence matrix | [`EVIDENCE_MATRIX.md`](EVIDENCE_MATRIX.md) |
| Mainnet gaps (honest) | [`MAINNET_GAP_ANALYSIS.md`](MAINNET_GAP_ANALYSIS.md) |
| Tip safety ADR | [`adr/0001-tip-safety.md`](adr/0001-tip-safety.md) |
| Absolute-VM honesty | [`adr/0023-absolute-vm-opcode-map.md`](adr/0023-absolute-vm-opcode-map.md) — **not** Yellow Paper drop-in |
| Demo runbook | [`DEMO_RUNBOOK.md`](DEMO_RUNBOOK.md) |
| Ceremony dry-run | [`CEREMONY_DRY_RUN.md`](CEREMONY_DRY_RUN.md) |

Prefer the **pin** for firm scope. Experimental packs (libp2p / LR lab / EVM STRICT) are R&D evidence — label them as such.

### Recorded pins (prep — not an audit report)

| Tree | Ref | SHA (object) |
|------|-----|----------------|
| Industrial pin | tag `v1.3.1339-tip-v2-industrial` | `0531995d41673a807b5c21ddf1beb7b5034eab07` |
| Experimental (this repo) | `main` at kickoff | **re-record:** `git rev-parse HEAD` (prep pack `phase6prep1` recorded `a978328` historically) |

Pin SHA verified locally 2026-10-03 via `git rev-list -n 1 v1.3.1339-tip-v2-industrial` on [`dup-protocol`](https://github.com/Gruver87/dup-protocol). Prep pack: [`evidence/runs/phase6prep1/`](evidence/runs/phase6prep1/). Human checklist: [`FIRM_KICKOFF_CHECKLIST.md`](FIRM_KICKOFF_CHECKLIST.md). Firm one-pager: [`AUDIT_ENGAGEMENT_BRIEF.md`](AUDIT_ENGAGEMENT_BRIEF.md).

### Evidence pack IDs to list in the engagement letter

- Tip / industrial mesh: pin soak + Hybrid tip-v2 pack as labeled in [`EVIDENCE_MATRIX.md`](EVIDENCE_MATRIX.md)
- Experimental (optional, label R&D): `ind48pass1`, `lp2pstrict1`, `evmstrict1`, `mempool48pass1`, `lrstrict1` (lab only)
- Host lab re-verify (optional): `phase5reverify2` (oracle/shard/bridge OFF — **not** soak)
- Phase 6 prep refresh: `phase6prep1` (**not** firm PASS)

Operator self-check:

```powershell
.\scripts\verify_audit_engagement_prep.ps1
.\scripts\verify_audit_phase.ps1 -Phase H
.\scripts\verify_audit_90d_all.ps1 -SkipGate   # full A–H without industrial_gate
```

---

## In-scope (suggested)

1. Tip-safety / import refuse (ADR 0001)  
2. Money path: satoshi integers on wire **and** ABS ledger persist dual-write (AUDIT Phase G — validators/bridge/sprouts/NFT/burn/tx+receipts); refuse float mismatch / float fallback on critical paths  
3. Prod mesh config fail-closed (`tip_safety_enforce`, `require_native_crypto`, bridge OFF)  
4. P2P soft-refuse / rate limits (not ban theater)  
5. Secrets: no file-based secrets in prod; JWT / API keys  
6. EVM honesty: Absolute opcode map + CREATE2 host-salt Absolute hashing  

**Not ABS ledger (keep out of money satoshi claims):** oracle feed/report market `value`; lightning `fee_rate`.

## Out-of-scope (explicit)

- Public audited mainnet claim  
- Bridge ON / L1 contracts (until cutover ADR + pack)  
- Prod Long-Range (`feature_long_range` stays false)  
- Yellow Paper / solc drop-in compatibility  
- “Real ZK” circuits (explorer UI stripped; range = NotImplemented)  
- New 48h soak unless operator orders a fresh pack  

---

## Operator checklist (before kickoff)

- [ ] Pin tag + commit SHA recorded in engagement letter  
- [ ] Evidence pack IDs listed (tip / industrial mesh / optional experimental)  
- [ ] Secrets rotation plan (Vault/K8s — no `.env` in prod)  
- [ ] Ceremony dry-run completed; live ceremony still gated  
- [ ] Contact: security@ / founder channel for findings  
- [ ] NDA + scope signed; remote mesh access or sealed docker compose  

Step-by-step human box: [`FIRM_KICKOFF_CHECKLIST.md`](FIRM_KICKOFF_CHECKLIST.md).  
Copy-paste outreach draft: [`FIRM_OUTREACH_LETTER.md`](FIRM_OUTREACH_LETTER.md).  
Print handoff: `.\scripts\print_firm_handoff.ps1`.  

---

## After findings

1. Triage by severity (money / tip / P2P / honesty / DX)  
2. Fix on **experimental** or pin branch per firm agreement — no silent green  
3. Re-run unit + `industrial_gate` + mesh probe; soak only if firm requires re-proof  
4. Update `EVIDENCE_MATRIX` / `MAINNET_GAP_ANALYSIS` — never hide residual gaps  

---

**Related:** [`INVESTOR_DECK_SKELETON.md`](INVESTOR_DECK_SKELETON.md) · [`AUDIT_90D_FIX_PLAN.md`](AUDIT_90D_FIX_PLAN.md) · [`FUND_READINESS.md`](FUND_READINESS.md)
