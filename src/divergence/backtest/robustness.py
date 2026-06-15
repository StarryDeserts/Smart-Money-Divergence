from __future__ import annotations
from itertools import product
from .harness import run_backtest


def sensitivity_grid(history, *, thetas, lookbacks, costs, allow_short=False, split=0.65):
    """OOS Sharpe across the knob grid. A robust edge stays positive across most cells;
    a fragile one is positive in only a lucky corner."""
    rows = []
    for q, lb, c in product(thetas, lookbacks, costs):
        res = run_backtest(history, lookback=lb, theta_quantile=q,
                           allow_short=allow_short, cost_bps=c, split=split)
        rows.append({"theta_quantile": q, "lookback": lb, "cost_bps": c,
                     "oos_sharpe": res.oos_metrics["sharpe"],
                     "oos_return": res.oos_metrics["total_return"]})
    return rows


def leave_one_out(history, *, lookback=90, theta_quantile=0.8, cost_bps=15.0,
                  allow_short=False, split=0.65):
    """Drop each token once; the edge should survive removing any single name."""
    out = []
    for held in history:
        sub = {k: v for k, v in history.items() if k != held}
        if not sub:
            continue
        res = run_backtest(sub, lookback=lookback, theta_quantile=theta_quantile,
                           allow_short=allow_short, cost_bps=cost_bps, split=split)
        out.append({"held_out": held, "oos_sharpe": res.oos_metrics["sharpe"],
                    "oos_return": res.oos_metrics["total_return"]})
    return out
