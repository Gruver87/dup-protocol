"""ADR 0018 libp2p dual-stack adapter unit tests."""

from __future__ import annotations

import pytest

from network.transport.errors import TransportCapabilityError
from network.transport.libp2p_adapter import Libp2pTransportAdapter
from network.transport.types import PeerEndpoint
from runtime.config import Config


def test_default_config_libp2p_off() -> None:
    cfg = Config()
    assert cfg.feature_libp2p is False
    assert cfg.feature_long_range is False


def test_adapter_disabled_refuses_dial() -> None:
    ad = Libp2pTransportAdapter(enabled=False)
    with pytest.raises(TransportCapabilityError):
        ad.connect(PeerEndpoint(host="127.0.0.1", port=4001))


def test_adapter_enabled_capability() -> None:
    ad = Libp2pTransportAdapter(enabled=True)
    st = ad.capability_status()
    assert st["available"] is True
    assert st["transport"] == "libp2p"
    if not ad.rust_backend:
        # CI builds abs_native without --features libp2p. No stub handle.
        with pytest.raises(TransportCapabilityError, match="--features libp2p"):
            ad.connect(PeerEndpoint(host="127.0.0.1", port=4001))
    else:
        # Real rust backend: dial without listener must fail closed.
        with pytest.raises(TransportCapabilityError):
            ad.connect(PeerEndpoint(host="127.0.0.1", port=39999))
        ad.close()


def test_prod_allows_libp2p_refuses_long_range(monkeypatch) -> None:
    """Pin policy: prod apply_env keeps libp2p and clamps Long-Range off (ADR 0017).

    A field left True without apply_env still fails validate(); that path is
    test_prod_validate_allows_libp2p_but_refuses_long_range.
    """
    monkeypatch.setenv("DEPLOYMENT_MODE", "prod")
    monkeypatch.setenv("FEATURE_LIBP2P", "true")
    monkeypatch.setenv("FEATURE_LONG_RANGE", "true")
    monkeypatch.delenv("P2P_TLS_ENABLED", raising=False)
    cfg = Config()
    cfg.deployment_mode = "prod"
    cfg.apply_env()
    assert cfg.feature_libp2p is True
    assert cfg.feature_long_range is False
    errs = cfg.validate()
    assert not any("feature_libp2p" in e.lower() for e in errs), errs
    assert not any("FEATURE_LONG_RANGE" in e for e in errs), errs


def test_libp2p_close_logs_failure(caplog) -> None:
    import logging

    ad = Libp2pTransportAdapter(enabled=True)

    class _Boom:
        def close(self):
            raise RuntimeError("close boom")

    ad._node = _Boom()
    with caplog.at_level(logging.DEBUG, logger="LibP2P"):
        ad.close()
    assert "node close failed" in caplog.text
    assert ad._node is None
