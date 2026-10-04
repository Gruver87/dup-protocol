"""NFT HTTP mutations require actor signature unless jwt_enforce_admin."""
from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def test_nft_mutation_auth_requires_sig_without_jwt():
    from api.http import _nft_mutation_authorized

    cfg = SimpleNamespace(jwt_enforce_admin=False)
    err = _nft_mutation_authorized(cfg, {"token_id": "t1"}, "0x" + "a" * 40)
    assert err and "signature" in err

    cfg2 = SimpleNamespace(jwt_enforce_admin=True)
    assert _nft_mutation_authorized(cfg2, {}, "0x" + "a" * 40) is None


def test_nft_mutation_auth_needles_on_http_paths():
    src = (ROOT / "api" / "http.py").read_text(encoding="utf-8")
    assert "def _nft_mutation_authorized" in src
    for path in (
        '"/nft/buy"',
        '"/nft/list"',
        '"/nft/transfer"',
        '"/nft/auction"',
        '"/nft/bid"',
        '"/nft/offer"',
        '"/nft/cancel-offer"',
        '"/nft/accept-offer"',
        '"/nft/cancel-auction"',
        '"/nft/finalize-auction"',
    ):
        chunk = src.split(f"path == {path}")[1].split("elif path ==")[0]
        assert "_nft_mutation_authorized" in chunk, path
        if path == '"/nft/buy"':
            assert "401" in chunk
        if path == '"/nft/offer"':
            assert "403" in chunk
        if path == '"/nft/finalize-auction"':
            assert "nft finalize requires actor+signature" in chunk
