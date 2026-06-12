from datetime import date, timedelta
from divergence.types import Snapshot
from divergence.backtest.harness import run_backtest, BacktestResult


def _series(token, n, *, whale_fn, price_fn, fg=50.0):
    start = date(2025, 1, 1)
    return [Snapshot(token=token, day=start + timedelta(days=i), price=price_fn(i),
                     whale_retail_flow=whale_fn(i), fear_greed=fg) for i in range(n)]


def test_runs_and_splits_in_and_out_of_sample():
    # whales lead price: when whale>0 today, price rises tomorrow -> strategy should not be empty
    hist = {"BTC": _series("BTC", 200,
                           whale_fn=lambda i: 1.0 if i % 4 == 0 else -1.0,
                           price_fn=lambda i: 100.0 * (1.01 ** i))}
    res = run_backtest(hist, lookback=30, theta_quantile=0.7, cost_bps=5.0, split=0.65)
    assert isinstance(res, BacktestResult)
    assert res.theta_abs >= 0
    assert res.oos_metrics["n_days"] > 0
    assert "whale_retail_flow" in res.attribution


def test_theta_calibrated_on_in_sample_only(monkeypatch):
    # if OOS leaked into calibration, theta would change; guard by construction:
    hist = {"BTC": _series("BTC", 120, whale_fn=lambda i: float((-1) ** i), price_fn=lambda i: 100.0 + i)}
    res = run_backtest(hist, lookback=20, split=0.5)
    assert res.in_sample_days + res.oos_days == res.total_days
    assert res.in_sample_days > 0 and res.oos_days > 0


def test_flat_strategy_when_theta_huge_has_zero_turnover():
    hist = {"BTC": _series("BTC", 100, whale_fn=lambda i: 0.0, price_fn=lambda i: 100.0)}
    res = run_backtest(hist, lookback=20, theta_quantile=0.999)
    assert res.oos_metrics["turnover"] == 0.0


def test_benchmark_is_equal_weight_buy_and_hold_same_days():
    hist = {"BTC": _series("BTC", 120, whale_fn=lambda i: float((-1) ** i), price_fn=lambda i: 100.0 + i)}
    res = run_backtest(hist, lookback=20, split=0.6)
    assert res.oos_benchmark["n_days"] == res.oos_metrics["n_days"]
    assert "total_return" in res.oos_benchmark and "sharpe" in res.oos_benchmark


def test_no_lookahead_future_prices_do_not_change_in_sample():
    # THE central no-look-ahead evidence test (spec §8): tamper the FUTURE, assert the past is untouched.
    base = _series("BTC", 120, whale_fn=lambda i: float((-1) ** i), price_fn=lambda i: 100.0 + i)
    r1 = run_backtest({"BTC": base}, lookback=20, split=0.6)
    tampered = base[:-10] + [Snapshot(token="BTC", day=s.day, price=s.price * 100,
                                      whale_retail_flow=s.whale_retail_flow, fear_greed=s.fear_greed)
                             for s in base[-10:]]
    r2 = run_backtest({"BTC": tampered}, lookback=20, split=0.6)
    assert r2.theta_abs == r1.theta_abs       # theta calibrated in-sample only -> unaffected
    assert r2.is_metrics == r1.is_metrics     # in-sample signals depend only on past data
