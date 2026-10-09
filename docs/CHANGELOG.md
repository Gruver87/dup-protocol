# Documentation changelog

Documentation-only releases for the industrial pin. **Product / code changelog:** [../CHANGELOG.md](../CHANGELOG.md).

Format based on [Keep a Changelog](https://keepachangelog.com/).

---

## [Unreleased]

### Sprout lab profiles + elevator / firm calendar

- Pin-honest NFT/AI/Oracle lab profiles, elevator pitch, firm engagement calendar,
  legacy network quarantine; SHOWCASE / VERIFY_SUITE links.

### Pin FAQ / ONE_PAGER + diligence link honesty

- Added pin-honest `FAQ.md`, `ONE_PAGER.md`, `ONE_PAGER_RU.md`, `OPS_CONSOLE.md`;
  `DEMO_RUNBOOK.md` → pin stub; `SHOWCASE.md` local paths; `secrets/README.md`.
- ADR 0021 Exp EXECUTION_ORDER / pack links fixed to Exp GitHub.

### ADR 0020 — libp2p industrial mesh (pin docs)

- **Transport honesty:** prod 3-node mesh JSON (`778888`) is **rust-libp2p** (`feature_libp2p=true`, `p2p_tls_enabled=false`). TCP+TLS/mTLS remains the **alternate** profile (`docker/node.prod.json`, ceremony, `feature_libp2p=false`). Long-Range stays **off** / refuse.
- **Evidence:** tag `v1.3.1339-tip-v2-industrial` and sealed tip-v2 packs remain **historical TCP+TLS** — do not relabel. Pin libp2p 48h soak **VOID** (2026-10-08 · not PASS); pack [`evidence/runs/pin-libp2p-cutover-pending/`](evidence/runs/pin-libp2p-cutover-pending/). Do **not** cite Experimental soaks `3c801b87` / `lp2pstrict1` as pin evidence.
- **Suggested release tag (operator, after soak + probe):** `v1.3.1340-libp2p-industrial-mesh` — **not tagged** until mesh probe + 48h `hard_fails=0` pack exist on pin HEAD.
- Synced: [EVIDENCE_MATRIX.md](EVIDENCE_MATRIX.md) · [MAINNET_GAP_ANALYSIS.md](MAINNET_GAP_ANALYSIS.md) · [FUND_DEMO_OPERATOR_PACK.md](FUND_DEMO_OPERATOR_PACK.md) · audit scope / threat model · [FIRM_KICKOFF_CHECKLIST.md](FIRM_KICKOFF_CHECKLIST.md) · [adr/0020-libp2p-industrial-mesh.md](adr/0020-libp2p-industrial-mesh.md) · [adr/README.md](adr/README.md).
