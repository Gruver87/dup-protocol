"""bridge_off_audit_gate accepts sealed bridge_decision_off evidence."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _load_gate():
    spec = importlib.util.spec_from_file_location(
        "bridge_off_audit_gate", ROOT / "scripts" / "bridge_off_audit_gate.py"
    )
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_sealed_bridge_decision_off_exists():
    sealed = ROOT / "docs" / "evidence" / "runs" / "bridgeoff1" / "bridge_decision_off.json"
    assert sealed.is_file()
    import json

    doc = json.loads(sealed.read_text(encoding="utf-8"))
    assert doc["name"] == "bridge_decision_off"
    assert doc["result"] == "PASS"


def test_gate_source_accepts_sealed_pack():
    src = (ROOT / "scripts" / "bridge_off_audit_gate.py").read_text(encoding="utf-8")
    assert "bridgeoff1/bridge_decision_off.json" in src.replace("\\", "/")
    assert "sealed bridgeoff1 pack" in src
