"""EVM opcode-map honesty (Absolute-native ≠ Yellow Paper)."""

from __future__ import annotations

from execution.evm_runtime import compat_matrix_rows, evm_compat_honesty_snapshot


def test_compat_matrix_discloses_absolute_opcode_map():
    rows = {r["area"]: r for r in compat_matrix_rows()}
    assert "opcode_map_yellow_paper" in rows
    assert rows["opcode_map_yellow_paper"]["status"] == "absolute_native"
    assert "Yellow Paper" in rows["opcode_map_yellow_paper"]["notes"]


def test_evm_status_snapshot_opcode_map_honesty():
    snap = evm_compat_honesty_snapshot(None)
    oh = snap["opcode_map_honesty"]
    assert oh["yellow_paper_compatible"] is False
    assert oh["absolute_native_map"] is True
    assert oh["example"]["absolute_0x10"] == "AND"
    assert oh["example"]["yellow_paper_0x10"] == "LT"
    assert "Yellow Paper" in snap["detail"] or "Absolute opcode map" in snap["detail"]
