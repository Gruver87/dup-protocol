#!/usr/bin/env python3
"""HTTP concurrency bound + adversarial mempool identity (audit sections 14/24)."""

from __future__ import annotations

import os
import sys
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from api.http import ThreadedHTTPServer, _http_max_concurrent_requests
from blockchain.mempool import Mempool, MempoolTransaction
from core.tx_identity import bind_identity_from_fields
from crypto.wallet import Wallet


class _SlowHandler(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        time.sleep(0.15)
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"ok")

    def log_message(self, *_args):
        return


def test_http_max_concurrent_config_helper():
    class C:
        http_max_concurrent_requests = 7

    assert _http_max_concurrent_requests(C()) == 7
    assert _http_max_concurrent_requests(None) == 128


def test_threaded_server_respects_max_concurrent():
    server = ThreadedHTTPServer(
        ("127.0.0.1", 0), _SlowHandler, max_concurrent_requests=2
    )
    assert server.max_concurrent_requests == 2
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        import urllib.request

        port = server.server_address[1]
        url = f"http://127.0.0.1:{port}/"
        results: list[str] = []
        lock = threading.Lock()

        def _one():
            try:
                with urllib.request.urlopen(url, timeout=5) as resp:
                    body = resp.read().decode()
            except Exception as exc:  # noqa: BLE001 — collect failure class
                body = f"err:{type(exc).__name__}"
            with lock:
                results.append(body)

        workers = [threading.Thread(target=_one) for _ in range(4)]
        for w in workers:
            w.start()
        for w in workers:
            w.join(timeout=10)
        assert len(results) == 4
        assert results.count("ok") == 4
    finally:
        server.shutdown()
        server.server_close()


def test_mempool_rebinding_collapses_alternate_claimed_hashes():
    """Same payload under different claimed hashes → one canonical identity."""
    w = Wallet.create_new()
    signed = w.sign_transaction(to="0x" + "ab" * 20, value=1, nonce=0, chain_id=77777, gas_limit=21000)
    ts = 1_700_000_100
    canon, _ = bind_identity_from_fields(
        "",
        from_addr=signed["from"],
        to_addr=signed["to"],
        value=signed["value"],
        nonce=signed["nonce"],
        gas=int(signed["gas_limit"]),
        data=signed.get("data") or "",
        timestamp=ts,
        chain_id=77777,
    )
    mp = Mempool(max_size=100, min_fee=0)
    if hasattr(mp, "min_fee_satoshi"):
        mp.min_fee_satoshi = 0
    mp.require_signatures = False
    mp.chain_id = 77777

    def _mk(claimed: str) -> MempoolTransaction:
        kw = dict(
            tx_hash=claimed,
            from_addr=signed["from"],
            to_addr=signed["to"],
            amount=signed["value"],
            fee=0.0,
            nonce=int(signed["nonce"]),
            signature=signed.get("signature") or "",
            public_key=signed.get("public_key") or "",
            data=signed.get("data") or "",
            gas=int(signed["gas_limit"]),
            timestamp=float(ts),
        )
        try:
            return MempoolTransaction(**kw, fee_satoshi=0, amount_satoshi=1_000_000)
        except TypeError:
            return MempoolTransaction(**kw)

    forged = _mk("ff" * 32)
    assert mp.add(forged, signature_preverified=True, chain_prevalidated=True) is False

    first = _mk("")
    assert mp.add(first, signature_preverified=True, chain_prevalidated=True) is True
    assert first.tx_hash == canon

    second = _mk(str(signed.get("hash") or ""))
    assert mp.add(second, signature_preverified=True, chain_prevalidated=True) is False
    assert second.tx_hash == canon
