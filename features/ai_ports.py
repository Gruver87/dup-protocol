"""Optional AI model port — fail-closed when unbound (ADR 0016 sprout).

Not consensus-wired. Not mainnet. Bind a real model only in lab / ops profiles.
"""

from __future__ import annotations

from typing import Any, Mapping, Optional, Protocol, Sequence, runtime_checkable


@runtime_checkable
class ModelPort(Protocol):
    """Predictive model bound behind a port (never invent confidence)."""

    def predict(
        self,
        features: Sequence[float],
        *,
        context: Optional[Mapping[str, Any]] = None,
    ) -> Mapping[str, Any]:
        """Return at least ``prediction`` (numeric). Optional ``confidence`` only if real."""


class UnboundModel:
    """Explicit unbound sentinel — calling predict refuses."""

    def predict(
        self,
        features: Sequence[float],
        *,
        context: Optional[Mapping[str, Any]] = None,
    ) -> Mapping[str, Any]:
        raise RuntimeError("model_unbound: no ModelPort configured")


def is_bound_model(model: Optional[Any]) -> bool:
    return model is not None and not isinstance(model, UnboundModel)
