"""Exp mid-soak: no invent stake=100 / MEV gas=42000 / ZK demo value=42."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_main_proposer_source_no_invent_stake_100():
    text = (ROOT / "main.py").read_text(encoding="utf-8")
    assert 'v.get("stake", 100)' not in text
    assert "Refuse invent stake=100" in text
    assert 'v.get("stake_satoshi")' in text


def test_mev_frontrun_no_invent_gas_42000():
    from features.mev_analyzer import MEVAnalyzer, Transaction

    tx = Transaction(
        hash="0xabc",
        from_addr="0x1",
        to_addr="0x2",
        value=10.0,
        gas_price=2_000_000_000,
        timestamp=1,
    )
    out = MEVAnalyzer(db=None).simulate_frontrun(tx, bot_balance=100.0)
    assert out.get("gas_used") is None

    tx_with_gas = Transaction(
        hash="0xdef",
        from_addr="0x1",
        to_addr="0x2",
        value=10.0,
        gas_price=2_000_000_000,
        timestamp=1,
    )
    tx_with_gas.gas = 65000  # type: ignore[attr-defined]
    out2 = MEVAnalyzer(db=None).simulate_frontrun(tx_with_gas, bot_balance=100.0)
    assert out2.get("gas_used") == 65000


def test_mev_source_no_invent_21000_times_2():
    text = (ROOT / "features" / "mev_analyzer.py").read_text(encoding="utf-8")
    assert "21000 * 2" not in text
    assert "21000*2" not in text


def test_zk_range_get_source_no_invent_value_42():
    text = (ROOT / "api" / "http.py").read_text(encoding="utf-8")
    assert 'qs.get("value", ["42"])' not in text
    assert "do not invent demo 42" in text
