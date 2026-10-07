# Demo runbook — industrial pin mesh (TCP+TLS)

**Repo:** [`dup-protocol`](https://github.com/Gruver87/dup-protocol) (this tree)  
**Audience:** operator showing the **audit-freeze pin** to diligence / auditors.  
**Transport:** **TCP+TLS** (pin default).  
**Not:** Experimental libp2p demo · not a soak claim · not public mainnet.

Full showcase index (funds / ПВТ): [SHOWCASE.md](SHOWCASE.md).  
Ops Console: [OPS_CONSOLE.md](OPS_CONSOLE.md).  
Exp live demo (R&D): Experimental [DEMO_RUNBOOK](https://github.com/Gruver87/dup-protocol-experimental/blob/main/docs/DEMO_RUNBOOK.md) — **different tree**.

---

## Goal (one session)

1. Bring up the pin **prod-profile 3-node** Docker mesh.  
2. Probe readiness (`18180–18182`).  
3. Point at packaged tip-v2 evidence [`375d14f`](evidence/runs/375d14f/) if discussing soak history.  
4. Optional: auditor path [AUDIT_ENGAGEMENT_BRIEF.md](AUDIT_ENGAGEMENT_BRIEF.md).

---

## Prerequisites (Windows)

- Docker Desktop running  
- Python 3.11+ on PATH  
- Repo root: local pin folder (GitHub: `dup-protocol`)  
- Native wheel when required by your pin scripts: `.\scripts\build_native.ps1`

---

## Steps

```powershell
# 1) Native (skip if already current)
.\scripts\build_native.ps1

# 2) Prod-profile 3-node mesh (TCP+TLS pin)
.\scripts\docker_prod_3node.ps1 -SkipBuild -KeepVolumes

# 3) Quick mesh probe — expect RESULT: PASS / ports ready
.\scripts\probe_prod_mesh.ps1 -Quick

# 4) Industrial honesty gate (local)
python scripts/industrial_gate.py
```

Operator harden detail: [INDUSTRIAL_HARDEN_RUNBOOK.md](INDUSTRIAL_HARDEN_RUNBOOK.md) · [COMMANDS_REFERENCE.md](COMMANDS_REFERENCE.md).

---

## What to say in the room

- This is the **industrial pin** — freeze-safe for firm engagement prep.  
- Transport is **TCP+TLS**, not Experimental libp2p.  
- Tip-v2 48h soak PASS is packaged as [`375d14f`](evidence/runs/375d14f/) — cite the pack, do not invent new soak from this demo.  
- External firm audit PDF is still **pending** (Phase 4 binder READY).  

## Forbidden

- Relabel this demo as libp2p Experimental  
- “Mainnet ready” / listed token  
- “Soak passed” without naming the on-disk pack
