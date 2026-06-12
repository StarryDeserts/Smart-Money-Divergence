from datetime import date
import pytest
from divergence.types import Snapshot
from divergence.adapters.base import assert_schema, SnapshotProvider


def test_assert_schema_accepts_valid_snapshot():
    assert_schema(Snapshot(token="BTC", day=date(2025, 1, 1), price=1.0))


def test_assert_schema_rejects_bad_price():
    with pytest.raises(ValueError):
        assert_schema(Snapshot(token="BTC", day=date(2025, 1, 1), price=float("nan")))


def test_assert_schema_rejects_empty_token():
    with pytest.raises(ValueError):
        assert_schema(Snapshot(token="", day=date(2025, 1, 1), price=1.0))


def test_a_fake_provider_satisfies_the_protocol():
    class Fake:
        def trailing_window(self, token, end, lookback):
            return [Snapshot(token=token, day=date(2025, 1, 1), price=1.0)]
    f: SnapshotProvider = Fake()
    assert len(f.trailing_window("BTC", None, 90)) == 1
