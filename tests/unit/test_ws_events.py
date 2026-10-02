from network.ws_events import normalize_block_event, normalize_tx_event
from runtime.amount import to_satoshi


def test_normalize_block_from_dict():
    b = normalize_block_event({
        "height": 42,
        "hash": "abc123",
        "tx_count": 3,
        "total_burned": 0.5,
    })
    assert b["height"] == 42
    assert b["hash"] == "abc123"
    assert b["txs"] == 3
    assert b["burned"] == 0.5
    assert b["burned_satoshi"] == int(to_satoshi(0.5))


def test_normalize_tx_from_dict():
    t = normalize_tx_event({
        "hash": "tx1",
        "from_addr": "0xfrom",
        "to_addr": "0xto",
        "value": 1.5,
        "block_height": 10,
    })
    assert t["hash"] == "tx1"
    assert t["from"] == "0xfrom"
    assert t["block"] == 10
    assert t["value_satoshi"] == int(to_satoshi(1.5))


def test_normalize_prefers_satoshi_twins():
    b = normalize_block_event({
        "height": 1,
        "hash": "h",
        "burned": 99.0,
        "burned_satoshi": 1_000_000,
    })
    assert b["burned"] == 1.0
    assert b["burned_satoshi"] == 1_000_000

    t = normalize_tx_event({
        "hash": "tx",
        "value": 99.0,
        "amount_satoshi": 2_500_000,
    })
    assert t["value"] == 2.5
    assert t["value_satoshi"] == 2_500_000
