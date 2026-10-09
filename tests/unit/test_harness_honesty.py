#!/usr/bin/env python3
"""Unit tests for shared harness soft-PASS honesty."""

from runtime.harness_honesty import harness_smoke_ok


def test_healthy_is_ok():
    assert harness_smoke_ok({"harness_healthy": True})


def test_solo_p2p_na_soft_pass():
    assert harness_smoke_ok(
        {
            "harness_healthy": False,
            "failed_checks": ["p2p_state_consistent"],
            "peers": [],
            "live_state_root": "abc",
        }
    )


def test_peered_soft_requires_peer_match():
    assert not harness_smoke_ok(
        {
            "harness_healthy": False,
            "failed_checks": ["p2p_state_consistent"],
            "peers": [{"match": False}],
            "live_state_root": "abc",
        }
    )
    assert harness_smoke_ok(
        {
            "harness_healthy": False,
            "failed_checks": ["p2p_state_consistent"],
            "peers": [{"match": True}, {"match": True}],
            "live_state_root": "abc",
        }
    )


def test_hard_fail_not_soft():
    assert not harness_smoke_ok(
        {
            "harness_healthy": False,
            "failed_checks": ["p2p_state_consistent", "supply_within_cap"],
            "peers": [{"match": True}],
            "live_state_root": "abc",
        }
    )


def test_peer_probe_timeout_tip_aligned():
    assert harness_smoke_ok(
        {
            "harness_healthy": False,
            "failed_checks": ["peer_probe_ok"],
            "tip_state_aligned": True,
            "peer_probe_error": "timeout",
            "peers": [],
            "live_state_root": "abc",
        }
    )
