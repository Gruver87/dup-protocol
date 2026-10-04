"""format_tx must observe blockHash/transactionIndex — never invent index 0."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from api.eth_format import format_tx


class _Q:
    def __init__(self) -> None:
        self.blocks: dict = {}

    def get_block(self, query):
        height = getattr(query, "height", None)
        if height is None and isinstance(query, int):
            height = query
        return self.blocks.get(int(height)) if height is not None else None


def test_format_tx_pending_fields_null() -> None:
    out = format_tx({"hash": "0xabc", "value": 0})
    assert out is not None
    assert out["blockNumber"] is None
    assert out["blockHash"] is None
    assert out["transactionIndex"] is None


def test_format_tx_index_from_block_listing() -> None:
    q = _Q()
    h = "0x" + "cd" * 32
    q.blocks[2] = {"height": 2, "hash": h, "transactions": ["0xaa", "0xbb"]}
    out = format_tx({"hash": "0xbb", "block_height": 2, "value": 0}, query=q)
    assert out is not None
    assert out["blockHash"] == h
    assert out["transactionIndex"] == hex(1)


def test_format_tx_stored_index_when_no_listing() -> None:
    out = format_tx(
        {"hash": "0xabc", "block_height": 1, "tx_index": 2, "value": 0}
    )
    assert out is not None
    assert out["transactionIndex"] == hex(2)
