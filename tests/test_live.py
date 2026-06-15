from datetime import date
import pytest
from divergence.types import Snapshot
from divergence.adapters.base import assert_schema, SnapshotProvider
from divergence.adapters.live import LiveAdapter


def _fake_rows():
    # source returns newest-first; adapter must sort ascending and coerce to Snapshot
    return [
        {"day": date(2025, 1, 2), "price": 11.0, "whale_retail_flow": 2.0, "fear_greed": 55.0},
        {"day": date(2025, 1, 1), "price": 10.0, "whale_retail_flow": 1.0, "fear_greed": 50.0},
    ]


def test_live_adapter_returns_sorted_schema_valid_snapshots():
    a = LiveAdapter(fetch=lambda token, lookback: _fake_rows())
    win = a.trailing_window("BTC", end=None, lookback=90)
    assert [s.day for s in win] == [date(2025, 1, 1), date(2025, 1, 2)]
    for s in win:
        assert_schema(s)
    assert win[-1].whale_retail_flow == 2.0


def test_live_adapter_satisfies_provider_protocol():
    a = LiveAdapter(fetch=lambda token, lookback: _fake_rows())
    p: SnapshotProvider = a
    assert isinstance(a, SnapshotProvider)


def test_missing_optional_keys_become_none():
    a = LiveAdapter(fetch=lambda token, lookback: [{"day": date(2025, 1, 1), "price": 10.0}])
    win = a.trailing_window("BTC", end=None, lookback=90)
    assert win[0].social_heat is None and win[0].whale_retail_flow is None
