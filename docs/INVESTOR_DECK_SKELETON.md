# Investor / ПВТ deck skeleton — DUP Protocol

**Org:** DUP Labs · **Product:** DUP Protocol · **Author:** Uladzimir Dabranski (D.U.P.)  
**Repos:** industrial pin [`dup-protocol`](https://github.com/Gruver87/dup-protocol) · R&D [`dup-protocol-experimental`](https://github.com/Gruver87/dup-protocol-experimental)  
**Source of truth for claims:** [DILIGENCE_BRIEF.md](DILIGENCE_BRIEF.md) · [FUND_READINESS.md](FUND_READINESS.md) · [EVIDENCE_MATRIX.md](EVIDENCE_MATRIX.md)

This is a **slide outline**, not a finished pitch deck. Copy into your presentation tool; every numerical / soak claim must cite an on-disk pack.

---

## Slide map (≤12)

| # | Title | Content rule |
|---|--------|--------------|
| 1 | **DUP Protocol** | Brand hero: DUP Labs · hybrid L1 · fail-closed private mesh. One sentence from Diligence Brief. |
| 2 | Problem | Why industrial L1 R&D needs evidence packs, not demo theater. |
| 3 | Architecture | Python orchestration + Rust hot path (ADR 0009). One diagram. |
| 4 | Two repos | Pin = audit freeze (`v1.3.1339-tip-v2-industrial`). Experimental = libp2p / LR lab / EVM depth. |
| 5 | Tip safety | ADR 0001 / tip-v2 — cite tip soak pack if shown. |
| 6 | Money path | Satoshi integers; float refuse on wire. Units + mesh evidence. |
| 7 | Mesh proof | 3-node prod-profile · probe · pick **one** 48h pack (`hard_fails=0`) with path. |
| 8 | EVM honesty | Absolute opcode map ≠ Yellow Paper. Matrix + `/evm/status`. No silent remap (ADR 0023). |
| 9 | What is **not** claimed | Public audited mainnet · bridge ON · prod Long-Range · listed token. |
| 10 | 90-day plan | Org / show / harden order from [AUDIT_90D_FIX_PLAN.md](AUDIT_90D_FIX_PLAN.md). Soaks on shelf unless re-proof ordered. |
| 11 | Ask | Grant / ПВТ / diligence engagement — technical review of private mesh + evidence. |
| 12 | Appendix | Links: brief, matrix, gaps, demo runbook, ceremony dry-run. |

---

## Forbidden phrases

- “Mainnet ready” / “Ethereum-compatible” / “Yellow Paper EVM” without Absolute honesty  
- “Soak passed” without pack id + `hard_fails=0`  
- Old GitHub names as current links (`Absolute_Blockchain_Ultimate_Hybrid`, `experimental`)

---

## Demo companion

Live mesh: [DEMO_RUNBOOK.md](DEMO_RUNBOOK.md) · Ceremony rehearsal: [CEREMONY_DRY_RUN.md](CEREMONY_DRY_RUN.md)
