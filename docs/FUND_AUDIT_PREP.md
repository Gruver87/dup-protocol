# Fund + external audit prep — pin snapshot (honest)

**Date:** 2026-10-09 · HEAD: run `git rev-parse --short HEAD`  
**Repo:** [`Gruver87/dup-protocol`](https://github.com/Gruver87/dup-protocol) · brand: [BRAND.md](BRAND.md)  
**Audience:** grant / investor / firm tech diligence  
**Soak:** **not running** this prep. Pin libp2p STRICT attempt **VOID** (host power-off 2026-10-08) — see [`evidence/runs/pin-libp2p-cutover-pending/SOAK_VOID_HOST_POWEROFF_2026-10-08.txt`](evidence/runs/pin-libp2p-cutover-pending/SOAK_VOID_HOST_POWEROFF_2026-10-08.txt).

This page is the **single front door** for “are you ready for funds and audit?”  
Longer maps: [FUND_READINESS.md](FUND_READINESS.md) · [DILIGENCE_BRIEF.md](DILIGENCE_BRIEF.md) · [AUDITS.md](AUDITS.md) · [MAINNET_GAP_ANALYSIS.md](MAINNET_GAP_ANALYSIS.md).

---

## Auditor / fund verdict (today)

| Question | Answer |
|----------|--------|
| Industrial private mesh proven? | **Yes** — tip-v2 TCP+TLS freeze soak (`375d14f` / tag `v1.3.1339-tip-v2-industrial`); ADR 0020 libp2p cutover + Quick probe packaged |
| Pin libp2p 48h soak PASS on HEAD? | **No** — prep READY · attempt VOID · not restarted |
| External firm PDF? | **No** — tracker **6/8** (2 firm-owned open) |
| Public mainnet / listed token? | **Not claimed** |
| Ready for technical diligence meeting? | **Yes** — private-mesh + evidence-first |
| Ready to claim “audited mainnet”? | **No** |

---

## What funds should open first (15 min)

1. This page + [DILIGENCE_BRIEF.md](DILIGENCE_BRIEF.md)  
2. [EVIDENCE_MATRIX.md](EVIDENCE_MATRIX.md) — freeze pack + `pin-libp2p-cutover-pending/`  
3. [AUDITS.md](AUDITS.md) · [AUDIT_ENGAGEMENT_BRIEF.md](AUDIT_ENGAGEMENT_BRIEF.md) · [FIRM_KICKOFF_CHECKLIST.md](FIRM_KICKOFF_CHECKLIST.md)  
4. Gaps: [MAINNET_GAP_ANALYSIS.md](MAINNET_GAP_ANALYSIS.md)  
5. Operator: [VERIFY_SUITE.md](VERIFY_SUITE.md) · [FUND_DEMO_OPERATOR_PACK.md](FUND_DEMO_OPERATOR_PACK.md)

---

## Operator bar (no soak)

```powershell
cd C:\Users\vovun\Desktop\Absolute_Blockchain_Ultimate_Hybrid
.\scripts\verify_project.ps1 -Mode Quick
.\scripts\verify_project.ps1 -Mode Industrial
python scripts/industrial_gate.py
python scripts/verify_security_honesty.py   # security-honesty needles + unit slice
python scripts/external_audit_tracker.py --list
.\scripts\export_audit_pack.ps1
# optional live mesh (already up):
.\scripts\probe_prod_mesh.ps1 -Quick
.\scripts\docker_testnet_mesh3.ps1   # public testnet 77777 demo
```

---

## Org blockers (Phase 6 — not code)

1. Schedule external penetration test  
2. Contract third-party L1 / EVM security audit → PDF under `audits/<firm>/`  
3. Live ceremony pin + secret rotation on cutover day only  
4. Fresh pin libp2p 48h soak when operator chooses (**not** this prep)

---

## Cruft removed / quarantined

| Action | Why |
|--------|-----|
| Nested `nft_images/nft_images/`, empty `services`/`db`/`node` | Duplicate / husks (wave 1) |
| `SOAK_IN_PROGRESS.txt` → `SOAK_STOPPED_VOID.txt` | Dishonest filename |
| Root marketing `linkedin_*` / `twitter_*` / `social_*` / HTML explorers / `nft_core.py` / obsolete `init_git`/`build_docker` / `ARCHITECTURE_AUDIT.md` | Noise, not industrial evidence (wave 2) |
| `docker-compose.yml` / `.ha.yml` / `.observability.yml` | DEPRECATED / OPTIONAL LAB headers |
| `docs/evidence/runs/latest/README.md` | Pointer-only honesty (not HEAD soak) |
| Brand pass: DISCLAIMER, CoC, IR/DR, ADR README, RELEASING, PR template | DUP Labs current; Absolute = formerly |
| `RELEASE_NOTES_v*.md` stay at repo root | Gate needles — see [releases/README.md](releases/README.md) |

**Do not touch:** sealed packs under `docs/evidence/runs/375d14f/`, phase packs, cutover VOID artifacts. Prometheus alert *names* `Absolute*` (gate needles).

---

## Honesty lines (copy-paste)

- PASS on verify / industrial_gate ≠ public mainnet  
- tip-v2 soak PASS is **TCP+TLS freeze-tag** evidence, not current-HEAD libp2p soak  
- Harness soft-PASS requires peer-match wire evidence (`runtime/harness_honesty.py`); sticky `_state_consistent` lag alone does not greenwash  
- `/health/ready` still fail-closed on the live P2P flag when peers are present  

- Experimental packs (`3c801b87`, Long-Range, Exp EVM STRICT) are **not** pin industrial evidence  
- Bridge stays OFF on live mesh without audited L1 cutover  
