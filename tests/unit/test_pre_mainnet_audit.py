#!/usr/bin/env python3
"""Pre-mainnet audit runner smoke tests."""

import importlib.util
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, ROOT)


def _load_audit():
    path = os.path.join(ROOT, "scripts", "pre_mainnet_audit.py")
    spec = importlib.util.spec_from_file_location("pre_mainnet_audit", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def test_pre_mainnet_audit_passes_locally():
    audit = _load_audit()
    errors, warnings, checklist = audit.run_checks()
    assert isinstance(errors, list)
    assert isinstance(warnings, list)
    assert len(checklist) >= 5
    assert errors == [], errors


def test_pre_mainnet_report_written():
    audit = _load_audit()
    errors, warnings, checklist = audit.run_checks()
    path = audit.write_report(errors, warnings, checklist)
    assert path.is_file()
    assert path.name == "pre_mainnet_audit.json"


def test_pre_mainnet_checklist_uses_live_evaluate():
    """Diligence honesty: do not paint all rows empty when auto items PASS."""
    import json
    from pathlib import Path

    from runtime.external_audit import evaluate

    audit = _load_audit()
    _warn, completed, summary = evaluate(root=Path(ROOT), live_automated=True)
    assert summary["total"] >= 5
    assert summary["completed"] >= 1, summary
    assert len(completed) == summary["completed"]
    labels = [str(i["label"]) for i in (summary.get("items") or [])]
    path = audit.write_report([], [], labels, audit_summary=summary)
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert "external_audit" in payload
    assert int(payload["external_audit"]["completed"]) == int(summary["completed"])
    assert int(payload["external_audit"]["pending"]) == int(summary["pending"])
    src = open(
        os.path.join(ROOT, "scripts", "pre_mainnet_audit.py"), encoding="utf-8"
    ).read()
    assert "live_automated=True" in src
    assert "evaluate_external_audit" in src
