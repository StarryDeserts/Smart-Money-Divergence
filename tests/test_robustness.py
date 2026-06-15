from datetime import date, timedelta
from divergence.types import Snapshot
from divergence.backtest.robustness import sensitivity_grid, leave_one_out


def _hist(tokens=("BTC", "ETH"), n=160):
    start = date(2025, 1, 1)
    h = {}
    for j, t in enumerate(tokens):
        h[t] = [Snapshot(token=t, day=start + timedelta(days=i), price=100.0 * (1.005 ** i),
                         whale_retail_flow=1.0 if (i + j) % 3 == 0 else -1.0, fear_greed=50.0)
                for i in range(n)]
    return h


def test_sensitivity_grid_covers_all_combos():
    grid = sensitivity_grid(_hist(), thetas=[0.7, 0.8], lookbacks=[20, 30], costs=[5.0])
    assert len(grid) == 4                       # 2 * 2 * 1
    for row in grid:
        assert "oos_sharpe" in row and "theta_quantile" in row


def test_leave_one_out_drops_each_token_once():
    loo = leave_one_out(_hist(("BTC", "ETH", "SOL")), lookback=20)
    assert len(loo) == 3
    assert {r["held_out"] for r in loo} == {"BTC", "ETH", "SOL"}
