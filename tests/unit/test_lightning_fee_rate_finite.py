"""Lightning fee_rate must refuse bool / NaN at the DB boundary."""

import os
import tempfile

import pytest

from storage.database import Database


def test_save_lightning_channel_refuses_bool_and_nan_fee_rate():
    tmp = tempfile.mkdtemp()
    db = Database(os.path.join(tmp, "ln.db"))
    db.initialize()
    base = {
        "channel_id": "ch1",
        "node1": "0x" + "a" * 40,
        "node2": "0x" + "b" * 40,
        "capacity": 1.0,
        "balance1": 0.5,
        "balance2": 0.5,
        "status": "open",
        "created_at": 1,
    }
    with pytest.raises(ValueError, match="must be a number, not bool"):
        db.save_lightning_channel({**base, "fee_rate": True})
    with pytest.raises(ValueError, match="must be finite"):
        db.save_lightning_channel({**base, "fee_rate": float("nan")})
