"""Engine POST success must not paint from truthy non-bool objects."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def test_http_engine_result_refuses_truthy_objects():
    from api.http import _http_engine_result

    class _Truthy:
        def __bool__(self):
            return True

    assert _http_engine_result(True) == {"success": True}
    assert _http_engine_result(False) == {"success": False}
    assert _http_engine_result(None)["error"] == "engine_returned_none"
    assert _http_engine_result(_Truthy())["success"] is False
    assert _http_engine_result(_Truthy())["error"] == "engine_result_not_boolean"
    assert _http_engine_result({"ok": 1})["ok"] == 1
    flagged = type("R", (), {"success": False, "error": "locked"})()
    out = _http_engine_result(flagged)
    assert out["success"] is False
    assert out["error"] == "locked"


def test_http_engine_result_wired_on_engine_posts():
    src = (ROOT / "api" / "http.py").read_text(encoding="utf-8")
    assert "def _http_engine_result" in src
    for path in (
        '"/smart-account/add-guardian"',
        '"/slashing/record-vote"',
        '"/beacon/vote"',
        '"/finality/finalize"',
        '"/sharding/add-tx"',
        '"/smart-account/register"',
        '"/sharding/mine"',
    ):
        chunk = src.split(f"path == {path}")[1].split("elif path ==")[0]
        assert "_http_engine_result" in chunk, path
