from datetime import date

import pytest

from divergence.adapters import cmc_mcp
from divergence.adapters.base import assert_schema
from divergence.adapters.cmc_mcp import (
    _capital_structure,
    _to_float,
    make_mcp_fetch,
    resolve_id,
)
from divergence.adapters.live import LiveAdapter


@pytest.mark.parametrize(
    "raw, expected",
    [
        (65671.7, 65671.7),
        (23, 23.0),
        ("-0.00025221", -0.00025221),
        ("383.61 B", 383.61e9),
        ("2.24 T", 2.24e12),
        ("134.68 M", 134.68e6),
        ("5 K", 5_000.0),
        ("+1.95%", 0.0195),
        ("1,316,256", 1_316_256.0),
        (None, None),
        ("", None),
        ("n/a", None),
    ],
)
def test_to_float_parses_cmc_numeric_forms(raw, expected):
    got = _to_float(raw)
    if expected is None:
        assert got is None
    else:
        assert got == pytest.approx(expected)


def test_resolve_id_is_case_insensitive():
    assert resolve_id("btc") == 1
    assert resolve_id("ETH") == 1027


def test_resolve_id_unknown_raises():
    with pytest.raises(ValueError):
        resolve_id("NOPE")


def test_capital_structure_maps_recorded_metrics_payload():
    # shape recorded live from get_crypto_metrics(id=1)
    metrics = {
        "circulatingSupplyDistribution": {
            "whales": {"volume": 248597.58, "percentOfSupply": 1.25},
            "others": {"volume": 39351410.12, "percentOfSupply": 98.75},
        },
        "addressesByHoldingTime": {
            "traders": {"count": 2542722.0, "percentOfAddresses": 4.61},
            "cruisers": {"count": 10681905.0, "percentOfAddresses": 19.35},
            "holders": {"count": 41982983.0, "percentOfAddresses": 76.05},
        },
    }
    cs = _capital_structure(metrics)
    assert cs["whale_supply_pct"] == pytest.approx(1.25)
    assert cs["retail_supply_pct"] == pytest.approx(98.75)
    assert cs["traders_pct"] == pytest.approx(4.61)
    assert cs["holders_pct"] == pytest.approx(76.05)


def test_capital_structure_tolerates_missing_keys():
    cs = _capital_structure({})
    assert cs["whale_supply_pct"] is None
    assert cs["holders_pct"] is None


def test_make_mcp_fetch_row_feeds_schema_valid_snapshot(monkeypatch):
    # latest-only: one canned live tip -> one schema-valid Snapshot through LiveAdapter
    monkeypatch.setattr(cmc_mcp, "live_snapshot", lambda token, api_key=None: {
        "day": date(2026, 6, 15), "price": 65585.28,
        "whale_retail_flow": None, "funding_rate": -0.000292,
        "open_interest": 394460000000.0, "fear_greed": 23.0,
    })
    win = LiveAdapter(make_mcp_fetch("dummy")).trailing_window("BTC", end=None, lookback=30)
    assert len(win) == 1
    s = win[0]
    assert_schema(s)
    assert s.price == pytest.approx(65585.28)
    assert s.fear_greed == 23.0
    assert s.whale_retail_flow is None  # honest: structure, not directional flow
