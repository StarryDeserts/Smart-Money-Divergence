from collections.abc import Sequence
import numpy as np


def _causal_z(series: Sequence[float | None]) -> float | None:
    """Z-score of the most recent available value vs the window distribution.
    Causal: uses only values present in the window (no future data). None if <2 values."""
    vals = [float(v) for v in series if v is not None]
    if len(vals) < 2:
        return None
    arr = np.asarray(vals, dtype=float)
    sd = float(arr.std(ddof=0))
    if sd == 0.0:
        return 0.0
    return float((arr[-1] - arr.mean()) / sd)


def _momentum_series(prices: Sequence[float], k: int = 5) -> list[float]:
    """k-day trailing returns series, one value per day from index k onward."""
    p = list(prices)
    out: list[float] = []
    for i in range(k, len(p)):
        base = p[i - k]
        out.append((p[i] - base) / base if base else 0.0)
    return out
