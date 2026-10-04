#!/usr/bin/env python3
"""ZK proof verification invariants."""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from features.zk import ZKProof, ZKProofSystem


def test_knowledge_proof_verifies_against_public_value():
    zk = ZKProofSystem()
    secret = 12345
    public_value = pow(zk.PARAMS["g"], secret, zk.PARAMS["p"])
    proof = zk.prove_knowledge(secret)

    assert zk.verify_knowledge(proof, public_value) is True
    assert zk.verify_knowledge(proof, public_value + 1) is False


def test_knowledge_proof_rejects_tampered_challenge_and_response():
    zk = ZKProofSystem()
    secret = 12345
    public_value = pow(zk.PARAMS["g"], secret, zk.PARAMS["p"])
    proof = zk.prove_knowledge(secret)

    tampered_challenge = ZKProof(
        commitment=proof.commitment,
        response=proof.response,
        challenge=proof.challenge + 1,
        proof_type=proof.proof_type,
    )
    tampered_response = ZKProof(
        commitment=proof.commitment,
        response=proof.response + 1,
        challenge=proof.challenge,
        proof_type=proof.proof_type,
    )

    assert zk.verify_knowledge(tampered_challenge, public_value) is False
    assert zk.verify_knowledge(tampered_response, public_value) is False


def test_range_proof_refused_hash_theater_removed():
    zk = ZKProofSystem()
    with pytest.raises(NotImplementedError, match="zk_range_proof_not_implemented"):
        zk.prove_range(42, 0, 100)
    with pytest.raises(NotImplementedError, match="zk_range_proof_not_implemented"):
        zk.verify_range(
            ZKProof(commitment="x", response=1, challenge=1, proof_type="range"),
            0,
            100,
        )


def test_balance_proof_rejects_tampered_challenge():
    zk = ZKProofSystem()
    balance_proof = zk.prove_balance(1000, 250)
    assert zk.verify_balance(balance_proof, 250) is True

    bad_balance = ZKProof(
        commitment=balance_proof.commitment,
        response=balance_proof.response,
        challenge=balance_proof.challenge + 1,
        proof_type=balance_proof.proof_type,
    )
    assert zk.verify_balance(bad_balance, 250) is False


def test_zk_system_info_refuses_range_claim():
    info = ZKProofSystem().get_system_info()

    assert info["security_level"] == "r-and-d"
    assert "Fiat-Shamir" in info["knowledge_proof"]
    assert "range" not in info["supported_proofs"]
    assert "range" in info["refused_proofs"]
    assert "refused" in info["range_proof"]
