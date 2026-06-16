"""Offline tests for the zero-config fallback. SyntheticProvider depends only on
`types`; resolve_provider's cache branch is exercised with a temp cache_dir so no
real `data/` frame is touched."""
from datetime import date

from divergence.adapters.synthetic import SyntheticProvider, resolve_provider
from divergence.adapters.historical import HistoricalAdapter
from divergence.skill.runtime import run_skill


def test_synthetic_window_drops_capital_axis_and_spikes_fear():
    w = SyntheticProvider().trailing_window("BTC", None, 90)
    assert len(w) == 90
    assert all(s.whale_retail_flow is None for s in w)   # capital axis absent -> degraded
    assert all(s.token == "BTC" for s in w)
    assert w[-1].fear_greed < w[0].fear_greed             # extreme-fear spike on the last day


def test_synthetic_provider_yields_degraded_directional_signal():
    # The whole point of the fallback: a non-crashing, non-flat, honestly-degraded demo.
    out = run_skill("BTC", SyntheticProvider())          # no theta_abs -> DEFAULT_THETA
    d = out["detail"]
    assert d["degraded"] is True
    assert d["capital_score"] is None                    # no whale z-score
    assert d["direction"] == "long"                      # crowd in extreme fear -> contrarian long
    assert 0.0 < d["confidence"] <= 0.6                  # degraded confidence is capped


def test_resolve_provider_falls_back_to_synthetic_without_cache(tmp_path):
    from divergence.adapters.cmc_client import CMCClient
    client = CMCClient(cache_dir=tmp_path)               # empty dir -> no cached frame
    provider, note = resolve_provider("BTC", client=client)
    assert isinstance(provider, SyntheticProvider)
    assert note and "synthetic" in note.lower()


def test_resolve_provider_prefers_cache_when_present(tmp_path):
    import pandas as pd
    from divergence.adapters.cmc_client import CMCClient
    client = CMCClient(cache_dir=tmp_path)
    client.cache_put("BTC_frame", pd.DataFrame({"day": [date(2025, 1, 1)], "price": [100.0]}))
    provider, note = resolve_provider("BTC", client=client)
    assert isinstance(provider, HistoricalAdapter)
    assert note is None
