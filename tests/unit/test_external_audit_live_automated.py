"""Live automated external-audit evaluate (no gitignored status file required)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime.external_audit import (
    AUTOMATED_ITEMS,
    HUMAN_REQUIRED_AUDIT_ITEMS,
    evaluate,
)


def test_evaluate_live_automated_marks_pass_without_status_file(tmp_path):
    status = tmp_path / "empty_status.json"
    warnings, completed, summary = evaluate(
        status_path=status,
        root=ROOT,
        live_automated=True,
    )
    assert summary["live_automated"] is True
    for label in AUTOMATED_ITEMS:
        assert label in completed, label
    for label in HUMAN_REQUIRED_AUDIT_ITEMS:
        assert label not in completed
        assert any(label in w for w in warnings)


def test_evaluate_without_live_keeps_empty_status_pending(tmp_path):
    status = tmp_path / "empty_status.json"
    warnings, completed, summary = evaluate(
        status_path=status,
        root=ROOT,
        live_automated=False,
    )
    assert completed == []
    assert summary["pending"] == summary["total"]
    assert len(warnings) == summary["total"]
