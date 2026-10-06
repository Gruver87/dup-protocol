# Ceremony dry-run pack (organizational)

**Purpose:** Rehearse genesis ceremony **without** promoting keys to live mainnet.  
**Canonical ceremony doc:** [GENESIS_CEREMONY.md](GENESIS_CEREMONY.md) · secrets: [sprouts/CEREMONY_AND_SECRETS.md](sprouts/CEREMONY_AND_SECRETS.md)  
**Rule:** never commit private keys · never put ceremony secrets in prod JSON · file-based secrets refused in production.

---

## Dry-run checklist

1. **Offline keygen (lab dir only)**  
   ```powershell
   python scripts/genesis_ceremony_keygen.py --out data/ceremony_keys_dryrun
   ```
   Confirm outputs stay under a gitignored path.

2. **Evidence suite (dry)**  
   ```powershell
   .\scripts\ceremony_evidence_suite.ps1 -CeremonyDir data/ceremony_keys_dryrun
   .\scripts\pin_ceremony_hash.ps1 -CeremonyDir data/ceremony_keys_dryrun
   ```

3. **Build artifact (lab)**  
   Follow `scripts/genesis_ceremony.py` with the dry-run manifest — do **not** point live `validators_manifest_path` at dry-run keys.

4. **Verify wallets (read-only)**  
   ```powershell
   python scripts/genesis_ceremony_verify_wallet.py --help
   ```
   Run against dry-run wallets only.

5. **Honesty gate**  
   - `feature_long_range=false` on prod JSON  
   - Bridge OFF unless separately ordered  
   - No claim of “ceremony complete for public mainnet” until third-party audit + live key ceremony

---

## Pack layout (suggested)

```text
docs/evidence/runs/<ceremony-dryrun-id>/
  README.md              # operator notes + git SHA
  ceremony_preflight.json
  ceremony_result.json   # dry-run only
  hashes.txt
```

Do not copy dry-run private material into evidence packs — digests / public addresses only.

---

## Pass / fail (dry-run)

| Check | Pass |
|-------|------|
| Keygen produces addresses matching manifest public fields | Required |
| Hash pin script exits 0 | Required |
| No secrets under `docs/` or git | Required |
| Prod mesh still boots with **non-dry** ceremony path unset or example-only | Required |

**Live ceremony** remains an organizational Phase 6 gate — this pack only proves the **procedure**.

---

**Related:** [DEMO_RUNBOOK.md](DEMO_RUNBOOK.md) · [INVESTOR_DECK_SKELETON.md](INVESTOR_DECK_SKELETON.md)
