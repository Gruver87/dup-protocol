# api/eth_format.py — ADR 0011 WS-safe eth formatters (no RESTHandler)
"""Block/tx/receipt/log formatting shared by JSON-RPC and WebSocket."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

from api.ports import BlockQuery, LogsQuery, QueryLimitError, QueryTimeoutError
from runtime.amount import WEI_PER_SATOSHI, to_satoshi

ZERO_ROOT = "0x" + ("0" * 64)
EMPTY_LOGS_BLOOM = "0x" + ("0" * 512)
DEFAULT_EVM_GAS_LIMIT = 8_000_000


def _keccak(data: bytes) -> bytes:
    try:
        from crypto import native

        return native.keccak256_digest(data)
    except Exception:
        import hashlib

        return hashlib.sha3_256(data).digest()


def _addr_bytes(addr: str) -> bytes:
    a = str(addr or "").strip().lower().replace("0x", "")
    if len(a) != 40:
        a = a.zfill(40)[-40:]
    return bytes.fromhex(a)


def _topic_bytes(topic: str) -> bytes:
    t = str(topic or "").strip().lower().replace("0x", "")
    if len(t) > 64:
        t = t[-64:]
    return bytes.fromhex(t.zfill(64))


def _as_eth_root(value: str) -> str:
    s = str(value or "").strip().lower()
    if s.startswith("0x"):
        s = s[2:]
    if len(s) != 64 or any(c not in "0123456789abcdef" for c in s):
        raise ValueError(f"invalid merkle root encoding: {value!r}")
    return "0x" + s


def _abs_tx_merkle_root(items: List[str]) -> str:
    """Absolute SHA256 merkle (same as Block.tx_root). Not Ethereum Hexary MPT."""
    from crypto.merkle import merkle_root

    cleaned = [str(x) for x in items if str(x)]
    raw = merkle_root(cleaned) if cleaned else merkle_root(["empty"])
    return _as_eth_root(raw)


def _tx_hash_from_block_item(tx: Any) -> str:
    if isinstance(tx, dict):
        return str(tx.get("hash") or tx.get("tx_hash") or "")
    return str(tx or "")


def block_transactions_root(blk: Dict[str, Any]) -> Optional[str]:
    """Stored tx_root, else Absolute merkle of tx hashes. Corrupt stored → None."""
    stored = blk.get("tx_root") or blk.get("transactions_root") or blk.get("transactionsRoot")
    if stored:
        try:
            return _as_eth_root(str(stored))
        except ValueError:
            return None
    txs = blk.get("transactions") or []
    hashes = []
    if isinstance(txs, list):
        for tx in txs:
            h = _tx_hash_from_block_item(tx)
            if h:
                hashes.append(h)
    return _abs_tx_merkle_root(hashes)


def block_receipts_root(blk: Dict[str, Any]) -> Optional[str]:
    """Stored receipts_root, else merkle of hash:status. Corrupt stored → None."""
    stored = blk.get("receipts_root") or blk.get("receiptsRoot")
    if stored:
        try:
            return _as_eth_root(str(stored))
        except ValueError:
            return None
    txs = blk.get("transactions") or []
    leaves: List[str] = []
    if isinstance(txs, list):
        for tx in txs:
            if isinstance(tx, dict):
                h = str(tx.get("hash") or tx.get("tx_hash") or "")
                if not h:
                    continue
                try:
                    status = int(tx.get("status") or 0)
                except (TypeError, ValueError):
                    status = 0
                leaves.append(f"{h}:{status}")
            else:
                s = str(tx or "")
                if s:
                    leaves.append(s)
    return _abs_tx_merkle_root(leaves)


def _bloom_add(bloom: bytearray, data: bytes) -> None:
    h = _keccak(data)
    for i in (0, 2, 4):
        bit_index = ((h[i] << 8) | h[i + 1]) & 2047
        byte_index = 255 - (bit_index // 8)
        bloom[byte_index] |= 1 << (bit_index % 8)


def logs_bloom(logs: Sequence[Dict[str, Any]]) -> str:
    """Ethereum logsBloom from address + topics (Yellow Paper)."""
    bloom = bytearray(256)
    for log in logs or ():
        if not isinstance(log, dict):
            continue
        addr = log.get("address") or log.get("contract_address") or ""
        if addr:
            _bloom_add(bloom, _addr_bytes(str(addr)))
        topics = log.get("topics") or []
        if isinstance(topics, (list, tuple)):
            for topic in topics:
                if topic is None or topic == "":
                    continue
                _bloom_add(bloom, _topic_bytes(str(topic)))
    return "0x" + bloom.hex()


def _normalize_eth_root(raw: Any) -> Optional[str]:
    """Valid 32-byte hex root, or None. Never the zero stub as Absolute empty merkle."""
    if raw is None:
        return None
    try:
        out = _as_eth_root(str(raw))
    except ValueError:
        return None
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
    n = observed_uint(row, *keys)
    if n is None:
        return None
    return hex(n)


def observed_uint(row: Optional[Dict[str, Any]], *keys: str) -> Optional[int]:
    """First present non-negative int. Missing is None — never invent 0/21000."""
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
        return n
    return None


def observed_uint_hex(row: Optional[Dict[str, Any]], *keys: str) -> Optional[str]:
    return _observed_uint_hex(row, *keys)


def observed_block_gas_limit(blk: Optional[Dict[str, Any]], *, protocol_limit=None) -> Optional[int]:
    """Stored header gas_limit, else protocol apply cap. Never Ethereum 30M."""
    n = observed_uint(blk, "gas_limit", "gasLimit")
    if n is not None and n > 0:
        return n
    if protocol_limit is None:
        return None
    try:
        p = int(protocol_limit)
    except (TypeError, ValueError):
        return None
    return p if p > 0 else None


def observed_tx_input(tx: Optional[Dict[str, Any]]) -> Optional[str]:
    """Calldata. Missing is null — empty stored calldata is 0x, not an invented transfer."""
    if not isinstance(tx, dict):
        return None
    if "data" not in tx and "tx_data" not in tx and "input" not in tx:
        return None
    raw = tx.get("data", tx.get("tx_data", tx.get("input")))
    if raw is None:
        return None
    s = str(raw).strip()
    if not s:
        return "0x"
    if s.startswith(("0x", "0X")):
        return s
    return "0x" + s


def block_extra_data(blk: Optional[Dict[str, Any]]) -> Optional[str]:
    """RPC extraData from the stored header. Missing is null, not a hardcoded empty hex."""
    if not isinstance(blk, dict):
        return None
    if "extra_data" not in blk and "extraData" not in blk:
        return None
    raw = blk.get("extra_data")
    if raw is None:
        raw = blk.get("extraData")
    if raw is None:
        return None
    if raw == "":
        return "0x"
    s = str(raw)
    if s.startswith(("0x", "0X")):
        hexpart = s[2:]
        if not hexpart:
            return "0x"
        if any(c not in "0123456789abcdefABCDEF" for c in hexpart):
            return "0x" + s.encode("utf-8").hex()
        return "0x" + hexpart.lower()
    return "0x" + s.encode("utf-8").hex()


def observed_tx_address(
    row: Optional[Dict[str, Any]],
    *keys: str,
    allow_zero: bool = False,
) -> Optional[str]:
    """Address from a tx/receipt row. Missing/empty is null, not ''."""
    if not isinstance(row, dict):
        return None
    for key in keys:
        if key not in row:
            continue
        raw = row.get(key)
        if raw is None or str(raw).strip() == "":
            continue
        s = str(raw).strip()
        hexpart = s[2:] if s.startswith(("0x", "0X")) else s
        if hexpart and all(c in "0123456789abcdefABCDEF" for c in hexpart):
            if not allow_zero and all(c == "0" for c in hexpart):
                return None
            return "0x" + hexpart.lower()
        return s
    return None


def observed_tx_hash(row: Optional[Dict[str, Any]]) -> Optional[str]:
    """Tx hash from the row. Missing/empty/all-zero is null, not ''."""
    if not isinstance(row, dict):
        return None
    raw = row.get("hash") or row.get("tx_hash") or row.get("transactionHash")
    if raw is None or str(raw).strip() == "":
        return None
    s = str(raw).strip()
    if not s.startswith(("0x", "0X")):
        s = "0x" + s
    hexpart = s[2:]
    if not hexpart or any(c not in "0123456789abcdefABCDEF" for c in hexpart):
        return None
    if all(c == "0" for c in hexpart):
        return None
    return s


def observed_receipt_status(row: Optional[Dict[str, Any]]) -> Optional[str]:
    """Receipt status 0x0/0x1 from a stored field. Missing is null, not reverted."""
    if not isinstance(row, dict) or "status" not in row:
        return None
    from storage.database import Database

    return hex(int(Database._normalize_tx_status(row.get("status"))))


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
    # Roots: stored Absolute merkle, else compute from txs. Corrupt stored → None.
    # Never invent Ethereum zero merkle / ethash nonce / 30M gas.
    state_root = _normalize_eth_root(blk.get("state_root") or blk.get("stateRoot"))
    tx_root = block_transactions_root(blk)
    receipts_root = block_receipts_root(blk)
    bloom_raw = blk.get("logs_bloom") or blk.get("logsBloom")
    if bloom_raw is not None and str(bloom_raw).strip():
        bloom_s = str(bloom_raw).strip().lower()
        if not bloom_s.startswith("0x"):
            bloom_s = "0x" + bloom_s
        hexpart = bloom_s[2:]
        if len(hexpart) == 512 and any(c != "0" for c in hexpart):
            bloom_out = "0x" + hexpart
        else:
            bloom_out = logs_bloom([])  # empty observed bloom
    else:
        bloom_out = logs_bloom([])
    limit_i = observed_block_gas_limit(blk, protocol_limit=gas_limit)
    limit = hex(limit_i) if limit_i is not None else None
    used = _observed_uint_hex(blk, "gas_used", "gasUsed")
    ts = _observed_uint_hex(blk, "timestamp")
    return {
        "number": hex(number) if number is not None else None,
        "hash": blk.get("hash", blk.get("block_hash")) or None,
        "parentHash": blk.get("parent_hash") or blk.get("parentHash") or None,
        "nonce": None,  # Absolute is not ethash — never paint 8-byte zero
        "sha3Uncles": None,  # no uncle trie on pin formatter; null > zero digest
        "logsBloom": bloom_out,
        "transactionsRoot": tx_root,
        "stateRoot": state_root,
        "receiptsRoot": receipts_root,
        "miner": blk.get("miner") or blk.get("proposer") or None,
        "difficulty": "0x0",
        "totalDifficulty": "0x0",
        "extraData": block_extra_data(blk),
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
        "hash": observed_tx_hash(tx),
        "blockNumber": hex(tx.get("block_height", 0)) if tx.get("block_height") is not None else None,
        "from": observed_tx_address(tx, "from_addr", "from"),
        "to": observed_tx_address(tx, "to_addr", "to", allow_zero=True),
        "value": observed_value_hex(tx),
        "gas": _observed_uint_hex(tx, "gas", "gas_limit"),
        "gasUsed": _observed_uint_hex(tx, "gas_used", "gasUsed"),
        "nonce": _observed_uint_hex(tx, "nonce"),
        "input": observed_tx_input(tx),
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

    tx_hash = observed_tx_hash(tx)
    logs: List[Dict] = []
    facade = query
    if facade is not None and hasattr(facade, "get_evm_logs_by_tx") and tx_hash:
        rows = facade.get_evm_logs_by_tx(tx_hash)
        logs = [format_eth_log(row, facade) for row in rows]
    elif bc is not None and getattr(bc, "query_facade", None) is not None and tx_hash:
        rows = bc.query_facade.get_evm_logs_by_tx(tx_hash)
        logs = [format_eth_log(row, bc.query_facade) for row in rows]
    status_hex = observed_receipt_status(tx)
    return {
        "transactionHash": observed_tx_hash(tx),
        "blockNumber": hex(tx.get("block_height", 0)) if tx.get("block_height") is not None else None,
        "from": observed_tx_address(tx, "from_addr", "from"),
        "to": observed_tx_address(tx, "to_addr", "to", allow_zero=True),
        "status": status_hex,
        "gasUsed": _observed_uint_hex(tx, "gas_used", "gasUsed"),
        "logs": logs,
        "logsBloom": logs_bloom(logs),
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
        used = observed_uint(blk, "gas_used", "gasUsed")
        limit = observed_block_gas_limit(blk, protocol_limit=protocol)
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
