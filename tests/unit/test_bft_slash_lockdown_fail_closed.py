"""RoundSM must re-raise when slash/lockdown backends fail (AUDIT P1)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def test_round_sm_source_reraises_slash_and_lockdown() -> None:
    src = (ROOT / "consensus" / "bft" / "service.py").read_text(encoding="utf-8")
    chunk = src.split("mark_slashed failed")[1].split("ConsensusMaliciousError")[0]
    assert "raise" in chunk.split("lockdown failed")[0]
    assert "raise" in chunk.split("lockdown failed")[1]


def test_rocks_warns_on_silent_close_and_writeback() -> None:
    src = (ROOT / "storage" / "rocks_store.py").read_text(encoding="utf-8")
    assert "native engine drop failed" in src
    assert "get_account_rows failed, per-account load" in src
