import pytest
from divergence.backtest.simulate import simulate


def test_position_earns_next_day_return():
    # position[0]=1 applies to return[1]; no cost if no change from implicit prior 0... see cost test
    rets = simulate(positions=[1.0, 1.0], asset_returns=[0.0, 0.05], cost_bps=0.0)
    assert rets[1] == pytest.approx(0.05)


def test_no_lookahead_first_day_has_no_prior_return():
    rets = simulate(positions=[1.0], asset_returns=[0.99], cost_bps=0.0)
    # only one day: position can't earn a t->t+1 return -> strategy return 0 that day
    assert rets[0] == 0.0


def test_cost_charged_on_position_change():
    # enter (0->1) then exit (1->0); flat returns; cost 100bps each turn
    rets = simulate(positions=[1.0, 0.0], asset_returns=[0.0, 0.0], cost_bps=100.0)
    assert rets[0] == pytest.approx(-0.01)   # 0->1 turnover 1.0 * 100bps
    assert rets[1] == pytest.approx(-0.01)   # 1->0 turnover 1.0 * 100bps


def test_length_mismatch_raises():
    with pytest.raises(ValueError):
        simulate(positions=[1.0, 1.0], asset_returns=[0.0], cost_bps=0.0)
