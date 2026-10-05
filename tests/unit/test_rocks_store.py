#!/usr/bin/env python3
"""RocksDB chain store tests (skipped when native RocksEngine is unavailable)."""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

try:
    import abs_native  # type: ignore

    HAS_ROCKS = hasattr(abs_native, "RocksEngine")
except Exception:
    HAS_ROCKS = False

pytestmark = pytest.mark.skipif(not HAS_ROCKS, reason="abs_native.RocksEngine not built")


@pytest.fixture
def rocks(tmp_path):
    from storage.rocks_store import RocksChainStore

    path = str(tmp_path / "chainstore")
    store = RocksChainStore(path, synchronous="FULL")
    store.initialize()
    yield store
    store.close()


def test_persist_block_atomic(rocks):
    from runtime.tokenomics import genesis_balances

    for addr, amount in genesis_balances("0x" + "1" * 40).items():
        rocks.set_balance(addr, float(amount))
    assert rocks.get_balance("0xecosystem000000000000000000000000000001") > 0
    assert rocks.get_balance("0xtreasury00000000000000000000000000001") > 0

    block = {
        "height": 1,
        "hash": "a" * 64,
        "parent_hash": "0" * 64,
        "timestamp": 1700000000,
        "miner": "0x" + "1" * 40,
        "tx_count": 1,
        "transactions": [],
    }
    txs = [
        {
            "hash": "b" * 64,
            "block_height": 1,
            "from_addr": "0x" + "2" * 40,
            "to_addr": "0x" + "3" * 40,
            "value": 1.0,
            "gas": 21000,
            "fee": 0.1,
            "burned": 0.5,
            "nonce": 0,
            "status": 1,
            "timestamp": 1700000001,
        }
    ]
    burn_addr = "0x" + "d" * 40
    assert rocks.persist_block_atomic(block, txs, burned_amount=0.5, burn_address=burn_addr)
    assert rocks.get_chain_tip() == 1
    assert rocks.get_block(1) is not None
    assert len(rocks.get_transactions_in_block(1)) == 1
    assert rocks.get_total_burned() == pytest.approx(0.5)
    assert rocks.get_balance(burn_addr) == pytest.approx(0.5)
    receipts = rocks.get_receipts_by_block(1)
    assert len(receipts) == 1
    audit = rocks.get_proposer_audit_log(limit=5, proposer="0x" + "1" * 40)
    assert len(audit) == 1
    by_addr = rocks.get_transactions_by_address("0x" + "2" * 40, direction="sent")
    assert len(by_addr) == 1


def test_get_last_block_returns_genesis_at_height_zero(rocks):
    block = {
        "height": 0,
        "hash": "c" * 64,
        "parent_hash": "0" * 64,
        "timestamp": 1700000000,
        "miner": "genesis",
        "state_root": "d" * 64,
        "transactions": [],
    }
    rocks.save_block(block)
    assert rocks.get_chain_tip() == 0
    last = rocks.get_last_block()
    assert last is not None
    assert last["height"] == 0
    assert last["hash"] == "c" * 64


def test_compute_state_root_uses_incremental_accumulator(rocks):
    from runtime.tokenomics import genesis_balances
    from storage import keycodec as kc
    from execution.state_root import compute_state_root_from_blobs

    founder = "0x" + "f" * 40
    for addr, amount in genesis_balances(founder).items():
        rocks.set_balance(addr, float(amount))
    root1 = rocks.compute_state_root()
    rocks.set_balance("0x" + "9" * 40, 1.0)
    root2 = rocks.compute_state_root()
    assert root1 != root2
    blobs = [value for _key, value in rocks._scan_prefix(kc.prefix_accounts())]
    assert root2 == compute_state_root_from_blobs(blobs)


def test_persist_block_atomic_keeps_accumulator_in_sync(rocks):
    from runtime.tokenomics import genesis_balances

    founder = "0x" + "e" * 40
    for addr, amount in genesis_balances(founder).items():
        rocks.set_balance(addr, float(amount))
    before = rocks.compute_state_root()

    block = {
        "height": 1,
        "hash": "f" * 64,
        "parent_hash": "0" * 64,
        "timestamp": 1700000001,
        "miner": founder,
        "state_root": before,
        "tx_count": 0,
        "transactions": [],
    }
    rocks.update_balance("0x" + "1" * 40, 5.0)
    block["state_root"] = rocks.compute_state_root()
    assert rocks.persist_block_atomic(block, [])
    assert rocks.get_live_state_root_meta() == (block["state_root"], 1)
    assert rocks.compute_state_root() == block["state_root"]


def test_state_root_mismatch_audit_on_rocks(rocks):
    rocks.record_state_root_mismatch(
        3,
        expected_root="a" * 64,
        computed_root="b" * 64,
        source="p2p",
        proposer="0x" + "1" * 40,
    )
    rows = rocks.get_state_root_mismatches(limit=5)
    assert len(rows) == 1
    assert rows[0]["height"] == 3
    assert rows[0]["expected_root"] == "a" * 64


def test_reorg_refreshes_live_state_root_meta(rocks):
    from runtime.tokenomics import genesis_balances

    founder = "0x" + "c" * 40
    for addr, amount in genesis_balances(founder).items():
        rocks.set_balance(addr, float(amount))
    roots = []
    for h in range(1, 4):
        root = rocks.compute_state_root()
        roots.append(root)
        rocks.persist_block_atomic(
            {
                "height": h,
                "hash": hex(h)[2:].zfill(64),
                "parent_hash": "0" * 64,
                "timestamp": 1700000000 + h,
                "miner": founder,
                "state_root": root,
                "transactions": [],
            },
            [],
        )
    assert rocks.get_live_state_root_meta() == (roots[-1], 3)
    with rocks.atomic():
        rocks.reorg_truncate_above(1)
    assert rocks.get_chain_tip() == 1
    assert rocks.get_block_by_hash(hex(3)[2:].zfill(64)) is None
    assert rocks.get_live_state_root_meta() == (roots[0], 1)


def test_reorg_truncate_and_reset(rocks):
    for h in range(1, 4):
        rocks.persist_block_atomic(
            {
                "height": h,
                "hash": hex(h)[2:].zfill(64),
                "parent_hash": "0" * 64,
                "timestamp": 1700000000 + h,
                "miner": "0x" + "1" * 40,
                "transactions": [],
            },
            [],
        )
    assert rocks.get_chain_tip() == 3
    with rocks.atomic():
        rocks.reorg_truncate_above(1)
        rocks.reset_accounts_from_alloc({"0x" + "a" * 40: 100.0}, _in_atomic=True)
    assert rocks.get_chain_tip() == 1
    assert rocks.get_block(2) is None
    assert rocks.get_balance("0x" + "a" * 40) == pytest.approx(100.0)


def test_hybrid_factory(tmp_path):
    from runtime.config import Config
    from storage.factory import open_database

    cfg = Config()
    cfg.db_engine = "rocksdb"
    cfg.db_path = str(tmp_path / "chainstore")
    cfg.sqlite_synchronous = "NORMAL"
    cfg.rocksdb_sync = "FULL"
    db = open_database(cfg)
    db.initialize()
    assert getattr(db, "engine", "") == "rocksdb_hybrid"
    db.save_block({"height": 0, "hash": "0" * 64, "miner": "genesis", "transactions": []})
    assert db.get_chain_tip() == 0
    db.close()


def test_address_tx_index_direction_and_pagination(rocks):
    for i, (fr, to) in enumerate(
        [
            ("0xaaa", "0xbbb"),
            ("0xbbb", "0xccc"),
            ("0xaaa", "0xccc"),
        ],
        start=1,
    ):
        rocks.persist_block_atomic(
            {
                "height": i,
                "hash": hex(i)[2:].zfill(64),
                "parent_hash": "0" * 64,
                "timestamp": 100 + i,
                "miner": "0x" + "1" * 40,
                "tx_count": 1,
                "transactions": [],
            },
            [
                {
                    "hash": hex(i + 100)[2:].zfill(64),
                    "block_height": i,
                    "from_addr": fr,
                    "to_addr": to,
                    "value": float(i),
                    "fee": 0.01,
                    "burned": 0.0,
                    "gas_used": 21000,
                    "status": 1,
                    "timestamp": 100 + i,
                }
            ],
        )

    sent = rocks.get_transactions_by_address("0xaaa", direction="sent")
    assert len(sent) == 2
    assert all(t["direction"] == "sent" for t in sent)

    recv = rocks.get_transactions_by_address("0xbbb", direction="received")
    assert len(recv) == 1
    assert recv[0]["direction"] == "received"

    page = rocks.get_transactions_by_address("0xaaa", limit=1, offset=1)
    assert len(page) == 1
    assert page[0]["block_height"] == 1

    act = rocks.get_address_activity("0xaaa")
    assert act["sent_count"] == 2
    assert act["received_count"] == 0
    assert act["tx_count"] == 2
    assert act["last_tx_height"] == 3


def test_reorg_removes_address_tx_indexes(rocks):
    rocks.persist_block_atomic(
        {
            "height": 1,
            "hash": "a" * 64,
            "parent_hash": "0" * 64,
            "timestamp": 1700000001,
            "miner": "0x" + "1" * 40,
            "transactions": [],
        },
        [
            {
                "hash": "b" * 64,
                "block_height": 1,
                "from_addr": "0x" + "2" * 40,
                "to_addr": "0x" + "3" * 40,
                "value": 1.0,
                "gas": 21000,
                "fee": 0.1,
                "burned": 0.0,
                "nonce": 0,
                "status": 1,
                "timestamp": 1700000002,
            }
        ],
    )
    sender = "0x" + "2" * 40
    assert rocks.count_transactions_by_address(sender, "sent") == 1
    with rocks.atomic():
        rocks.reorg_truncate_above(0)
    assert rocks.count_transactions_by_address(sender, "sent") == 0


def test_get_recent_transactions_uses_index(rocks):
    for i in range(1, 4):
        rocks.persist_block_atomic(
            {
                "height": i,
                "hash": f"{i:064x}",
                "parent_hash": f"{i - 1:064x}" if i > 1 else "0" * 64,
                "timestamp": 1700000000 + i,
                "miner": "0x" + "1" * 40,
                "transactions": [],
            },
            [
                {
                    "hash": f"0x{(i + 100):064x}",
                    "block_height": i,
                    "from_addr": "0x" + "a" * 40,
                    "to_addr": "0x" + "b" * 40,
                    "value": 1.0,
                    "gas": 21000,
                    "fee": 0.1,
                    "burned": 0.0,
                    "nonce": i - 1,
                    "status": 1,
                    "timestamp": 1700000100 + i,
                }
            ],
        )
    recent = rocks.get_recent_transactions(limit=2)
    assert len(recent) == 2
    assert recent[0]["block_height"] == 3
    assert recent[1]["block_height"] == 2


def test_reorg_removes_recent_tx_index(rocks):
    rocks.persist_block_atomic(
        {
            "height": 1,
            "hash": "a" * 64,
            "parent_hash": "0" * 64,
            "timestamp": 1700000001,
            "miner": "0x" + "1" * 40,
            "transactions": [],
        },
        [
            {
                "hash": "b" * 64,
                "block_height": 1,
                "from_addr": "0x" + "2" * 40,
                "to_addr": "0x" + "3" * 40,
                "value": 1.0,
                "gas": 21000,
                "fee": 0.1,
                "burned": 0.0,
                "nonce": 0,
                "status": 1,
                "timestamp": 1700000002,
            }
        ],
    )
    assert len(rocks.get_recent_transactions(limit=10)) == 1
    with rocks.atomic():
        rocks.reorg_truncate_above(0)
    assert rocks.get_recent_transactions(limit=10) == []


def test_bridge_lock_and_credit(rocks):
    rocks.save_bridge_lock("0xalice", "ethereum", "0xrecipient", 10.0, "0x" + "11" * 32)
    locks = rocks.get_bridge_locks()
    assert len(locks) == 1
    assert locks[0]["status"] == "pending"
    assert locks[0]["tx_hash"] == "0x" + "11" * 32
    rocks.confirm_bridge_lock("0x" + "11" * 32)
    assert rocks.get_bridge_locks()[0]["status"] == "confirmed"
    l1 = "0x" + "aa" * 32
    key = rocks.save_bridge_credit(l1, "0xrecipient", 10.0, "ethereum", log_index=0)
    assert rocks.has_bridge_credit(key)
    assert rocks.bridge_credit_key("ethereum", l1, 0) == key
    assert rocks.save_bridge_credit(l1, "0xrecipient", 10.0, "ethereum") == key
    # Same L1 event cannot be re-credited under a different claim amount/recipient.
    alt = rocks.bridge_credit_key("ethereum", l1, 0)
    assert alt == key
    claim = rocks.claim_and_credit_bridge_event(
        "ethereum", l1, "0xother", 99.0, log_index=0
    )
    assert claim["duplicate"] is True
    claim2 = rocks.claim_and_credit_bridge_event(
        "ethereum", l1, "0xother", 5.0, log_index=1
    )
    assert claim2["credited"] is True
    assert rocks.get_balance("0xother") == 5.0


def test_sqlite_to_rocks_migration(tmp_path):
    from storage.database import Database

    src_path = str(tmp_path / "legacy.db")
    dest_path = str(tmp_path / "chainstore")
    db = Database(src_path)
    db.initialize()
    block = {
        "height": 1,
        "hash": "c" * 64,
        "parent_hash": "0" * 64,
        "timestamp": 1700000000,
        "miner": "0x" + "4" * 40,
        "transactions": [],
    }
    txs = [
        {
            "hash": "d" * 64,
            "block_height": 1,
            "from_addr": "0x" + "5" * 40,
            "to_addr": "0x" + "6" * 40,
            "value": 2.0,
            "gas": 21000,
            "fee": 0.2,
            "burned": 0.1,
            "nonce": 0,
            "status": 1,
            "timestamp": 1700000002,
        }
    ]
    db.persist_block_atomic(block, txs, burned_amount=0.1, burn_address="0x" + "e" * 40)
    db.close()

    import subprocess

    proc = subprocess.run(
        [
            sys.executable,
            "scripts/migrate_sqlite_to_rocks.py",
            "--source",
            src_path,
            "--dest",
            dest_path,
            "--verify",
        ],
        cwd=os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0


def test_rocksdb_tuning_and_properties(tmp_path):
    from storage.rocks_store import RocksChainStore

    path = str(tmp_path / "tuned")
    store = RocksChainStore(
        path, synchronous="FULL", block_cache_mb=32, write_buffer_mb=16
    )
    store.initialize()
    stats = store.get_stats()
    assert stats["rocksdb_tuning"]["block_cache_mb"] == 32
    assert stats["rocksdb_tuning"]["write_buffer_mb"] == 16
    if hasattr(store._engine, "storage_properties"):
        props = dict(store._engine.storage_properties())
        assert isinstance(props, dict)
    store.close()


def test_rocksdb_column_families_roundtrip_and_legacy_dual_read(tmp_path):
    from storage import keycodec as kc
    from storage.rocks_store import RocksChainStore

    legacy = str(tmp_path / "legacy")
    store_v1 = RocksChainStore(legacy, synchronous="FULL", column_families=False)
    store_v1.initialize()
    store_v1.set_balance("0x" + "a" * 40, 42.0)
    store_v1._raw_put(kc.key_block_height(1), b'{"height":1,"hash":"ab"}')
    store_v1.close()

    # Enable CF on existing DB: dual-read must see legacy default keys.
    store_cf = RocksChainStore(legacy, synchronous="FULL", column_families=True)
    store_cf.initialize()
    assert store_cf.get_balance("0x" + "a" * 40) == 42.0
    assert store_cf._raw_get(kc.key_block_height(1)) == b'{"height":1,"hash":"ab"}'
    assert store_cf.column_families is True
    names = store_cf._engine.column_family_names()
    assert set(names) >= {"default", "blocks", "state", "index"}

    # New writes land in CFs and remain readable.
    store_cf.set_balance("0x" + "b" * 40, 7.5)
    assert store_cf.get_balance("0x" + "b" * 40) == 7.5
    assert store_cf.get_meta("schema_version") == "rocksdb-chain-v2-cf"
    stats = store_cf.get_stats()
    assert stats["rocksdb_tuning"].get("column_families") in (True, 1, "1")
    runtime = store_cf.get_rocks_runtime_stats()
    assert "total_transactions" not in runtime
    assert "total_accounts" not in runtime
    assert runtime.get("engine") == "rocksdb"
    assert runtime.get("rocksdb_tuning", {}).get("column_families") in (True, 1, "1")
    store_cf.close()


def _persist_blocks(rocks, count, miner_for):
    for h in range(1, count + 1):
        rocks.persist_block_atomic(
            {
                "height": h,
                "hash": f"{h:064x}",
                "parent_hash": f"{h - 1:064x}",
                "timestamp": 1700000000 + h,
                "miner": miner_for(h),
                "transactions": [],
            },
            [],
        )


def _spy_scan_prefix(rocks, monkeypatch):
    scans = []
    orig = rocks._scan_prefix

    def _spy(prefix, limit=100_000):
        scans.append(prefix)
        return orig(prefix, limit=limit)

    monkeypatch.setattr(rocks, "_scan_prefix", _spy)
    return scans


def test_get_total_burned_uses_latest_prefix_key(rocks, monkeypatch):
    from storage import keycodec as kc

    rocks.record_burn(1, 0.1)
    rocks.record_burn(2, 0.2)
    rocks.record_burn(10, 0.3)
    scans = _spy_scan_prefix(rocks, monkeypatch)
    assert rocks.get_total_burned() == pytest.approx(0.6)
    assert kc.P_BURN not in scans


def test_get_latest_blocks_does_not_prefix_scan_heights(rocks, monkeypatch):
    from storage import keycodec as kc

    _persist_blocks(rocks, 5, lambda _h: "0x" + "1" * 40)
    scans = _spy_scan_prefix(rocks, monkeypatch)
    latest = rocks.get_latest_blocks(limit=3)
    assert [int(b["height"]) for b in latest] == [5, 4, 3]
    assert kc.prefix_block_heights() not in scans


def test_get_address_activity_does_not_scan_proposer_audit(rocks, monkeypatch):
    from storage import keycodec as kc

    miner = "0x" + "aa" * 20
    _persist_blocks(rocks, 5, lambda _h: miner)
    scans = _spy_scan_prefix(rocks, monkeypatch)
    act = rocks.get_address_activity(miner)
    assert act["blocks_proposed"] == 5
    assert act["blocks_proposed_known"] is True
    assert kc.P_PROPOSER_AUDIT not in scans


def test_proposer_audit_log_seeks_by_height_not_prefix_scan(rocks, monkeypatch):
    from storage import keycodec as kc

    miner_a = "0x" + "aa" * 20
    miner_b = "0x" + "bb" * 20
    _persist_blocks(rocks, 7, lambda h: miner_a if h % 2 else miner_b)
    scans = _spy_scan_prefix(rocks, monkeypatch)
    page = rocks.get_proposer_audit_log(limit=3, offset=1)
    assert [r["height"] for r in page] == [6, 5, 4]
    assert kc.P_PROPOSER_AUDIT not in scans
    filtered = rocks.get_proposer_audit_log(limit=10, proposer=miner_a)
    assert all(r["proposer"] == miner_a for r in filtered)
    assert len(filtered) == 4
    assert rocks.count_proposer_audit() == 7
    assert rocks.count_proposer_audit(proposer=miner_a) == 4
    stats = rocks.get_proposer_stats(limit=5)
    assert stats[0]["proposer"] == miner_a
    assert stats[0]["blocks_proposed"] == 4
    detail = rocks.get_proposer_detail(miner_a, recent_limit=2)
    assert detail["blocks_proposed"] == 4
    assert detail["blocks_proposed_known"] is True
    assert len(detail["recent_blocks"]) == 2


def test_proposer_counts_follow_reorg(rocks):
    miner = "0x" + "aa" * 20
    _persist_blocks(rocks, 4, lambda _h: miner)
    assert rocks.count_proposer_audit(proposer=miner) == 4
    with rocks.atomic():
        rocks.reorg_truncate_above(2)
    assert rocks.count_proposer_audit(proposer=miner) == 2
    assert rocks.get_address_activity(miner)["blocks_proposed"] == 2


def test_address_tx_counts_are_meta_o1_and_follow_reorg(rocks, monkeypatch):
    from storage import keycodec as kc

    sender = "0x" + "2" * 40
    receiver = "0x" + "3" * 40
    for h in range(1, 4):
        rocks.persist_block_atomic(
            {
                "height": h,
                "hash": f"{h:064x}",
                "parent_hash": f"{h - 1:064x}",
                "timestamp": 1700000000 + h,
                "miner": "0x" + "1" * 40,
                "transactions": [],
            },
            [
                {
                    "hash": f"{h + 100:064x}",
                    "block_height": h,
                    "from_addr": sender,
                    "to_addr": receiver,
                    "value": 1.0,
                    "gas": 21000,
                    "fee": 0.1,
                    "burned": 0.0,
                    "nonce": h,
                    "status": 1,
                    "timestamp": 1700000000 + h,
                }
            ],
        )
    scans = _spy_scan_prefix(rocks, monkeypatch)
    assert rocks.count_transactions_by_address(sender, "sent") == 3
    assert rocks.count_address_transactions(receiver, "received") == 3
    assert rocks.count_transactions_by_address(sender, "all") == 3
    assert kc.prefix_tx_from(sender) not in scans
    assert kc.prefix_tx_to(receiver) not in scans
    monkeypatch.undo()
    with rocks.atomic():
        rocks.reorg_truncate_above(1)
    assert rocks.count_transactions_by_address(sender, "sent") == 1
    assert rocks.count_transactions_by_address(receiver, "received") == 1
    assert rocks.count_transactions_by_address(sender, "all") == 1


def test_address_tx_counts_survive_many_txs_in_one_batch(rocks):
    """RocksWriteBatch is invisible to _raw_get; counters must not lose increments."""
    sender = "0x" + "5" * 40
    receiver = "0x" + "6" * 40
    txs = [
        {
            "hash": f"{i + 500:064x}",
            "block_height": 1,
            "from_addr": sender,
            "to_addr": receiver,
            "value": 1.0,
            "gas": 21000,
            "fee": 0.1,
            "burned": 0.0,
            "nonce": i,
            "status": 1,
            "timestamp": 1700000002,
        }
        for i in range(4)
    ]
    rocks.persist_block_atomic(
        {
            "height": 1,
            "hash": "a" * 64,
            "parent_hash": "0" * 64,
            "timestamp": 1700000001,
            "miner": "0x" + "1" * 40,
            "transactions": [],
        },
        txs,
    )
    assert rocks.count_transactions_by_address(sender, "sent") == 4
    assert rocks.count_transactions_by_address(receiver, "received") == 4
    assert rocks.count_transactions_by_address(sender, "all") == 4
    assert rocks.count_transactions_by_address(receiver, "all") == 4


def test_self_send_touch_count_not_double_counted(rocks):
    addr = "0x" + "4" * 40
    rocks.persist_block_atomic(
        {
            "height": 1,
            "hash": "a" * 64,
            "parent_hash": "0" * 64,
            "timestamp": 1700000001,
            "miner": "0x" + "1" * 40,
            "transactions": [],
        },
        [
            {
                "hash": "c" * 64,
                "block_height": 1,
                "from_addr": addr,
                "to_addr": addr,
                "value": 1.0,
                "gas": 21000,
                "fee": 0.1,
                "burned": 0.0,
                "nonce": 0,
                "status": 1,
                "timestamp": 1700000002,
            }
        ],
    )
    assert rocks.count_transactions_by_address(addr, "sent") == 1
    assert rocks.count_transactions_by_address(addr, "received") == 1
    assert rocks.count_transactions_by_address(addr, "all") == 1


def test_rocks_runtime_stats_no_scan_and_matches_get_stats_tuning(rocks, monkeypatch):
    scans = _spy_scan_prefix(rocks, monkeypatch)
    runtime = rocks.get_rocks_runtime_stats()
    assert scans == []
    assert "total_transactions" not in runtime
    assert "total_accounts" not in runtime
    assert runtime["engine"] == rocks.engine
    full = rocks.get_stats()
    assert full["rocksdb_tuning"]["column_families"] == runtime["rocksdb_tuning"][
        "column_families"
    ]
    assert "total_transactions" in full and "height" in full


def _persist_tx_block(rocks, height: int, tx_hash: str, fr: str, to: str) -> None:
    rocks.persist_block_atomic(
        {
            "height": height,
            "hash": f"{height:064x}",
            "parent_hash": f"{height - 1:064x}" if height > 1 else "0" * 64,
            "timestamp": 1700000000 + height,
            "miner": "0x" + "1" * 40,
            "transactions": [],
        },
        [
            {
                "hash": tx_hash,
                "block_height": height,
                "from_addr": fr,
                "to_addr": to,
                "value": 1,
                "fee": 0.01,
                "burned": 0.0,
                "gas_used": 21000,
                "status": 1,
                "timestamp": 1700000000 + height,
            }
        ],
    )


def test_address_tx_page_does_not_prefix_scan(rocks, monkeypatch):
    sender = "0xaaa"
    for i in range(1, 6):
        _persist_tx_block(rocks, i, hex(i + 200)[2:].zfill(64), sender, "0xbbb")
    scans = _spy_scan_prefix(rocks, monkeypatch)
    page = rocks.get_transactions_by_address(sender, limit=2, offset=1, direction="sent")
    assert [t["block_height"] for t in page] == [4, 3]
    assert rocks.count_transactions_by_address(sender, "sent") == 5
    assert scans == []


def test_address_tx_all_direction_merges_from_and_to_newest_first(rocks, monkeypatch):
    # Interleaved heights across the from-index and to-index prefixes: the
    # merge must order by index body (height), not by the full key (prefix byte).
    me = "0xaaa"
    other = "0xbbb"
    layout = [(1, me, other), (2, other, me), (3, me, other), (4, other, me), (5, me, me)]
    for h, fr, to in layout:
        _persist_tx_block(rocks, h, hex(h + 300)[2:].zfill(64), fr, to)
    scans = _spy_scan_prefix(rocks, monkeypatch)
    full = rocks.get_transactions_by_address(me, limit=50, direction="all")
    assert [t["block_height"] for t in full] == [5, 4, 3, 2, 1]
    # Self-send appears once (dedup across from/to indexes).
    assert len({t["hash"] for t in full}) == 5
    page = rocks.get_transactions_by_address(me, limit=2, offset=2, direction="all")
    assert [t["block_height"] for t in page] == [3, 2]
    tail = rocks.get_transactions_by_address(me, limit=10, offset=4, direction="all")
    assert [t["block_height"] for t in tail] == [1]
    assert rocks.get_transactions_by_address(me, limit=5, offset=50) == []
    assert scans == []


def test_address_index_page_requires_native_prefix_prev(rocks, monkeypatch):
    from storage.types import StorageUnavailableError

    _persist_tx_block(rocks, 1, "e" * 64, "0xaaa", "0xbbb")

    class _NoPrev:
        def __init__(self, inner):
            self._inner = inner

        def __getattr__(self, name):
            if name == "prefix_prev":
                raise AttributeError(name)
            return getattr(self._inner, name)

    monkeypatch.setattr(rocks, "_engine", _NoPrev(rocks._engine))
    with pytest.raises(StorageUnavailableError):
        rocks.get_transactions_by_address("0xaaa", direction="sent")


def test_get_chain_metrics_uses_cached_counts_not_full_tx_scan(rocks, monkeypatch):
    from storage import keycodec as kc

    _persist_tx_block(rocks, 1, "b" * 64, "0xaaa", "0xbbb")
    first = rocks.get_chain_metrics(window=8)
    assert first["tx_count"] >= 1
    assert first["proposer_audit_count"] >= 1
    scans = _spy_scan_prefix(rocks, monkeypatch)
    second = rocks.get_chain_metrics(window=8)
    assert second["tx_count"] == first["tx_count"]
    assert second["receipt_count"] == first["receipt_count"]
    assert kc.P_TX not in scans
    assert kc.P_TX_RECEIPT not in scans
    assert kc.P_PROPOSER_AUDIT not in scans


def test_get_recent_transactions_does_not_unbounded_prefix_scan(rocks, monkeypatch):
    _persist_tx_block(rocks, 1, "b" * 64, "0x" + "2" * 40, "0x" + "3" * 40)
    scans = _spy_scan_prefix(rocks, monkeypatch)
    recent = rocks.get_recent_transactions(limit=1)
    assert len(recent) == 1
    assert scans == []


def test_get_bridge_locks_bounded_range_not_unbounded_prefix_scan(rocks, monkeypatch):
    from storage import keycodec as kc

    scans = _spy_scan_prefix(rocks, monkeypatch)
    rocks.get_bridge_locks(limit=5)
    assert kc.prefix_bridge_locks() not in scans
