# Audit → 90-day fix plan — industrial pin (honest)

**Repo:** [`Gruver87/dup-protocol`](https://github.com/Gruver87/dup-protocol)  
**Rule:** nothing that breaks tip-v2 evidence packs, money satoshi, tip-safety, or prod mesh JSON.  
**Soak:** new 48h soaks stay on the shelf unless a hot-path money/P2P/consensus change requires re-proof.  
**R&D sequence (Experimental):** see [EXECUTION_ORDER on Exp](https://github.com/Gruver87/dup-protocol-experimental/blob/main/docs/EXECUTION_ORDER.md) — **not** pin evidence.

---

## Safety ladder (always)

```text
1. Honesty / docs / labels          ← no consensus break
2. Quarantine / UI / refuse APIs    ← fail-closed, tests update
3. Additive satoshi ports           ← float display only at REST
4. Behavior harden under flags      ← require_native refuse, etc.
5. Breaking remap / revm            ← ONLY with migration ADR + lab
```

**Forbidden in this window:** Great Merge · bridge ON on live mesh · prod Long-Range · silent opcode remap without ADR.

---

## Pin status (2026-10-07)

| Track | Status |
|-------|--------|
| Honesty / satoshi / RPC / health | **CLOSED** via Exp→pin merge waves — [EVIDENCE_MATRIX](EVIDENCE_MATRIX.md) |
| Bridge OFF audit | **CLOSED** — `verify_bridge_off_lab.ps1` |
| Phase-5 sprout labs (offline) | **CLOSED** — `verify_sprout_labs.ps1` |
| ADR 0020 libp2p mesh JSON + Quick probe | **Packaged** — soak **deferred** |
| External firm audit PDF / pen-test | **Org Phase 6** — [FIRM_KICKOFF_CHECKLIST](FIRM_KICKOFF_CHECKLIST.md) |
| Fresh pin libp2p 48h soak | **Operator** — prepare then start (do not invent PASS) |

Detailed A–H remediation history for Experimental mid-2026 lives on the Exp tree; this pin tracks **industrial engagement**, not Exp R&D phase letters.

---

## Next 90 days (org / operator)

1. Keep CI + `industrial_gate` green on `master`  
2. When merge declared complete: `prepare_48h_soak.ps1` → `start_soak_prod_mesh_48h.ps1` → pack only if `hard_fails=0`  
3. Firm outreach + NDA / scope — [EXTERNAL_AUDIT_ENGAGEMENT.md](EXTERNAL_AUDIT_ENGAGEMENT.md)  
4. Do **not** arm Long-Range or bridge on prod 778888 mesh JSON  

**Related:** [FUND_READINESS.md](FUND_READINESS.md) · [DILIGENCE_BRIEF.md](DILIGENCE_BRIEF.md) · [MAINNET_GAP_ANALYSIS.md](MAINNET_GAP_ANALYSIS.md)
