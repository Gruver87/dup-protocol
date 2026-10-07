# AI / MEV lab profile (ADR 0016 sprouts)

**Status:** experimental / analysis / dev-test — **not** industrial L1 core.  
**Repo:** industrial pin [`dup-protocol`](https://github.com/Gruver87/dup-protocol).  
**Prod mesh:** `feature_ai_agents=false`, `feature_ai_validator=false`, `feature_mev=false`.

## What this is

| Module | Role | Consensus-wired? |
|--------|------|------------------|
| `features/ai_manager.py` | Agent registry + optional `ModelPort` | **No** |
| `features/ai_ports.py` | Fail-closed model binding | **No** |
| `features/ai_validator.py` | Heuristic validator sim | **No** |
| `features/mev_analyzer.py` | Mempool fee heuristics | **No** |
| `scripts/ai_ops_anomaly.py` | Off-node ready/status triage | **No** |
| `scripts/ai_lab.py` | Offline honesty lab | **No** |

## Operator checks

```powershell
python scripts/ai_lab.py
python scripts/ai_ops_anomaly.py --offline-only
.\scripts\verify_sprout_labs.ps1
pytest tests/unit/test_ai_sprout_harden.py tests/unit/test_wave43_ai_agents.py -q
```

## Honesty

- HTTP `/ai/*` and `/ai/register-validator` enabled only when `feature_ai_validator` ∧ loaded ∧ ¬prod_block
- HTTP `/ai-agent/*` gated the same way on `feature_ai_agents`
- Forge path must **not** call AI validator into tip-safety
- `ai_ops` triage is simulation / off-node only
- MEV stub surfaces `profit_satoshi=None` where not proven
- Prod JSON keeps AI/MEV flags **false**

## Forbidden

- Flipping AI/MEV flags on prod `778888` mesh JSON
- Binding AI output into tip-safety / proposer forge
- Claiming soak / mainnet / firm PASS from these labs
