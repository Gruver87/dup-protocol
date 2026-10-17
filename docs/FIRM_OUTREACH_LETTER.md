# Firm outreach letter (copy-paste draft)

**Status:** draft for operator — **not** an audit contract and **not** a PASS.  
**Fill brackets before send.** Prefer English for international firms.

---

Subject: DUP Protocol — security review engagement (industrial pin `v1.3.1339-tip-v2-industrial`)

---

Hello [Firm / Partner name],

We are **DUP Labs** (product **DUP Protocol**), seeking a **scoped external security review** of our industrial L1 pin — not a marketing “audit badge” exercise.

### Scope (proposed)

- **Primary tree:** https://github.com/Gruver87/dup-protocol  
- **Freeze tag:** `v1.3.1339-tip-v2-industrial`  
- **Chain:** prod-profile `778888`, 3-node Docker mesh, tip encoding v2 (`b_satoshi`), RocksDB, native crypto required, **bridge OFF**. Working-tip transport is rust-libp2p (ADR 0020). Freeze tag `v1.3.1339-tip-v2-industrial` is historical TCP+TLS.
- **In scope:** tip-safety / import refuse, satoshi money path, libp2p mesh honesty, API/RPC auth, RocksDB + DR scripts, `abs_native` hot path. Libp2p STRICT pack: `docs/evidence/runs/pin-libp2p-strict-48h/` (not mainnet; tag `v1.3.1340` not cut).
- **Out of scope (explicit):** bridge ON, prod Long-Range, full geth parity, public mainnet ops, ZK “real circuits”

Optional R&D appendix (label as Experimental, not pin):  
https://github.com/Gruver87/dup-protocol-experimental — tip at kickoff: `[paste git rev-parse HEAD]`

### Starting documents

| Doc | URL |
|-----|-----|
| Engagement letter | https://github.com/Gruver87/dup-protocol/blob/master/docs/EXTERNAL_AUDIT_ENGAGEMENT.md |
| Firm one-pager | https://github.com/Gruver87/dup-protocol/blob/master/docs/AUDIT_ENGAGEMENT_BRIEF.md |
| Human kickoff checklist | https://github.com/Gruver87/dup-protocol/blob/master/docs/FIRM_KICKOFF_CHECKLIST.md |
| Diligence brief | https://github.com/Gruver87/dup-protocol/blob/master/docs/DILIGENCE_BRIEF.md |
| Threat model | https://github.com/Gruver87/dup-protocol/blob/master/docs/THREAT_MODEL.md |
| Honest gaps | https://github.com/Gruver87/dup-protocol/blob/master/docs/MAINNET_GAP_ANALYSIS.md |
| Libp2p STRICT pack | https://github.com/Gruver87/dup-protocol/blob/master/docs/evidence/runs/pin-libp2p-strict-48h/README.md |

Pin engagement brief (same product, freeze tree):  
https://github.com/Gruver87/dup-protocol/blob/master/docs/AUDIT_ENGAGEMENT_BRIEF.md

### What we need from you

1. Written report with severity ratings  
2. Repro notes against the **pin tag**  
3. Explicit confirmation tip-v2 + satoshi path were in the reviewed build  
4. PDF delivery path agreed in NDA  

### Access

We can provide: sealed Docker compose + audit zip, and/or time-boxed read-only mesh access under NDA.

### Contact

GitHub: [@Gruver87](https://github.com/Gruver87) · private disclosure: repository Security Advisories / owner channel  
Author: Uladzimir Dabranski (D.U.P.)

We will **not** claim “audited” or “mainnet-ready” until your report is on disk with real evidence URLs in our tracker.

Best regards,  
[Your name]  
DUP Labs

---

**Operator:** after send, do **not** mark tracker items done until vendor schedule/report evidence exists (`docs/FIRM_KICKOFF_CHECKLIST.md`).
