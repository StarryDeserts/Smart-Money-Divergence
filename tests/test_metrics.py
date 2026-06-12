import pytest
from divergence.backtest.metrics import sharpe, max_drawdown, hit_rate, turnover, equity_curve


def test_sharpe_zero_for_no_variance():
    assert sharpe([0.0, 0.0, 0.0]) == 0.0


def test_sharpe_positive_for_steady_gains():
    assert sharpe([0.01, 0.012, 0.009, 0.011], periods_per_year=252) > 0


def test_max_drawdown_is_worst_peak_to_trough():
    eq = [1.0, 1.2, 0.9, 1.1]   # peak 1.2 -> trough 0.9 = -0.25
    assert max_drawdown(eq) == pytest.approx(-0.25)


def test_hit_rate_fraction_positive_among_nonzero():
    assert hit_rate([0.01, -0.02, 0.0, 0.03]) == pytest.approx(2 / 3)


def test_turnover_sums_position_changes():
    assert turnover([0.0, 1.0, 1.0, 0.0]) == pytest.approx(2.0)


def test_equity_curve_compounds():
    eq = equity_curve([0.0, 0.1, -0.5])
    assert eq[-1] == pytest.approx(1.0 * 1.1 * 0.5)
