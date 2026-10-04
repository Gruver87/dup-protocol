"""Poll /status must use cached supply/burn getters (no full account scan)."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_sqlite_cached_supply_is_none_honest():
    from storage.database import Database

    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    try:
        db = Database(path)
        db.initialize()
        assert db.get_cached_total_supply() is None
        assert db.get_cached_total_burned() is None
        db.record_burn(1, 0.5)
        burned = db.get_cached_total_burned()
        assert burned is not None
        assert float(burned) == 0.5
    finally:
        try:
            db.close()
        except Exception:
            pass
        os.unlink(path)


def test_status_source_uses_cached_metric():
    http_py = (ROOT / "api" / "http.py").read_text(encoding="utf-8")
    assert "def _status_cached_metric" in http_py
    assert 'get_cached_total_supply' in http_py
    assert 'get_cached_total_burned' in http_py
    # Poll path must not call full getters for money fields.
    status_chunk = http_py.split('if path == "/status":', 1)[1][:2500]
    assert "get_cached_total_supply" in status_chunk
    assert "get_cached_total_burned" in status_chunk
    assert "db.get_total_supply()" not in status_chunk
    assert "db.get_total_burned()" not in status_chunk


def test_rocks_source_has_supply_meta_hooks():
    rocks = (ROOT / "storage" / "rocks_store.py").read_text(encoding="utf-8")
    assert "def _adjust_total_supply_abs" in rocks
    assert "def get_cached_total_supply" in rocks
    assert "def get_cached_total_burned" in rocks
    assert 'kc.key_meta("total_supply_abs")' in rocks
