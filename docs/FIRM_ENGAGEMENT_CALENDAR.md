# Firm engagement calendar stub — Phase 6 (industrial pin)

**Status:** SCHEDULE TEMPLATE — dates blank until human books firm.  
**Tracker:** stays incomplete until real https evidence (no TBD paint).  
**Repo:** [`dup-protocol`](https://github.com/Gruver87/dup-protocol)

| Step | Owner | Target week | Done when |
|------|-------|-------------|-----------|
| NDA signed | DUP Labs + firm counsel | ____ | PDF on file ([FIRM_NDA_OUTLINE.md](FIRM_NDA_OUTLINE.md)) |
| Kickoff call (scope = pin tag / disclosed tip) | Both | ____ | Notes + SHA confirmed |
| Pen-test window | Firm | ____ | Tracker item + evidence URL |
| L1 / EVM-subset review | Firm | ____ | Report PDF + evidence URL |
| Findings triage (P0 money/tip first) | DUP Labs | ____ | Fix PRs or accepted risk |
| Re-verify `verify_audit_engagement_prep.ps1` | DUP Labs | ____ | Prep still honest |

## Commands (after real booking)

```powershell
python scripts/external_audit_tracker.py --set "External penetration test scheduled" `
  --note "<vendor> scheduled <ISO-date>" --evidence-url "https://..."
python scripts/external_audit_tracker.py --set "Third-party smart-contract / L1 security audit completed" `
  --note "<vendor> report <id>" --evidence-url "https://..."
.\scripts\verify_audit_engagement_prep.ps1
```

Forbidden: marking rows with placeholders · claiming “audited” before both human items.
