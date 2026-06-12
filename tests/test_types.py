from datetime import date
from divergence.types import Snapshot, Driver, Score, Signal


def test_snapshot_defaults_optional_fields_to_none():
    s = Snapshot(token="BTC", day=date(2025, 1, 1), price=42000.0)
    assert s.whale_retail_flow is None and s.fear_greed is None
    assert s.price == 42000.0


def test_types_are_frozen():
    s = Snapshot(token="BTC", day=date(2025, 1, 1), price=1.0)
    import dataclasses, pytest
    with pytest.raises(dataclasses.FrozenInstanceError):
        s.price = 2.0  # type: ignore[misc]


def test_signal_carries_direction_and_drivers():
    d = Driver(signal="whale_retail_flow", z=-1.8, side="capital", label="distributing")
    sig = Signal(token="BTC", day=date(2025, 1, 1), divergence=-2.0, direction="short",
                 confidence=0.7, capital_score=-1.8, crowd_score=0.2, drivers=[d], degraded=False)
    assert sig.direction == "short" and sig.drivers[0].side == "capital"
