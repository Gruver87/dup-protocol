# Demo runbook — 3-node mesh + Ops Console (fund / ПВТ)

**Repo:** [`dup-protocol-experimental`](https://github.com/Gruver87/dup-protocol-experimental)  
**Audience:** operator showing a live private mesh to diligence / HTP reviewers.  
**Not:** public mainnet · not a soak claim · not industrial pin TCP+TLS unless you switch compose.

---

## Goal (one session)

1. Bring up the **prod-profile 3-node** Docker mesh.  
2. Probe readiness (`18180–18182`).  
3. Open **Ops Console** (live wallets / council / health).  
4. Optionally point at a packaged STRICT evidence pack on disk.

Soak is **not** part of this demo unless an evidence pack already exists.

---

## Prerequisites (Windows)

- Docker Desktop running  
- Python 3.11+ on PATH  
- Repo root: local `Absolute_Blockchain_Experimental` (GitHub name: `dup-protocol-experimental`)  
- Native wheel built at least once: `.\scripts\build_native.ps1`

---

## Steps

```powershell
# 1) Native (skip if already current)
.\scripts\build_native.ps1

# 2) Prod-profile 3-node mesh (keep volumes for repeat demos)
.\scripts\docker_prod_3node.ps1 -SkipBuild -KeepVolumes

# 3) Quick mesh probe — must print RESULT: PASS (or equivalent ready ports)
.\scripts\probe_prod_mesh.ps1 -Quick

# 4) Industrial honesty gate (local static needles)
python scripts/industrial_gate.py

# 5) Ops Console (static + API against live nodes)
.\scripts\open_ops_console.ps1
```

Console doc: [`OPS_CONSOLE.md`](OPS_CONSOLE.md). Explorer is **legacy UI** — prefer console for diligence demos.

---

## What to show (honest script)

| Surface | Claim |
|---------|--------|
| `/health/ready` on three nodes | Prod mesh ready when P2P bound + checks green |
| Ops Console wallets / tip | Live RPC against mesh — not mocked theater |
| Evidence folder (optional) | Open one pack under `docs/evidence/runs/` — e.g. tip / libp2p STRICT — **only if present** |
| Opcode / EVM | Absolute opcode map ≠ Yellow Paper — see `/evm/status` `opcode_map_honesty` |

**Refuse to say:** “mainnet ready”, “Yellow Paper EVM”, “48h soak passed today” (unless that pack was run).

---

## Tear-down

```powershell
# Compose project name follows docker_prod_3node.ps1 (typically abs-prod-3node)
docker compose -p abs-prod-3node down
# Keep volumes if you want a warm demo next time; else add -v
```

---

## Failure triage

| Symptom | Action |
|---------|--------|
| Ports 18180–18182 down | `docker logs` on crashed node; fix stack — do not paint green |
| `probe_prod_mesh.ps1` FAIL | Stop demo; do not claim mesh |
| Console empty / CORS | Confirm API origin allow-list + console open script targets |

---

**Related:** [CEREMONY_DRY_RUN.md](CEREMONY_DRY_RUN.md) · [INVESTOR_DECK_SKELETON.md](INVESTOR_DECK_SKELETON.md) · [DILIGENCE_BRIEF.md](DILIGENCE_BRIEF.md)
