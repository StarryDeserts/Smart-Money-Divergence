import numpy as np
from divergence.signal_core import _causal_z, _momentum_series


def test_causal_z_positive_when_last_value_spikes_up():
    series = [0.0] * 89 + [10.0]
    assert _causal_z(series) > 3.0


def test_causal_z_none_when_too_few_values():
    assert _causal_z([1.0]) is None
    assert _causal_z([None, None]) is None


def test_causal_z_zero_when_flat():
    assert _causal_z([5.0] * 10) == 0.0


def test_causal_z_ignores_none_gaps():
    assert _causal_z([None, 0.0, 0.0, 0.0, 4.0]) > 0.0


def test_momentum_series_is_k_day_returns():
    prices = [100.0, 100.0, 100.0, 110.0]  # k=2 -> returns at i>=2
    out = _momentum_series(prices, k=2)
    assert out[-1] == 0.10  # (110-100)/100 over last 2 days
