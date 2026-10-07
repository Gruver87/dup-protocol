# FAQ — DUP Protocol / DUP Labs (industrial pin)

**Audience:** grant officers, HTP / ПВТ, technical advisors.  
**Canonical:** English · RU summary: [ONE_PAGER_RU.md](ONE_PAGER_RU.md)  
**Source of truth for claims:** [DILIGENCE_BRIEF.md](DILIGENCE_BRIEF.md) · [FUND_READINESS.md](FUND_READINESS.md) · [SHOWCASE.md](SHOWCASE.md)  
**This tree:** [`Gruver87/dup-protocol`](https://github.com/Gruver87/dup-protocol)

---

### What is DUP Protocol?

An **industrial hybrid L1** (Python orchestration + Rust/PyO3 hot path) with a fail-closed private prod-profile mesh and evidence-backed soaks. Org face: **DUP Labs**. Author: **Uladzimir Dabranski (D.U.P.)**.

### Why two GitHub repositories?

| Repo | Role |
|------|------|
| [`dup-protocol`](https://github.com/Gruver87/dup-protocol) | Audit-freeze **industrial pin**. Freeze tag `v1.3.1339-tip-v2-industrial` (TCP+TLS soak). Working tip: ADR 0020 rust-libp2p mesh JSON. |
| [`dup-protocol-experimental`](https://github.com/Gruver87/dup-protocol-experimental) | R&D sandbox (libp2p depth, Long-Range lab, EVM STRICT, mempool Rust). **Not** pin industrial evidence. |

Do not conflate pin tip-v2 / pin Quick probe with Experimental STRICT soaks.

### Is this a public mainnet / listed token?

**No.** Ready for technical diligence on a private mesh / R&D L1. Not public audited mainnet. Not a listed token sale.

### Has an external security firm finished an audit?

**No.** Firm engagement is **prep** (checklists, outreach drafts). Not firm PASS.

### What does “soak PASS” mean here?

Only a packaged run under `docs/evidence/runs/<id>/` with report `passed=true` and `hard_fails=0`. Live demo / `probe_prod_mesh.ps1 -Quick` ≠ soak.

### What transport do I see in a demo?

- **Pin live demo** ([DEMO_RUNBOOK_PIN.md](DEMO_RUNBOOK_PIN.md)): working-tip prod 3-node mesh JSON is **rust-libp2p** (ADR 0020). Freeze-tag soak evidence is **TCP+TLS** — do not relabel.  
- **Pin libp2p 48h soak:** **deferred** (Quick probe packaged under [`pin-libp2p-cutover-pending`](evidence/runs/pin-libp2p-cutover-pending/); not 48h PASS).  
- **Experimental demo:** separate tree — [Exp DEMO_RUNBOOK](https://github.com/Gruver87/dup-protocol-experimental/blob/main/docs/DEMO_RUNBOOK.md).

### How is money represented?

**Satoshi integers only.** Float-only amounts are refused on the wire. See [FUND_READINESS.md](FUND_READINESS.md) + tip-v2 pack [`375d14f`](evidence/runs/375d14f/).

### Is Long-Range production-ready?

**No.** ADR 0017 work is **lab-only** on Experimental. Prod JSON keeps `feature_long_range=false`. Do not cite Exp LR packs as pin evidence.

### Is the bridge on?

**No** on prod mesh. Bridge stays OFF until audited L1 cutover ([MAINNET_GAP_ANALYSIS.md](MAINNET_GAP_ANALYSIS.md)). Gate: `verify_bridge_off_lab.ps1`.

### Is the NFT marketplace ERC-721 / OpenSea?

**No.** App-profile sprout; prod `feature_nft=false`. Soft escrow is not an L1 escrow contract. See [NFT_LAB_PROFILE.md](sprouts/NFT_LAB_PROFILE.md).

### What about AI agents / AI validator?

Lab sprouts only. Prod `feature_ai_agents=false` / `feature_ai_validator=false`. Not consensus-wired. See [AI_LAB_PROFILE.md](sprouts/AI_LAB_PROFILE.md).

### Former name “Absolute Blockchain”?

Same trees / evidence. Current brand: **DUP Labs / DUP Protocol**. Old Desktop folder names may still say `Absolute_*` — path only, not the GitHub name.

### Belarus trademark / patent?

**Prep pack only** for НЦИС trademark filing: [TRADEMARK_FILING_PREP_BY.md](TRADEMARK_FILING_PREP_BY.md). Not a registration certificate. Not a utility patent grant. Copyright + MIT attribution: [IP_AND_ATTRIBUTION.md](IP_AND_ATTRIBUTION.md).

### Who do we contact?

GitHub [Gruver87](https://github.com/Gruver87) · [`SECURITY.md`](../SECURITY.md). Company email / ПВТ legal entity fields in [FIRM_NDA_OUTLINE.md](FIRM_NDA_OUTLINE.md) are **placeholders** until the operator fills them — we do not invent contacts in-repo.

### Where do I start for a show?

[SHOWCASE.md](SHOWCASE.md) · live pin mesh: [DEMO_RUNBOOK_PIN.md](DEMO_RUNBOOK_PIN.md).
