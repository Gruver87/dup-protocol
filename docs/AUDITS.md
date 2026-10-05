# Audits — honest status

**External third-party L1 / smart-contract / penetration audit: not completed.**

This file exists so the repository matches professional open-source practice
(OpenZeppelin-style honesty): a single place that states audit status without
marketing theater.

| Scope | Status | Notes |
|-------|--------|-------|
| In-repo industrial gates (`industrial_gate`, `verify_industrial_waves`) | Active | Code/evidence checks — **not** an external audit |
| Native fuzz (`fuzz-native.yml`) | Active | Coverage-guided / API fuzz — **not** formal verification |
| Security workflow (`security-audit.yml`) | Active | pip-audit + cargo-audit (scoped pyo3 ignores until PR #7) |
| Threat model + scope letter | Ready for engagement | [THREAT_MODEL.md](THREAT_MODEL.md) · [AUDIT_SCOPE.md](AUDIT_SCOPE.md) · [AUDIT_ENGAGEMENT_BRIEF.md](AUDIT_ENGAGEMENT_BRIEF.md) · [AUDIT_PACK_CHECKLIST.md](AUDIT_PACK_CHECKLIST.md) · tag `v1.3.1339-tip-v2-industrial` |
| Independent external audit report | **Pending** | Firm TBD — PDF goes under `audits/<firm>/`; tracker must stay open until then (6/8 automated; 2 firm-owned open) |
| Bug bounty (Immunefi / etc.) | **Not configured** | Disclose via [SECURITY.md](../SECURITY.md) |

## Engagement targets (replace when contracted)

| Field | Value |
|-------|-------|
| Firm | _TBD — do not fake_ |
| Kickoff date | _TBD_ |
| Report URL / path | `audits/<firm>/report.pdf` when received |
| Tracker | `python scripts/external_audit_tracker.py --list` |

When an external report exists, place PDFs under `audits/<firm>/` and link them
from this table. Do **not** claim “audited” in README until that lands.
Do **not** mark tracker items complete with template notes.

Related: [SECURITY.md](../SECURITY.md) · [MAINNET_GAP_ANALYSIS.md](MAINNET_GAP_ANALYSIS.md) · [EVIDENCE_MATRIX.md](EVIDENCE_MATRIX.md) · [INDUSTRIAL_HARDEN_RUNBOOK.md](INDUSTRIAL_HARDEN_RUNBOOK.md) · [DEPENDABOT_TRIAGE.md](DEPENDABOT_TRIAGE.md)

## Safe Hybrid work (Exp→pin honesty CLOSED — code tip `adc8547`)

**ADR 0020:** working-tip prod 3-node mesh JSON on this pin is **rust-libp2p** (`feature_libp2p=true`). Freeze tag `v1.3.1339-tip-v2-industrial` remains **TCP+TLS** sealed evidence. **Post-cutover Quick probe PASS** packaged under `docs/evidence/runs/pin-libp2p-cutover-pending/`. **Pin libp2p 48h soak deferred** until full Exp→pin merge complete (premature restart stopped — not PASS).

Experimental owns Long-Range R&D and completed libp2p soaks on **its** tree (**B1 PASS** there) — **do not** cite `3c801b87`, `lp2pstrict1`, or `0a7932c4` as pin libp2p proof. Honesty Exp→pin merge is **CLOSED** (units + `industrial_gate`; **not** pin libp2p soak). Working tip: `git rev-parse --short HEAD`. On **this** pin, prefer:

1. External audit engagement prep — [FIRM_KICKOFF_CHECKLIST.md](FIRM_KICKOFF_CHECKLIST.md) · [AUDIT_ENGAGEMENT_BRIEF.md](AUDIT_ENGAGEMENT_BRIEF.md) · [AUDIT_PACK_CHECKLIST.md](AUDIT_PACK_CHECKLIST.md) · regenerate audit pack (**Phase 6 / org**)
2. Ops dry-runs (DR / ceremony / bridge-OFF) — no prod secret `-Force` unless cutover day
3. Actions-only Dependabot when CI green (see [DEPENDABOT_TRIAGE](DEPENDABOT_TRIAGE.md)) — **hold** pyo3 / socket2 majors
4. Sprout profiles **off** `778888` (staging / L2 / shard lab compose)

**Operator commands (local, no Experimental port):**

```powershell
cd C:\Users\vovun\Desktop\Absolute_Blockchain_Ultimate_Hybrid
.\scripts\export_audit_pack.ps1
python scripts/external_audit_tracker.py --list
python scripts/industrial_gate.py
```

Optional Exp Phase 6 appendix (prep only, **not** pin PASS): [EXTERNAL_AUDIT_ENGAGEMENT](https://github.com/Gruver87/dup-protocol-experimental/blob/main/docs/EXTERNAL_AUDIT_ENGAGEMENT.md) · [phase6prep1](https://github.com/Gruver87/dup-protocol-experimental/tree/main/evidence/runs/phase6prep1).

**Do not:** enable `feature_long_range` on prod · claim Experimental soaks (`3c801b87`, `lp2pstrict1`, `0a7932c4`, `lr2hmesh`, `lr48pass1`, `evm48pass1`) as **pin** libp2p/tip-v2 evidence · claim pin libp2p soak PASS without `pin-libp2p-cutover-pending` (or successor) pack · run Experimental soak scripts as pin proof.
