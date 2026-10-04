"""ADR 0016: sprout getattr defaults fail-closed; CryptoWill gated."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_main_feature_getattr_defaults_false():
    src = (ROOT / "main.py").read_text(encoding="utf-8")
    # Fail-open True defaults must not remain for ADR 0016 sprouts.
    for flag in (
        "feature_zk",
        "feature_sharding",
        "feature_oracles",
        "feature_smart_accounts",
        "feature_pq",
        "feature_minivm",
        "feature_validator_selection",
        "feature_mev",
        "feature_lightning",
        "feature_plasma",
        "feature_wasm",
    ):
        assert f'getattr(config, "{flag}", True)' not in src, flag
        assert f'getattr(config, "{flag}", False)' in src, flag


def test_crypto_will_feature_gated():
    main_src = (ROOT / "main.py").read_text(encoding="utf-8")
    assert 'getattr(config, "feature_crypto_will", False)' in main_src
    cfg_src = (ROOT / "runtime" / "config.py").read_text(encoding="utf-8")
    assert "feature_crypto_will: bool = False" in cfg_src
    assert "FEATURE_CRYPTO_WILL" in cfg_src


def test_pq_keygen_prod_blocked():
    src = (ROOT / "api" / "http.py").read_text(encoding="utf-8")
    chunk = src.split("_PROD_BLOCKED_PATHS")[1].split(")")[0]
    assert '"/pq/keygen"' in chunk


def test_nft_ai_list_honesty_needles():
    src = (ROOT / "api" / "http.py").read_text(encoding="utf-8")
    auctions = src.split('path == "/nft/auctions"')[1].split("elif path")[0]
    assert "consensus_wired" in auctions
    assert "execution_bound" in auctions
    offers = src.split('path == "/nft/offers"')[1].split("elif path")[0]
    assert "consensus_wired" in offers
    ai = src.split('path == "/ai-agent/list"')[1].split("elif path")[0]
    assert "simulation_only" in ai
    assert "consensus_wired" in ai
