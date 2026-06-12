from __future__ import annotations
import math
from datetime import date
from typing import Protocol, runtime_checkable
from ..types import Snapshot


@runtime_checkable
class SnapshotProvider(Protocol):
    def trailing_window(self, token: str, end: date | None, lookback: int) -> list[Snapshot]: ...


def assert_schema(s: Snapshot) -> None:
    """Boundary validation — both adapters MUST emit snapshots that pass this.
    This is what guarantees backtest == live at the data seam."""
    if not s.token:
        raise ValueError("snapshot.token must be non-empty")
    if s.price is None or math.isnan(s.price) or s.price <= 0:
        raise ValueError(f"snapshot.price must be positive, got {s.price}")
    for name in ("whale_retail_flow", "funding_rate", "open_interest", "social_heat", "fear_greed"):
        v = getattr(s, name)
        if v is not None and math.isnan(float(v)):
            raise ValueError(f"snapshot.{name} is NaN; use None for absent")
