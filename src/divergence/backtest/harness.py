from __future__ import annotations
from dataclasses import dataclass, field
import numpy as np
from ..signal_core import score_window, decide, calibrate_theta
from .simulate import simulate
from .metrics import sharpe, max_drawdown, hit_rate, equity_curve


@dataclass
class BacktestResult:
    theta_abs: float
    total_days: int
    in_sample_days: int
    oos_days: int
    is_metrics: dict
    oos_metrics: dict
    is_benchmark: dict                                  # equal-weight buy&hold, same days
    oos_benchmark: dict                                 # the §7 "vs a real benchmark" headline pair
    signals: list = field(default_factory=list)        # (token, Signal) out-of-sample
    attribution: dict = field(default_factory=dict)


def _position(sig) -> float:
    base = {"long": 1.0, "short": -1.0, "flat": 0.0}[sig.direction]
    return base * sig.confidence


def _daily_returns(snaps):
    out = [0.0]
    for i in range(1, len(snaps)):
        p0 = snaps[i - 1].price
        out.append((snaps[i].price - p0) / p0 if p0 else 0.0)
    return out


def _block(returns, turns) -> dict:
    """Metrics for one equal-weight portfolio return segment."""
    eq = equity_curve(returns)
    return {"n_days": len(returns), "sharpe": sharpe(returns),
            "max_drawdown": max_drawdown(eq), "hit_rate": hit_rate(returns),
            "turnover": float(sum(turns)), "total_return": (eq[-1] - 1.0) if eq else 0.0}


def run_backtest(history, *, lookback=90, theta_quantile=0.8, allow_short=False,
                 cost_bps=15.0, split=0.65) -> BacktestResult:
    if not history:
        raise ValueError("run_backtest: history is empty — pass at least one token's snapshots")
    # 1) score every day per token (causal windows)
    per_token = {}
    for token, snaps in history.items():
        snaps = sorted(snaps, key=lambda s: s.day)
        scores = [score_window(snaps[: i + 1], lookback=lookback) for i in range(len(snaps))]
        per_token[token] = (snaps, scores, _daily_returns(snaps))

    # 2) global in-sample cut (by index fraction of the longest series) -> boundary DATE
    longest = max((v[0] for v in per_token.values()), key=len)
    total = len(longest)
    cut = int(total * split)
    boundary_day = longest[cut].day if cut < total else None   # first out-of-sample calendar day

    # 3) calibrate theta on in-sample |D| only
    in_d = [sc.divergence for (_, scores, _) in per_token.values() for sc in scores[:cut]]
    theta = calibrate_theta(in_d, quantile=theta_quantile)

    # 4) per-token positions + simulated daily strat/benchmark returns, pooled by CALENDAR DAY
    #    into an equal-weight daily-rebalanced portfolio (averaging across tokens each day, so
    #    one token's series never compounds onto another's at a seam).
    strat_by_day, bench_by_day, turn_by_day = {}, {}, {}
    oos_signals, attr_num, attr_den = [], {}, {}
    for token, (snaps, scores, rets) in per_token.items():
        pos = [_position(decide(sc, theta_abs=theta, allow_short=allow_short)) for sc in scores]
        strat = simulate(pos, rets, cost_bps=cost_bps)
        bench = simulate([1.0] * len(rets), rets, cost_bps=0.0)
        prev = 0.0
        for i, s in enumerate(snaps):
            d = s.day
            strat_by_day.setdefault(d, []).append(strat[i])
            bench_by_day.setdefault(d, []).append(bench[i])
            turn_by_day.setdefault(d, []).append(abs(pos[i] - prev))
            prev = pos[i]
            if boundary_day is not None and d >= boundary_day:        # out-of-sample
                oos_signals.append((token, decide(scores[i], theta_abs=theta, allow_short=allow_short)))
                fwd = rets[i + 1] if i + 1 < len(rets) else 0.0
                for dr in scores[i].drivers:
                    attr_num[dr.signal] = attr_num.get(dr.signal, 0.0) + np.sign(dr.z) * pos[i] * fwd
                    attr_den[dr.signal] = attr_den.get(dr.signal, 0) + 1

    # 5) collapse to one equal-weight portfolio series, split IS/OOS by the boundary date
    days = sorted(strat_by_day)
    port = [float(np.mean(strat_by_day[d])) for d in days]
    benchp = [float(np.mean(bench_by_day[d])) for d in days]
    turn = [float(np.mean(turn_by_day[d])) for d in days]
    is_k = [k for k, d in enumerate(days) if boundary_day is None or d < boundary_day]
    oos_k = [k for k, d in enumerate(days) if boundary_day is not None and d >= boundary_day]

    def seg(series, idx, *, is_bench=False):
        s = [series[k] for k in idx]
        t = [1.0 if j == 0 else 0.0 for j in range(len(idx))] if is_bench else [turn[k] for k in idx]
        return _block(s, t)

    attribution = {k: attr_num[k] / attr_den[k] for k in attr_num if attr_den[k]}
    return BacktestResult(theta_abs=theta, total_days=total, in_sample_days=len(is_k),
                          oos_days=len(oos_k),
                          is_metrics=seg(port, is_k), oos_metrics=seg(port, oos_k),
                          is_benchmark=seg(benchp, is_k, is_bench=True),
                          oos_benchmark=seg(benchp, oos_k, is_bench=True),
                          signals=oos_signals, attribution=attribution)
