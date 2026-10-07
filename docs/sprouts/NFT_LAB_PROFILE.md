# NFT marketplace lab profile (ADR 0016 Profile C / app-profile)

**Status:** sprout — **not** industrial L1 core on `778888`.  
**Repo:** industrial pin [`dup-protocol`](https://github.com/Gruver87/dup-protocol).  
**Prod mesh:** `feature_nft=false` (enforced by industrial_gate).

## What this is

| Surface | Role |
|---------|------|
| `features/nft.py` | Mint / list / buy / offer / auction + satoshi prices |
| Staging Profile C | App staging (see [APP_STAGING_PROFILE.md](APP_STAGING_PROFILE.md)) — not prod `778888` |
| `scripts/nft_lab.py` | Offline honesty lab |
| `scripts/verify_nft_marketplace.ps1` | Pin verify wrapper (`-SkipStaging` for offline) |

## Operator

```powershell
python scripts/nft_lab.py
.\scripts\verify_nft_marketplace.ps1 -SkipStaging
python -m pytest tests/unit/test_nft_marketplace_harden.py tests/unit/test_nft_uow.py tests/unit/test_nft_ports.py -q
```

Aggregator: `.\scripts\verify_sprout_labs.ps1` (includes NFT when wired).

## Honesty

- Settlement raises inside `atomic()` (no partial commit on royalty fail)
- Paid paths require store `atomic()` (`nft_uow_required`)
- Offer expiry enforced; auction finalize refuses before `ends_at`
- Soft escrow: offer/bid debit `held_satoshi`; cancel/finalize refunds; **not** L1 escrow contract
- HTTP GET `/nft/*` gated `feature_nft ∧ loaded ∧ ¬prod_block`
- Port: mint/list/buy/offer/auction/cancel_auction/delist + Null fail-closed
- HTTP mutations require actor signature unless JWT admin

## Forbidden

- `feature_nft=true` on prod `778888` JSON
- Claiming ERC-721 / OpenSea parity / mainnet marketplace
- Wiring NFT settlement into tip-safety / forge
- Claiming soak / firm PASS from this lab
