# Demo runbook — industrial pin mesh (rust-libp2p)

**Repo:** [`dup-protocol`](https://github.com/Gruver87/dup-protocol) (this tree)  
**Audience:** operator showing the **working-tip pin** to diligence / auditors.  
**Transport:** **rust-libp2p** (ADR 0020: `feature_libp2p=true`, `p2p_tls_enabled=false`).  
**Not:** a new soak · not public mainnet · not the freeze-tag TCP+TLS demo.

Full showcase index (funds / ПВТ): [SHOWCASE.md](SHOWCASE.md).  
Ops Console: [OPS_CONSOLE.md](OPS_CONSOLE.md).  
Exp live demo (R&D): Experimental [DEMO_RUNBOOK](https://github.com/Gruver87/dup-protocol-experimental/blob/main/docs/DEMO_RUNBOOK.md) — **different tree**.

---

## Goal (one session)

1. Bring up the pin **prod-profile 3-node** Docker mesh.  
2. Probe readiness (`18180–18182`).  
3. Point at [`pin-libp2p-strict-48h`](evidence/runs/pin-libp2p-strict-48h/) for the libp2p 48h PASS, and [`375d14f`](evidence/runs/375d14f/) for the historical TCP+TLS tip-v2 soak. Do not start a soak from this demo.  
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

# 2) Prod-profile 3-node mesh (rust-libp2p, ADR 0020)
.\scripts\docker_prod_3node.ps1 -SkipBuild -KeepVolumes

# 3) Quick mesh probe — expect RESULT: PASS / ports ready
.\scripts\probe_prod_mesh.ps1 -Quick

# 4) Industrial honesty gate (local)
python scripts/industrial_gate.py
```

Operator harden detail: [INDUSTRIAL_HARDEN_RUNBOOK.md](INDUSTRIAL_HARDEN_RUNBOOK.md) · [COMMANDS_REFERENCE.md](COMMANDS_REFERENCE.md).

---

## What to say in the room

- This is the **industrial pin** working tip. Freeze tag `v1.3.1339-tip-v2-industrial` is historical **TCP+TLS**, not this mesh.  
- Transport is **rust-libp2p** (Noise). Experimental soaks are not this demo.  
- Libp2p 48h PASS is [`pin-libp2p-strict-48h`](evidence/runs/pin-libp2p-strict-48h/) (`hard_fails=0`, tag not cut). TCP+TLS tip-v2 PASS is [`375d14f`](evidence/runs/375d14f/). Do not start a soak from this demo.  
- External firm audit PDF is still **pending**.  

## Forbidden

- Call this mesh TCP+TLS (that is the freeze tag and `docker/node.prod.json` only)  
- Relabel this demo as an Experimental soak  
- “Mainnet ready” / listed token  
- Start a new 48h soak from this demo  
- “Soak passed” without naming `pin-libp2p-strict-48h` or `375d14f`
