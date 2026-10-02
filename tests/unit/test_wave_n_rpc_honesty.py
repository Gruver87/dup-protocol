"""Wave N / RPC honesty: PoS stake satoshi, empty finality, gasPrice null, balance wei."""

from __future__ import annotations

from types import SimpleNamespace

from runtime.amount import WEI_PER_SATOSHI, abs_to_wei, money_abs, to_satoshi


def test_consensus_engine_stake_satoshi():
    from consensus_engine import ConsensusEngine

    engine = ConsensusEngine()
    assert engine.add_validator("0x01", 100.0) is True
    assert engine.validators["0x01"].stake == int(to_satoshi(100.0))
    assert isinstance(engine.validators["0x01"].stake, int)
    assert engine.get_total_stake() == int(to_satoshi(100.0))


def test_finality_empty_set_does_not_invent_denom():
    from finality_engine import FinalityEngine

    fe = FinalityEngine()
    fe.set_active_validator_count(0)
    assert fe.active_validator_count == 0
    fe.create_checkpoint(0, "0xabc")
    assert fe.add_attestation("0xv", 0, "0xabc") is True
    assert fe.checkpoints[0].is_justified is False


def test_money_abs_and_abs_to_wei():
    import pytest

    assert money_abs(7.5) == 7.5
    assert abs_to_wei(1) == 10**18
    with pytest.raises(TypeError):
        money_abs(True)


def test_query_facade_get_balance_satoshi():
    from api.query_facade import QueryFacade

    sat = 3_500_000
    bc = SimpleNamespace(get_balance_satoshi=lambda _a: sat)
    q = QueryFacade(bc, SimpleNamespace())
    assert q.get_balance_satoshi("0xabc") == sat
    assert q.get_balance("0xabc") == 3.5


def test_encode_eth_call_return():
    from api.eth_format import encode_eth_call_return

    assert encode_eth_call_return(1) == "0x" + "1".zfill(64)
    assert encode_eth_call_return(b"\x01\x02") == "0x0102"
    assert encode_eth_call_return(None) == "0x"


def test_eth_gas_price_null_unless_advertise():
    from api.fake_rpc import FakeRpcClient

    client = FakeRpcClient()
    assert client.call("eth_gasPrice", []).get("result") is None
    client.config.advertise_config_gas_price = True
    assert client.call("eth_gasPrice", []).get("result") == hex(
        abs_to_wei(client.config.gas_price_wei)
    )


def test_eth_get_balance_uses_satoshi_wei():
    from api.fake_rpc import FakeRpcClient

    client = FakeRpcClient()
    client.query.balances["0xabc"] = 2.5
    out = client.call("eth_getBalance", ["0xabc", "latest"]).get("result")
    assert out == hex(int(to_satoshi(2.5)) * WEI_PER_SATOSHI)


def test_fee_history_no_stub_ratio():
    from api.eth_format import format_fee_history
    from api.fake_rpc import FakeQueryFacade

    q = FakeQueryFacade(tip=2)
    q.blocks[1] = {"height": 1, "hash": "0x1", "transactions": [], "gas_used": 1000, "gas_limit": 8000}
    q.blocks[2] = {"height": 2, "hash": "0x2", "transactions": [], "gas_used": 4000, "gas_limit": 8000}
    cfg = SimpleNamespace(evm_gas_limit=8_000_000)
    out = format_fee_history(query=q, cfg=cfg, block_count=2, newest_tag="latest")
    assert out["gasUsedRatio"] == [0.125, 0.5]
    assert out["baseFeePerGas"] == [None, None]
    assert out["reward"] == [None, None]


def test_format_tx_value_satoshi_no_invented_gas():
    from api.eth_format import format_tx, observed_value_hex

    tx = {"hash": "0xab", "value": 2.5, "from_addr": "0x1", "to_addr": "0x2", "nonce": 1}
    out = format_tx(tx)
    assert out["value"] == hex(int(to_satoshi(2.5)) * WEI_PER_SATOSHI)
    assert out["gas"] is None
    assert out["gasUsed"] is None
    assert observed_value_hex({"amount": 1}) == hex(int(to_satoshi(1)) * WEI_PER_SATOSHI)
    assert observed_value_hex({}) is None


def test_format_block_no_invented_eth_stubs():
    from api.eth_format import format_block

    blk = {
        "height": 7,
        "hash": "0x" + "ab" * 32,
        "parent_hash": "0x" + "cd" * 32,
        "transactions": [],
        "timestamp": 100,
        "gas_used": 0,
        "gas_limit": 8_000_000,
        "total_burned": 0.5,
    }
    out = format_block(blk)
    assert out["stateRoot"] is None
    assert out["transactionsRoot"] is None
    assert out["receiptsRoot"] is None
    assert out["nonce"] is None
    assert out["sha3Uncles"] is None
    assert out["logsBloom"] is None
    assert out["gasLimit"] == hex(8_000_000)
    assert out["gasUsed"] == hex(0)
    assert out["totalBurned"] == int(to_satoshi(0.5))
    # Invented Ethereum 30M / zero roots must not appear
    assert out["gasLimit"] != hex(30_000_000)


def test_multisig_amount_satoshi_and_execution_failed():
    from features.multisig import MultiSigWallet

    wallet = MultiSigWallet(["0x1", "0x2"], 2)
    created = wallet.create_transaction("0x3", 10)
    assert created["success"] is True
    assert created["amount_satoshi"] == int(to_satoshi(10))

    def boom(_tx):
        return {"success": False, "error": "debit refused"}

    wallet2 = MultiSigWallet(["0x1", "0x2"], 2, transaction_executor=boom)
    tx_id = wallet2.create_transaction("0x3", 1)["tx_id"]
    wallet2.confirm(tx_id, "0x1")
    second = wallet2.confirm(tx_id, "0x2")
    assert second["success"] is False
    assert second["error"] == "execution_failed"
    assert wallet2.get_transaction(tx_id)["status"] == "execution_failed"
