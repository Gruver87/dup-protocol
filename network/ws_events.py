# network/ws_events.py — normalize EventBus payloads for WebSocket broadcast

from typing import Any, Dict, Tuple


def _field(obj: Any, *keys, default=None):
    """Read field from dict or object."""
    if obj is None:
        return default
    if isinstance(obj, dict):
        for key in keys:
            if key in obj and obj[key] is not None:
                return obj[key]
        return default
    for key in keys:
        val = getattr(obj, key, None)
        if val is not None:
            return val
    return default


def _abs_and_satoshi(
    obj: Any,
    *,
    abs_keys: Tuple[str, ...],
    sat_keys: Tuple[str, ...],
) -> Tuple[float, int]:
    """Prefer integer satoshi twin; derive ABS float only for display."""
    from runtime.amount import from_satoshi_float, to_satoshi

    raw_sat = _field(obj, *sat_keys, default=None)
    if raw_sat is not None and str(raw_sat).strip() != "":
        sat = int(raw_sat)
        return float(from_satoshi_float(sat)), sat
    abs_v = float(_field(obj, *abs_keys, default=0) or 0)
    return abs_v, int(to_satoshi(abs_v))


def normalize_block_event(block: Any) -> Dict:
    txs = _field(block, "transactions", default=[]) or []
    tx_count = _field(block, "tx_count", default=None)
    if tx_count is None:
        tx_count = len(txs) if isinstance(txs, list) else 0
    burned, burned_sat = _abs_and_satoshi(
        block,
        abs_keys=("total_burned", "burned"),
        sat_keys=("burned_satoshi", "total_burned_satoshi"),
    )
    return {
        "height": int(_field(block, "height", "number", default=0) or 0),
        "hash": _field(block, "hash", "block_hash", default="") or "",
        "txs": int(tx_count),
        "timestamp": _field(block, "timestamp", default=0),
        "miner": _field(block, "miner", "proposer", default="") or "",
        "burned": burned,
        "burned_satoshi": burned_sat,
        "state_root": _field(block, "state_root", default="") or "",
    }


def normalize_tx_event(tx: Any) -> Dict:
    value, value_sat = _abs_and_satoshi(
        tx,
        abs_keys=("value", "amount"),
        sat_keys=("value_satoshi", "amount_satoshi"),
    )
    return {
        "hash": _field(tx, "hash", "tx_hash", default="") or "",
        "from": _field(tx, "from_addr", "from", default="") or "",
        "to": _field(tx, "to_addr", "to", default="") or "",
        "value": value,
        "value_satoshi": value_sat,
        "block": _field(tx, "block_height", "block", default="pending"),
        "nonce": _field(tx, "nonce", default=0),
    }
