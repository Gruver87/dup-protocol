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
| ADR 0020 libp2p mesh JSON + Quick probe | **Packaged** — 2026-10-08 soak **VOID** (not PASS); STRICT 2026-10-15–17 **PASS** (`pin-libp2p-strict-48h`, tag not cut) |
| External firm audit PDF / pen-test | **Org Phase 6** — [FIRM_KICKOFF_CHECKLIST](FIRM_KICKOFF_CHECKLIST.md) |
| Fresh pin libp2p 48h soak | **PASS** 2026-10-15–17 (`pin-libp2p-strict-48h`). Another run only for a clean-commit image bind |

Detailed A–H remediation history for Experimental mid-2026 lives on the Exp tree; this pin tracks **industrial engagement**, not Exp R&D phase letters.

---

## Layer bring-up (after the Exp port, 2026-10-17)

Code for libp2p, EVM, mempool validation, Long-Range, and the council NFT gate is on this pin. Bring-up does not flip prod JSON and does not start a soak.

1. **Lock** — prod `778888` keeps `feature_long_range=false`, `feature_nft=false`, bridge OFF. Long-Range lab profile stays `deployment_mode=dev`, chain `77779`. Gate refuses a lab file that uses `778888`.
2. **Long-Range lab only** — `python scripts/verify_long_range_host.py` runs the three offline labs and checks prod JSON. Committee keys, when needed later, come from `gen_long_range_lab_committee.py` into gitignored `data/`. No soak until the operator orders a pin lab window. BLS is not in this step.
3. **Council** — `features/council_nft.py` serves the existing NFT transfer refuse. `python scripts/nft_lab.py` is the offline check (`feature_nft` stays false; staging `:19080` is skipped when closed). No staging mint.
4. **Prod mesh unchanged** — libp2p STRICT pack `pin-libp2p-strict-48h` stays the mesh proof. Another 48h only for a clean-commit image bind.
5. **Org** — pen-test and firm PDF. Not a code flag.

## Next 90 days (org / operator)

1. Keep CI + `industrial_gate` green on `master`  
2. Pin libp2p STRICT 48h is PASS (`pin-libp2p-strict-48h`). A new window, only if ordered, is `prepare_48h_soak.ps1` then `start_soak_prod_mesh_48h_strict.ps1`. The non-strict starter stays on disk and is not that bar.  
3. Firm outreach + NDA / scope — [EXTERNAL_AUDIT_ENGAGEMENT.md](EXTERNAL_AUDIT_ENGAGEMENT.md)  
4. Do **not** arm Long-Range or bridge on prod 778888 mesh JSON  

**Related:** [FUND_READINESS.md](FUND_READINESS.md) · [DILIGENCE_BRIEF.md](DILIGENCE_BRIEF.md) · [MAINNET_GAP_ANALYSIS.md](MAINNET_GAP_ANALYSIS.md)
