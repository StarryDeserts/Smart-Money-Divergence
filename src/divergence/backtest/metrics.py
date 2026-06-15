from collections.abc import Sequence
import numpy as np


def equity_curve(returns: Sequence[float]) -> list[float]:
    eq, v = [], 1.0
    for r in returns:
        v *= (1.0 + r)
        eq.append(v)
    return eq


def sharpe(returns: Sequence[float], *, periods_per_year: int = 252) -> float:
    a = np.asarray(returns, dtype=float)
    if a.size == 0:
        return 0.0
    sd = a.std(ddof=0)
    if sd == 0:
        return 0.0
    return float((a.mean() / sd) * np.sqrt(periods_per_year))


def max_drawdown(equity: Sequence[float]) -> float:
    peak, mdd = -np.inf, 0.0
    for v in equity:
        peak = max(peak, v)
        mdd = min(mdd, v / peak - 1.0)
    return float(mdd)


def hit_rate(returns: Sequence[float]) -> float:
    nz = [r for r in returns if r != 0.0]
    if not nz:
        return 0.0
    return sum(1 for r in nz if r > 0) / len(nz)


def turnover(positions: Sequence[float]) -> float:
    prev, total = 0.0, 0.0
    for p in positions:
        total += abs(p - prev)
        prev = p
    return float(total)
