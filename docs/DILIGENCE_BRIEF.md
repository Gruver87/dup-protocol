# Diligence brief — DUP Protocol / DUP Labs (industrial pin)

**Audience:** grant officers, investors, HTP / ПВТ reviewers, technical advisors.  
**Date:** 2026-10-09 · Language: English (canonical)  
**Front door:** [FUND_AUDIT_PREP.md](FUND_AUDIT_PREP.md)  
**Brand:** [BRAND.md](BRAND.md) — **DUP Labs** (org) · **DUP Protocol** (product) · Uladzimir Dabranski (D.U.P.)  
**This tree:** [`Gruver87/dup-protocol`](https://github.com/Gruver87/dup-protocol) (industrial pin)  
**R&D sibling:** [`Gruver87/dup-protocol-experimental`](https://github.com/Gruver87/dup-protocol-experimental)  
**Former name:** Absolute Blockchain (same trees / evidence).  
**Showcase:** [SHOWCASE.md](SHOWCASE.md) · FAQ: [FAQ.md](FAQ.md)

This page is the **15-minute path for the pin**. Claims map to **on-disk evidence** under [`docs/evidence/runs/`](evidence/runs/) and [`EVIDENCE_MATRIX.md`](EVIDENCE_MATRIX.md). Soft marketing language is refused.

---

## One sentence

**DUP Protocol** (by **DUP Labs**) is an **industrial hybrid L1** (Python orchestration + Rust/PyO3 hot path) with a **fail-closed** private prod-profile mesh. This pin is the audit-freeze / firm-engagement tree; Experimental is the R&D sandbox. Do **not** conflate the two.

---

## Two repositories (on purpose)

| Tree | Role | What you can claim today |
|------|------|--------------------------|
| **Industrial pin** (this repo) | Audit-freeze · tag [`v1.3.1339-tip-v2-industrial`](https://github.com/Gruver87/dup-protocol/releases/tag/v1.3.1339-tip-v2-industrial) | Historical tip-v2 **TCP+TLS** 48h soak PASS (`375d14f`); ADR 0020 libp2p cutover + Quick probe; 2026-10-08 **VOID**; 2026-10-11 short window not PASS; dirty STRICT 2026-10-15–17 archived; **primary** clean STRICT **2026-10-18–20 PASS** (`pin-libp2p-strict-48h`, `hard_fails=0`, `git_dirty=false`, tag [`v1.3.1340-libp2p-industrial-mesh`](https://github.com/Gruver87/dup-protocol/releases/tag/v1.3.1340-libp2p-industrial-mesh); not mainnet) |
| **experimental** | R&D · libp2p depth / Long-Range lab / EVM STRICT packs | Cite only packs under that repo; **never** as pin industrial evidence |

---

## Stage of development (honest)

| Stage | Status |
|-------|--------|
| Local **3-node prod-profile mesh** (chain `778888`) | **Proven** — probe packs on pin; see EVIDENCE_MATRIX |
| Fail-closed money path (satoshi integers) | **Proven** — units + industrial_gate |
| ADR 0020 rust-libp2p as working-tip mesh transport | **Code + Quick probe PASS**; 2026-10-08 **VOID**; 2026-10-18–20 clean STRICT **PASS** (`pin-libp2p-strict-48h`, tag `v1.3.1340-libp2p-industrial-mesh`, not mainnet) |
| Public audited mainnet / listed token / BLS prod | **Not claimed** |
| External firm security audit PDF | **Pending** — prep: [FIRM_KICKOFF_CHECKLIST.md](FIRM_KICKOFF_CHECKLIST.md) · [EXTERNAL_AUDIT_ENGAGEMENT.md](EXTERNAL_AUDIT_ENGAGEMENT.md) · [FIRM_OUTREACH_LETTER.md](FIRM_OUTREACH_LETTER.md) |

---

## What is ready for a firm

- Freeze tag + tip-v2 historical soak binder (TCP+TLS era)
- Fail-closed tip-safety / money / bridge-off defaults
- Engagement docs: [AUDIT_ENGAGEMENT_BRIEF.md](AUDIT_ENGAGEMENT_BRIEF.md), this brief, [MAINNET_GAP_ANALYSIS.md](MAINNET_GAP_ANALYSIS.md)
- Operator gates: `python scripts/industrial_gate.py`, `.\scripts\prepare_48h_soak.ps1`, `.\scripts\verify_audit_phase.ps1`
- Pin libp2p STRICT 48h **PASS** 2026-10-18–20 (`passed=true`, `hard_fails=0`, pack `pin-libp2p-strict-48h`, `git_dirty=false`, `c5ac635c`). Not public mainnet. Tagged `v1.3.1340-libp2p-industrial-mesh`. Dirty 15–17 Oct archived separately.
- ПВТ / HTP show pack (RU): [PVT_HTP_SHOW_PACK_RU.md](PVT_HTP_SHOW_PACK_RU.md)

## What is not ready

- Public mainnet / token listing
- Firm pen-test + L1/EVM audit PDF on disk
- Long-Range in production (`feature_long_range` stays **off**)
- HTP residency / filled legal entity fields in-repo

---

## Operator next step

**Now:** [FUND_AUDIT_PREP.md](FUND_AUDIT_PREP.md) · `verify_project -Mode Industrial` · firm engagement docs · ПВТ pack [PVT_HTP_SHOW_PACK_RU.md](PVT_HTP_SHOW_PACK_RU.md). Primary soak cite: clean `pin-libp2p-strict-48h` (2026-10-18–20). Do not cite 2026-10-08 VOID or 2026-10-11 short window as PASS. Not public mainnet.

**Later:** another STRICT only if HEAD or mesh image changes materially. Do not resume a finished log.
