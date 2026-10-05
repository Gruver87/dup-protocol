# Firm kickoff checklist (Phase 6) — industrial pin

**Product:** DUP Protocol · **Org:** DUP Labs  
**Repo:** [`Gruver87/dup-protocol`](https://github.com/Gruver87/dup-protocol)  
**Purpose:** human / org checklist to close the two remaining external-audit tracker items.  
**This file is not an audit report and not a PASS.**

Pin transport (working tip): **rust-libp2p** on prod 3-node mesh JSON (ADR 0020). Freeze tag `v1.3.1339-tip-v2-industrial` = **TCP+TLS** historical scope. **Long-Range stays off.** Pin libp2p 48h soak **not run** — disclose before firm scopes P2P.

---

## Pin identity (paste into engagement letter)

| Field | Value |
|-------|-------|
| Freeze tag | `v1.3.1339-tip-v2-industrial` |
| Freeze SHA | `0531995` (`git rev-list -n 1 v1.3.1339-tip-v2-industrial`) |
| Working tip | `git rev-parse --short HEAD` (honesty code close `adc8547`; docs tip advances) |
| Chain under review | prod-profile `778888` · bridge **OFF** |

---

## Before first firm call

- [ ] Scope = **this pin** (not Experimental as “audited”)
- [ ] Attach / regenerate static zip: `.\scripts\export_audit_pack.ps1` → latest `logs/audit_pack_YYYYMMDD.zip` (operator current: `logs/audit_pack_20261004.zip`)
- [ ] Read [AUDIT_ENGAGEMENT_BRIEF.md](AUDIT_ENGAGEMENT_BRIEF.md) · [AUDIT_SCOPE.md](AUDIT_SCOPE.md) · [THREAT_MODEL.md](THREAT_MODEL.md) · [AUDITS.md](AUDITS.md)
- [ ] Tracker shows **6/8** until firm evidence: `python scripts/external_audit_tracker.py --list`
- [ ] NDA drafted / signed
- [ ] Disclosure channel agreed ([SECURITY.md](../SECURITY.md))
- [ ] Optional Exp outreach appendix (not pin PASS): [EXTERNAL_AUDIT_ENGAGEMENT (Exp)](https://github.com/Gruver87/dup-protocol-experimental/blob/main/docs/EXTERNAL_AUDIT_ENGAGEMENT.md) · [FIRM_OUTREACH_LETTER (Exp)](https://github.com/Gruver87/dup-protocol-experimental/blob/main/docs/FIRM_OUTREACH_LETTER.md) · [phase6prep1 (Exp)](https://github.com/Gruver87/dup-protocol-experimental/tree/main/evidence/runs/phase6prep1)

## During engagement

- [ ] Schedule **penetration test** (tracker: External penetration test scheduled)
- [ ] Schedule / execute **third-party L1 (+ EVM subset) review**
- [ ] Firm gets read-only mesh **or** sealed compose + audit zip from this pin
- [ ] Findings triage: money / tip / P2P / honesty / DX

## After firm delivers evidence

```powershell
python scripts/external_audit_tracker.py --set "External penetration test scheduled" `
  --note "<vendor> scheduled <ISO-date>" --evidence-url "https://..."
python scripts/external_audit_tracker.py --set "Third-party smart-contract / L1 security audit completed" `
  --note "<vendor> report <id>" --evidence-url "https://..."
python scripts/external_audit_tracker.py --list
```

Place PDF under `audits/<firm>/report.pdf`. Do **not** mark tracker items with TBD/placeholder notes.

## Forbidden until both human items have real evidence

- “Audited” / “mainnet-ready” / listed ABS  
- Claiming Experimental soak packs as pin audit PASS  
- Enabling `feature_long_range` on prod · claiming pin libp2p soak PASS without `docs/evidence/runs/pin-libp2p-cutover-pending/` (or successor) pack  

---

Related: [FUND_DEMO_OPERATOR_PACK.md](FUND_DEMO_OPERATOR_PACK.md) · [AUDIT_PACK_CHECKLIST.md](AUDIT_PACK_CHECKLIST.md)
