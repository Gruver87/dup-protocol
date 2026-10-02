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
