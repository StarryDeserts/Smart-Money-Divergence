from datetime import date
import pandas as pd
from divergence.adapters.cmc_client import CMCClient
from divergence.adapters.historical import HistoricalAdapter
from divergence.adapters.base import assert_schema


def _seed(client, token):
    days = pd.date_range("2025-01-01", periods=5, freq="D").date
    client.cache_put(f"{token}_frame", pd.DataFrame({
        "day": days, "price": [10, 11, 12, 13, 14],
        "whale_retail_flow": [1, -1, 2, -2, 3], "funding_rate": [0.01]*5,
        "open_interest": [100]*5, "social_heat": [5]*5, "fear_greed": [40, 50, 60, 70, 80],
    }))


def test_history_returns_schema_valid_ordered_snapshots(tmp_path):
    c = CMCClient(api_key="K", cache_dir=tmp_path); _seed(c, "BTC")
    a = HistoricalAdapter(c)
    hist = a.history("BTC")
    assert [s.day for s in hist] == sorted(s.day for s in hist)
    for s in hist:
        assert_schema(s)
    assert hist[0].fear_greed == 40


def test_trailing_window_is_causal_slice(tmp_path):
    c = CMCClient(api_key="K", cache_dir=tmp_path); _seed(c, "BTC")
    a = HistoricalAdapter(c)
    win = a.trailing_window("BTC", end=date(2025, 1, 3), lookback=90)
    assert win[-1].day == date(2025, 1, 3)
    assert all(s.day <= date(2025, 1, 3) for s in win)  # no future rows


def test_missing_optional_column_becomes_none(tmp_path):
    c = CMCClient(api_key="K", cache_dir=tmp_path)
    days = pd.date_range("2025-01-01", periods=3, freq="D").date
    c.cache_put("ETH_frame", pd.DataFrame({"day": days, "price": [1, 2, 3], "fear_greed": [40, 50, 60]}))
    a = HistoricalAdapter(c)
    hist = a.history("ETH")
    assert all(s.whale_retail_flow is None for s in hist)  # column absent -> None
