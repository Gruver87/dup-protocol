"""EIP-214 static write refuse, CREATE endowment, P2P mempool dup-check honesty."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def test_interpreter_static_write_helpers() -> None:
    src = (ROOT / "evm_interpreter.py").read_text(encoding="utf-8")
    assert "def _in_static_context" in src
    assert "def _revert_static_write" in src
    assert src.count("_revert_static_write()") >= 5


def test_rust_static_write_protection_needles() -> None:
    src = (
        ROOT / "native" / "abs_native" / "src" / "evm_pure_runner.rs"
    ).read_text(encoding="utf-8")
    assert "fn refuse_static_write" in src
    assert "fn get_inline_read_only" in src
    assert "static_write_protection" in src
    assert "_abs_inline_read_only" in src


def test_create_hook_pre_endowment() -> None:
    src = (ROOT / "execution" / "evm_adapter.py").read_text(encoding="utf-8")
    chunk = src.split("def _contract_create_hook")[1].split("\n    def ")[0]
    assert "_transfer_sat_fail_closed" in chunk
    assert "insufficient_call_value" in chunk
    assert "_refund_sat" in chunk
    assert "journal_snap" in chunk


def test_host_context_copies_read_only() -> None:
    src = (ROOT / "crypto" / "native.py").read_text(encoding="utf-8")
    chunk = src.split("def evm_host_context_from_evm")[1].split("\ndef ")[0]
    assert 'host["_abs_read_only"]' in chunk


def test_p2p_mempool_dup_check_fails_closed() -> None:
    src = (ROOT / "network" / "p2p_node.py").read_text(encoding="utf-8")
    chunk = src.split("Cheap duplicate refuse")[1].split("v1.3.177")[0]
    assert "mempool_dup_check_failed" in chunk
    assert "except Exception:\n                pass" not in chunk
