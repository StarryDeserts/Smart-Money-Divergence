from __future__ import annotations
from dataclasses import dataclass, field
import numpy as np
from ..signal_core import score_window, decide, calibrate_theta
from .simulate import simulate
from .metrics import sharpe, max_drawdown, hit_rate, turnover, equity_curve


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


def _metrics(positions, rets, cost_bps):
    strat = simulate(positions, rets, cost_bps=cost_bps)
    eq = equity_curve(strat)
    return {"n_days": len(strat), "sharpe": sharpe(strat), "max_drawdown": max_drawdown(eq),
            "hit_rate": hit_rate(strat), "turnover": turnover(positions),
            "total_return": (eq[-1] - 1.0) if eq else 0.0}, strat


def run_backtest(history, *, lookback=90, theta_quantile=0.8, allow_short=False,
                 cost_bps=15.0, split=0.65) -> BacktestResult:
    # 1) score every day per token (causal windows)
    per_token = {}
    for token, snaps in history.items():
        snaps = sorted(snaps, key=lambda s: s.day)
        scores, rets = [], _daily_returns(snaps)
        for i in range(len(snaps)):
            scores.append(score_window(snaps[: i + 1], lookback=lookback))
        per_token[token] = (snaps, scores, rets)

    # 2) global in-sample cut (by index fraction of the longest series)
    total = max(len(v[0]) for v in per_token.values())
    cut = int(total * split)

    # 3) calibrate theta on in-sample |D| only
    in_d = [sc.divergence for (_, scores, _) in per_token.values() for sc in scores[:cut]]
    theta = calibrate_theta(in_d, quantile=theta_quantile)

    # 4) evaluate -> positions, split metrics, attribution
    is_pos, is_ret, oos_pos, oos_ret, oos_signals = [], [], [], [], []
    attr_num, attr_den = {}, {}
    for token, (snaps, scores, rets) in per_token.items():
        for i, sc in enumerate(scores):
            sig = decide(sc, theta_abs=theta, allow_short=allow_short)
            pos = _position(sig)
            if i < cut:
                is_pos.append(pos); is_ret.append(rets[i])
            else:
                oos_pos.append(pos); oos_ret.append(rets[i]); oos_signals.append((token, sig))
                fwd = rets[i + 1] if i + 1 < len(rets) else 0.0
                for d in sc.drivers:
                    attr_num[d.signal] = attr_num.get(d.signal, 0.0) + np.sign(d.z) * pos * fwd
                    attr_den[d.signal] = attr_den.get(d.signal, 0) + 1

    is_metrics, _ = _metrics(is_pos, is_ret, cost_bps)
    oos_metrics, _ = _metrics(oos_pos, oos_ret, cost_bps)
    # benchmark: equal-weight, always-long buy&hold over the SAME days, no rebalance cost.
    # (positions all 1.0; per-token series each begin with a 0.0 return, so concatenation
    #  never bleeds one token's position into another's first day — same as the strategy path.)
    is_bench, _ = _metrics([1.0] * len(is_ret), is_ret, cost_bps=0.0)
    oos_bench, _ = _metrics([1.0] * len(oos_ret), oos_ret, cost_bps=0.0)
    attribution = {k: attr_num[k] / attr_den[k] for k in attr_num if attr_den[k]}

    return BacktestResult(theta_abs=theta, total_days=total, in_sample_days=cut,
                          oos_days=total - cut, is_metrics=is_metrics, oos_metrics=oos_metrics,
                          is_benchmark=is_bench, oos_benchmark=oos_bench,
                          signals=oos_signals, attribution=attribution)
