#!/usr/bin/env python3
"""Unit tests for Long-Range lab WS seed helper (no Docker)."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _load():
    path = ROOT / "scripts" / "seed_long_range_lab_ws.py"
    spec = importlib.util.spec_from_file_location("seed_long_range_lab_ws", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_seed_writes_valid_checkpoint(tmp_path):
    mod = _load()
    persist = tmp_path / "ws_checkpoint.json"
    path = mod.seed(persist=persist, height=0, block_hash="ab" * 32)
    assert path.is_file()
    raw = json.loads(path.read_text(encoding="utf-8"))
    assert raw["items"]
    assert int(raw["items"][0]["height"]) == 0
    assert raw["items"][0]["block_hash"] == "ab" * 32
    assert raw["items"][0].get("digest")


def _assert_lab_node(name: str, *, node_id: str, peers: list[str], mining: bool) -> None:
    node = json.loads((ROOT / name).read_text(encoding="utf-8"))
    assert node["node_id"] == node_id
    assert node["feature_long_range"] is True
    assert node["feature_libp2p"] is False
    assert node["bridge_enabled"] is False
    assert node["tip_safety_enforce"] is True
    assert node["tip_safety_shadow"] is True
    assert node["deployment_mode"] == "dev"
    assert int(node["chain_id"]) == 77779
    assert node["mining_enabled"] is mining
    assert node["bootstrap_peers"] == peers


def test_lab_node_json_arms_tip_safety():
    _assert_lab_node(
        "node.long_range.lab.json",
        node_id="lr-lab-0",
        peers=["lr1:5000", "lr2:5000"],
        mining=True,
    )
    _assert_lab_node(
        "node.long_range.lab1.json",
        node_id="lr-lab-1",
        peers=["lr0:5000", "lr2:5000"],
        mining=False,
    )
    _assert_lab_node(
        "node.long_range.lab2.json",
        node_id="lr-lab-2",
        peers=["lr0:5000", "lr1:5000"],
        mining=False,
    )


def test_lr_compose_bind_and_tip_safety():
    text = (ROOT / "docker-compose.long_range.lab.yml").read_text(encoding="utf-8")
    assert "TIP_SAFETY_ENFORCE" in text
    assert "./data/long_range_lab0" in text
    assert "29080" in text
    assert "29081" in text
    assert "29082" in text
    assert '"18180:' not in text
    assert "lr1:" in text
    assert "ABS_WS_COMMITTEE" in text
    assert "ABS_WS_COMMITTEE_SECRETS_FILE" in text
    assert "ABS_WS_ROLL_GAP" in text
    assert "TIP_ANCESTRY_WINDOW_MAX" in text
    assert (ROOT / "consensus" / "long_range" / "roll_forward.py").is_file()


def test_host_verifier_does_not_start_soak():
    src = (ROOT / "scripts" / "verify_long_range_host.py").read_text(encoding="utf-8")
    assert "long_range_lab.py" in src
    assert "long_range_p2p_lab.py" in src
    assert "long_range_gossip_lab.py" in src
    assert "start_soak" not in src
    assert "docker" not in src.lower() or "no docker" in src.lower()
    assert (ROOT / "scripts" / "gen_long_range_lab_committee.py").is_file()
