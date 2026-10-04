"""WASM call must not pretend L1 value transfer."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def test_wasm_call_refuses_nonzero_value():
    src = (ROOT / "api" / "http.py").read_text(encoding="utf-8")
    chunk = src.split('path == "/wasm/call"')[1].split("elif path")[0]
    assert "wasm call value not L1-bound" in chunk
    assert "l1_value_applied" in chunk
    assert "_http_amount_abs" in chunk
    assert 'value=_http_abs(body.get("value", 0)' not in chunk
