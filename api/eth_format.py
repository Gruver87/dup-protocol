# api/eth_format.py — ADR 0011 WS-safe eth formatters (no RESTHandler)
"""Block/tx/receipt/log formatting shared by JSON-RPC and WebSocket."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from api.ports import BlockQuery, LogsQuery, QueryLimitError, QueryTimeoutError
from runtime.amount import WEI_PER_SATOSHI, to_satoshi

ZERO_ROOT = "0x" + ("0" * 64)
EMPTY_LOGS_BLOOM = "0x" + ("0" * 512)


def _normalize_eth_root(raw: Any) -> Optional[str]:
    """Valid 32-byte hex root, or None. Never the zero stub as Absolute empty merkle."""
    if raw is None:
        return None
    s = str(raw).strip()
    if not s:
        return None
    if not s.startswith(("0x", "0X")):
        s = "0x" + s
    hexpart = s[2:]
    if len(hexpart) != 64:
        return None
    try:
        int(hexpart, 16)
    except ValueError:
        return None
    out = "0x" + hexpart.lower()
    if out == ZERO_ROOT:
        return None
    return out


def _burned_satoshi(row: Optional[Dict[str, Any]], key: str = "burned") -> int:
    if not isinstance(row, dict):
        return 0
    raw = row.get(key)
    if raw is None and key == "total_burned":
        raw = row.get("totalBurned")
    try:
        return int(to_satoshi(raw or 0))
    except (TypeError, ValueError):
        return 0


def _observed_uint_hex(row: Optional[Dict], *keys: str) -> Optional[str]:
    if not isinstance(row, dict):
        return None
    for key in keys:
        if key not in row:
            continue
        raw = row.get(key)
        if raw is None or raw == "":
            continue
        try:
            n = int(raw, 16) if isinstance(raw, str) and raw.startswith(("0x", "0X")) else int(raw)
        except (TypeError, ValueError):
            return None
        if n < 0:
            return None
        return hex(n)
    return None


def observed_value_hex(row: Optional[Dict[str, Any]]) -> Optional[str]:
    """ABS value as wei hex. Missing is null; stored 0 is 0x0."""
    if not isinstance(row, dict):
        return None
    if "value" not in row and "amount" not in row:
        return None
    raw = row.get("value")
    if raw is None or raw == "":
        raw = row.get("amount")
    if raw is None or raw == "":
        return None
    try:
        wei = int(to_satoshi(raw or 0)) * WEI_PER_SATOSHI
    except (TypeError, ValueError):
        return None
    return hex(wei)


def format_block(blk: Optional[Dict], full_tx: bool = False, *, query=None, bc=None, gas_limit=None) -> Optional[Dict]:
    if not blk:
        return None
    if blk.get("_full_tx_truncated"):
        full_tx = False
    txs = blk.get("transactions", [])
    tx_list = txs if isinstance(txs, list) else []
    tx_hashes = [
        tx.get("hash", "") if isinstance(tx, dict) else str(tx)
        for tx in tx_list
    ]
    height = blk.get("height", blk.get("block_height", blk.get("number")))
    try:
        number = int(height) if height is not None and height != "" else None
    except (TypeError, ValueError):
        number = None
    # Stored roots only — never invent Ethereum zero merkle / ethash nonce / 30M gas.
    state_root = _normalize_eth_root(blk.get("state_root") or blk.get("stateRoot"))
    tx_root = _normalize_eth_root(
        blk.get("tx_root") or blk.get("transactionsRoot") or blk.get("transactions_root")
    )
    receipts_root = _normalize_eth_root(
        blk.get("receipts_root") or blk.get("receiptsRoot")
    )
    bloom_raw = blk.get("logs_bloom") or blk.get("logsBloom")
    if bloom_raw is not None and str(bloom_raw).strip():
        bloom_s = str(bloom_raw).strip()
        if not bloom_s.startswith("0x"):
            bloom_s = "0x" + bloom_s
        logs_bloom = bloom_s if bloom_s != EMPTY_LOGS_BLOOM else None
    else:
        logs_bloom = None
    limit = _observed_uint_hex(blk, "gas_limit", "gasLimit")
    if limit is None and gas_limit is not None:
        try:
            gl = int(gas_limit)
            limit = hex(gl) if gl > 0 else None
        except (TypeError, ValueError):
            limit = None
    used = _observed_uint_hex(blk, "gas_used", "gasUsed")
    if used is None and isinstance(txs, list) and not txs:
        used = hex(0)
    ts = _observed_uint_hex(blk, "timestamp")
    return {
        "number": hex(number) if number is not None else None,
        "hash": blk.get("hash", blk.get("block_hash")) or None,
        "parentHash": blk.get("parent_hash") or blk.get("parentHash") or None,
        "nonce": None,  # Absolute is not ethash — never paint 8-byte zero
        "sha3Uncles": None,  # no uncle trie on pin formatter; null > zero digest
        "logsBloom": logs_bloom,
        "transactionsRoot": tx_root,
        "stateRoot": state_root,
        "receiptsRoot": receipts_root,
        "miner": blk.get("miner") or blk.get("proposer") or None,
        "difficulty": "0x0",
        "totalDifficulty": "0x0",
        "extraData": "0x",
        "size": _observed_uint_hex(blk, "size"),
        "gasLimit": limit,
        "gasUsed": used,
        "timestamp": ts,
        "uncles": [],
        "transactions": txs if full_tx else tx_hashes,
        "totalBurned": _burned_satoshi(blk, "total_burned"),
        "txCount": blk.get("tx_count", len(tx_hashes)),
    }


def format_tx(tx: Optional[Dict]) -> Optional[Dict]:
    if not tx:
        return None
    return {
        "hash": tx.get("hash", tx.get("tx_hash", "")),
        "blockNumber": hex(tx.get("block_height", 0)) if tx.get("block_height") is not None else None,
        "from": tx.get("from_addr", tx.get("from", "")),
        "to": tx.get("to_addr", tx.get("to", "")),
        "value": observed_value_hex(tx),
        "gas": _observed_uint_hex(tx, "gas", "gas_limit"),
        "gasUsed": _observed_uint_hex(tx, "gas_used", "gasUsed"),
        "nonce": _observed_uint_hex(tx, "nonce") or hex(0),
        "input": tx.get("data", tx.get("tx_data", "0x")),
        "burned": _burned_satoshi(tx, "burned"),
    }


def resolve_block_tag_to_height(bc_or_query, tag) -> int:
    tip_fn = getattr(bc_or_query, "tip_height", None)
    get_height = getattr(bc_or_query, "get_height", None)
    if tag in (None, "", "earliest"):
        return 0
    if tag in ("latest", "pending"):
        if callable(tip_fn):
            return int(tip_fn())
        if callable(get_height):
            return int(get_height())
        return 0
    try:
        return int(tag, 16) if str(tag).startswith("0x") else int(tag)
    except (TypeError, ValueError):
        return 0


def normalize_log_data(data) -> str:
    raw = str(data or "")
    if not raw or raw == "0x":
        return "0x"
    return raw if raw.startswith("0x") else "0x" + raw


def tx_index_in_block(bc, block_height: int, tx_hash: str) -> int:
    if not bc or not tx_hash:
        return 0
    blk = None
    get_block = getattr(bc, "get_block", None)
    if callable(get_block):
        try:
            blk = bc.get_block(BlockQuery(height=int(block_height)))
        except TypeError:
            blk = bc.get_block(int(block_height))
        except Exception:
            blk = None
    if not blk:
        return 0
    txs = blk.get("transactions", [])
    if not isinstance(txs, list):
        return 0
    target = tx_hash.lower()
    for idx, entry in enumerate(txs):
        if isinstance(entry, dict):
            h = str(entry.get("hash", entry.get("tx_hash", ""))).lower()
        else:
            h = str(entry).lower()
        if h == target:
            return idx
    return 0


def format_eth_log(row: Dict, bc=None) -> Dict:
    block_height = int(row.get("block_height", 0))
    block_hash = ""
    if bc is not None:
        blk = None
        get_block = getattr(bc, "get_block", None)
        if callable(get_block):
            try:
                blk = bc.get_block(BlockQuery(height=block_height))
            except TypeError:
                try:
                    blk = bc.get_block(block_height)
                except Exception:
                    blk = None
            except Exception:
                blk = None
        if blk:
            block_hash = blk.get("hash", blk.get("block_hash", ""))
    tx_hash = row.get("tx_hash", "")
    topics = row.get("topics", [])
    if not isinstance(topics, list):
        topics = []
    return {
        "removed": False,
        "logIndex": hex(int(row.get("log_index", 0))),
        "transactionIndex": hex(tx_index_in_block(bc, block_height, tx_hash)),
        "transactionHash": tx_hash,
        "blockHash": block_hash,
        "blockNumber": hex(block_height),
        "address": row.get("contract_address", ""),
        "data": normalize_log_data(row.get("data", "")),
        "topics": topics,
    }


def format_receipt(tx: Optional[Dict], bc=None, query=None) -> Optional[Dict]:
    if not tx:
        return None
    from storage.database import Database

    tx_hash = tx.get("hash", tx.get("tx_hash", ""))
    logs: List[Dict] = []
    facade = query
    if facade is not None and hasattr(facade, "get_evm_logs_by_tx"):
        rows = facade.get_evm_logs_by_tx(tx_hash)
        logs = [format_eth_log(row, facade) for row in rows]
    elif bc is not None and getattr(bc, "query_facade", None) is not None:
        rows = bc.query_facade.get_evm_logs_by_tx(tx_hash)
        logs = [format_eth_log(row, bc.query_facade) for row in rows]
    status_i = Database._normalize_tx_status(tx.get("status"))
    return {
        "transactionHash": tx_hash,
        "blockNumber": hex(tx.get("block_height", 0)) if tx.get("block_height") is not None else None,
        "from": tx.get("from_addr", tx.get("from", "")),
        "to": tx.get("to_addr", tx.get("to", "")),
        "status": hex(status_i),
        "gasUsed": _observed_uint_hex(tx, "gas_used", "gasUsed"),
        "logs": logs,
        "burned": _burned_satoshi(tx, "burned"),
    }


def handle_eth_get_logs(filt: Dict, bc=None, query=None) -> List[Dict]:
    from api.ports import NullQueryFacade

    facade = query
    if facade is None and bc is not None:
        facade = getattr(bc, "query_facade", None)
    # Unattached Blockchain defaults to NullQueryFacade — fall through to db.
    if isinstance(facade, NullQueryFacade):
        facade = None

    height_src = facade or bc
    from_block = resolve_block_tag_to_height(height_src, filt.get("fromBlock", "0x0"))
    to_block = resolve_block_tag_to_height(height_src, filt.get("toBlock", "latest"))
    if to_block < from_block:
        return []

    address = filt.get("address")
    addresses: tuple = ()
    if address:
        addresses = tuple(address if isinstance(address, list) else [address])
    topics = filt.get("topics")
    topics_t = tuple(topics) if isinstance(topics, list) else ()

    if facade is not None and hasattr(facade, "query_logs"):
        q = LogsQuery(
            from_block=from_block,
            to_block=to_block,
            addresses=addresses,
            topics=topics_t,
            limit=int(filt.get("limit") or 1000),
        )
        try:
            rows = facade.query_logs(q)
        except (QueryLimitError, QueryTimeoutError):
            raise
        return [format_eth_log(row, facade) for row in rows]

    store = getattr(bc, "db", None) if bc is not None else None
    if store is None or not hasattr(store, "query_evm_logs"):
        return []
    rows = store.query_evm_logs(
        from_block=from_block,
        to_block=to_block,
        addresses=list(addresses) if addresses else None,
        topics=list(topics_t) if topics_t else None,
    )
    return [format_eth_log(row, bc) for row in rows]


def resolve_block_by_tag(bc, tag: str, query=None) -> Optional[Dict]:
    facade = query or (getattr(bc, "query_facade", None) if bc else None)
    if facade is not None:
        return facade.get_block(BlockQuery(tag=str(tag or "latest")))
    if not bc:
        return None
    if tag in ("latest", "pending"):
        return bc.get_last_block()
    try:
        height = int(tag, 16) if str(tag).startswith("0x") else int(tag)
        return bc.get_block(height)
    except (TypeError, ValueError):
        return None


def tx_at_block_index(bc, blk: Optional[Dict], index: int, query=None) -> Optional[Dict]:
    facade = query or (getattr(bc, "query_facade", None) if bc else None)
    if not blk or index < 0:
        return None
    txs = blk.get("transactions", [])
    if not isinstance(txs, list) or index >= len(txs):
        return None
    entry = txs[index]
    if isinstance(entry, dict):
        return entry
    tx_hash = str(entry)
    if facade is not None:
        return facade.get_transaction(tx_hash)
    if bc is not None and hasattr(bc, "get_transaction"):
        return bc.get_transaction(tx_hash)
    return None


def encode_eth_call_return(value: Any) -> str:
    """Encode eth_call return as 0x-hex (ABI word for ints; raw hex for bytes)."""
    if value is None:
        return "0x"
    if isinstance(value, (bytes, bytearray)):
        return "0x" + bytes(value).hex()
    if isinstance(value, str):
        s = value.strip()
        if not s:
            return "0x"
        if s.startswith("0x") or s.startswith("0X"):
            return "0x" + s[2:]
        return "0x" + s
    if isinstance(value, bool):
        return "0x" + ("1" if value else "0").zfill(64)
    if isinstance(value, int):
        if value < 0:
            raise ValueError("eth_call negative int unsupported")
        return "0x" + format(value, "x").zfill(64)
    return "0x"


DEFAULT_EVM_GAS_LIMIT = 8_000_000


def format_fee_history(
    *,
    query,
    cfg,
    block_count: Any = 1,
    newest_tag: Any = "latest",
) -> Dict[str, Any]:
    """Fee history from observed heights. No stubbed 0.5 ratios, no EIP-1559 market."""
    from api.ports import BlockQuery

    if isinstance(block_count, bool):
        n_req = 1
    elif isinstance(block_count, int):
        n_req = block_count
    else:
        raw = str(block_count or "1").strip() or "1"
        try:
            n_req = int(raw, 16) if raw.startswith(("0x", "0X")) else int(raw)
        except (TypeError, ValueError):
            n_req = 1
    n_req = max(1, min(int(n_req), 1024))
    get_block = getattr(query, "get_block", None)
    tip = None
    if callable(get_block):
        try:
            tip = get_block(BlockQuery(tag=str(newest_tag or "latest")))
        except Exception:
            tip = None
    tip_fn = getattr(query, "tip_height", None)
    if isinstance(tip, dict):
        try:
            tip_h = int(tip.get("height", tip_fn() if callable(tip_fn) else 0) or 0)
        except (TypeError, ValueError):
            tip_h = int(tip_fn()) if callable(tip_fn) else 0
    else:
        tip_h = int(tip_fn()) if callable(tip_fn) else 0
    oldest = max(0, tip_h - n_req + 1)
    protocol = getattr(cfg, "evm_gas_limit", None) if cfg is not None else None
    if protocol is None:
        protocol = DEFAULT_EVM_GAS_LIMIT
    try:
        protocol_i = int(protocol)
    except (TypeError, ValueError):
        protocol_i = DEFAULT_EVM_GAS_LIMIT
    ratios: List[float] = []
    bases: List[Optional[str]] = []
    rewards: List[Optional[List[str]]] = []
    for height in range(oldest, tip_h + 1):
        blk = None
        if callable(get_block):
            try:
                blk = get_block(BlockQuery(height=int(height)))
            except Exception:
                blk = None
        if not isinstance(blk, dict):
            continue
        used_raw = blk.get("gas_used", blk.get("gasUsed"))
        limit_raw = blk.get("gas_limit", blk.get("gasLimit"))
        try:
            used = int(used_raw) if used_raw is not None and used_raw != "" else None
        except (TypeError, ValueError):
            used = None
        try:
            limit = int(limit_raw) if limit_raw is not None and limit_raw != "" else None
        except (TypeError, ValueError):
            limit = None
        if limit is None or limit <= 0:
            limit = protocol_i if protocol_i > 0 else None
        if used is None or limit is None or limit <= 0:
            continue
        ratios.append(min(1.0, max(0.0, used / float(limit))))
        bases.append(None)
        rewards.append(None)
    return {
        "oldestBlock": hex(oldest),
        "baseFeePerGas": bases,
        "gasUsedRatio": ratios,
        "reward": rewards,
    }


# Compat aliases
_format_block = format_block
_format_tx = format_tx
_format_receipt = format_receipt
_handle_eth_get_logs = handle_eth_get_logs
_resolve_block_by_tag = resolve_block_by_tag
_format_eth_log = format_eth_log
