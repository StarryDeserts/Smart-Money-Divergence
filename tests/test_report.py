from divergence.backtest.harness import BacktestResult
from divergence.backtest.report import render_report


def _result():
    return BacktestResult(theta_abs=1.5, total_days=200, in_sample_days=130, oos_days=70,
                          is_metrics={"sharpe": 1.2, "total_return": 0.3, "max_drawdown": -0.1,
                                      "hit_rate": 0.55, "turnover": 12.0, "n_days": 130},
                          oos_metrics={"sharpe": 0.8, "total_return": 0.15, "max_drawdown": -0.12,
                                       "hit_rate": 0.52, "turnover": 7.0, "n_days": 70},
                          is_benchmark={"sharpe": 0.6, "total_return": 0.2, "max_drawdown": -0.2,
                                        "hit_rate": 0.5, "turnover": 1.0, "n_days": 130},
                          oos_benchmark={"sharpe": 0.4, "total_return": 0.1, "max_drawdown": -0.25,
                                         "hit_rate": 0.5, "turnover": 1.0, "n_days": 70},
                          signals=[], attribution={"whale_retail_flow": 0.012, "fear_greed": 0.004})


def test_render_report_includes_oos_and_attribution():
    md = render_report(_result(), sensitivity=[{"theta_quantile": 0.8, "lookback": 90,
                       "cost_bps": 15.0, "oos_sharpe": 0.8, "oos_return": 0.15}])
    assert "Out-of-sample" in md or "OUT-OF-SAMPLE" in md
    assert "buy&hold" in md          # benchmark row present (§7 vs-a-real-benchmark)
    assert "whale_retail_flow" in md
    assert "0.8" in md  # the oos sharpe shows up
    assert "Sensitivity" in md or "sensitivity" in md


def test_render_report_flags_degraded_or_honest_limits():
    md = render_report(_result(), sensitivity=[], notes="Edge weak OOS; framework-first per C1.")
    assert "framework-first" in md
