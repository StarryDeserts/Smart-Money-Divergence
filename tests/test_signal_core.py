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


from conftest import make_window
from divergence.signal_core import score_window


def test_long_signal_when_whales_accumulate_into_crowd_fear():
    # whales spike up (accumulating) + fear&greed drops (fear) => capital>0, crowd<0 => D large +
    w = make_window(whale_last=10.0, fg_last=5.0)  # baseline whale=0, fg=50
    s = score_window(w)
    assert s.capital_score is not None and s.capital_score > 0
    assert s.crowd_score is not None and s.crowd_score < 0
    assert s.divergence > 0 and s.degraded is False


def test_short_signal_when_whales_distribute_into_crowd_greed():
    w = make_window(whale_last=-10.0, fg_last=95.0)
    s = score_window(w)
    assert s.divergence < 0 and s.degraded is False


def test_degraded_crowd_contrarian_when_hero_absent():
    # whale field entirely absent => capital unavailable => D = -crowd_score, degraded
    w = make_window(whale=None, fg_last=95.0)  # crowd greedy
    s = score_window(w)
    assert s.capital_score is None
    assert s.degraded is True
    assert s.divergence < 0  # -crowd_score, crowd greedy => negative => short bias


def test_crowd_score_renormalizes_over_available_inputs():
    # only fear_greed present on crowd side (social absent) -> crowd_score still computed
    w = make_window(whale=None, social=None, funding=None, oi=None, fg_last=95.0)
    s = score_window(w)
    assert s.crowd_score is not None


def test_flat_when_crowd_side_unavailable():
    # n=5 keeps the price series too short for momentum (needs >5 points), so with
    # fg/social/funding/oi all absent the crowd side genuinely evaporates to None.
    w = make_window(n=5, whale_last=10.0, fg=None, social=None, funding=None, oi=None)
    s = score_window(w)
    assert s.crowd_score is None
    assert s.divergence == 0.0


def test_drivers_tag_sides():
    w = make_window(whale_last=10.0, fg_last=95.0)
    s = score_window(w)
    sides = {d.signal: d.side for d in s.drivers}
    assert sides["whale_retail_flow"] == "capital"
    assert sides["fear_greed"] == "crowd"


from divergence.signal_core import calibrate_theta


def test_theta_is_quantile_of_abs_divergence():
    ds = [-1.0, 1.0, -2.0, 2.0, -3.0, 3.0, -4.0, 4.0, -5.0, 5.0]
    # |D| = 1..5 each twice; 80th percentile ~ 4.x
    theta = calibrate_theta(ds, quantile=0.8)
    assert 4.0 <= theta <= 5.0


def test_theta_zero_for_empty():
    assert calibrate_theta([], quantile=0.8) == 0.0


from datetime import date
from divergence.types import Score
from divergence.signal_core import decide


def _score(d, *, degraded=False):
    return Score(token="BTC", day=date(2025, 1, 1), divergence=d,
                 capital_score=None if degraded else 1.0,
                 crowd_score=-d if degraded else 0.0, drivers=[], degraded=degraded)


def test_long_when_d_exceeds_theta():
    sig = decide(_score(3.0), theta_abs=2.0)
    assert sig.direction == "long" and sig.confidence > 0


def test_flat_when_below_theta():
    sig = decide(_score(1.0), theta_abs=2.0)
    assert sig.direction == "flat" and sig.confidence == 0.0


def test_negative_d_is_flat_when_long_only():
    sig = decide(_score(-3.0), theta_abs=2.0, allow_short=False)
    assert sig.direction == "flat"


def test_negative_d_is_short_when_allowed():
    sig = decide(_score(-3.0), theta_abs=2.0, allow_short=True)
    assert sig.direction == "short"


def test_degraded_caps_confidence():
    full = decide(_score(4.0), theta_abs=2.0).confidence
    deg = decide(_score(4.0, degraded=True), theta_abs=2.0).confidence
    assert deg < full
