from collections.abc import Sequence
import numpy as np

from .types import Driver, Score, Signal

_MOM_K = 5
_DEGRADED_CONF_FACTOR = 0.6


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


def _field(window, name):
    return [getattr(s, name) for s in window]


def _mean(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


def score_window(window, *, lookback: int = 90) -> Score:
    w = list(window)[-lookback:]
    last = w[-1]

    capital_z = _causal_z(_field(w, "whale_retail_flow"))
    capital_score = capital_z  # hero only, no proxy

    fg_z = _causal_z(_field(w, "fear_greed"))
    social_z = _causal_z(_field(w, "social_heat"))
    funding_z = _causal_z(_field(w, "funding_rate"))
    oi_z = _causal_z(_field(w, "open_interest"))
    leverage_z = _mean([funding_z, oi_z])  # funding/OI crowding
    mom_series = _momentum_series(_field(w, "price"), k=_MOM_K)
    momentum_z = _causal_z(mom_series) if mom_series else None

    crowd_parts = [z for z in (fg_z, social_z, momentum_z, leverage_z) if z is not None]
    crowd_score = sum(crowd_parts) / len(crowd_parts) if crowd_parts else None

    degraded = False
    if capital_score is not None and crowd_score is not None:
        divergence = capital_score - crowd_score
    elif capital_score is None and crowd_score is not None:
        divergence = -crowd_score
        degraded = True
    else:
        divergence = 0.0

    drivers: list[Driver] = []
    if capital_z is not None:
        drivers.append(Driver("whale_retail_flow", capital_z, "capital",
                              "accumulating" if capital_z >= 0 else "distributing"))
    for name, z in (("fear_greed", fg_z), ("social_heat", social_z),
                    ("momentum", momentum_z), ("leverage", leverage_z)):
        if z is not None:
            drivers.append(Driver(name, z, "crowd", "elevated" if z >= 0 else "depressed"))
    drivers.sort(key=lambda d: abs(d.z), reverse=True)

    return Score(token=last.token, day=last.day, divergence=divergence,
                 capital_score=capital_score, crowd_score=crowd_score,
                 drivers=drivers, degraded=degraded)


def calibrate_theta(d_values, *, quantile: float = 0.8) -> float:
    """Absolute |D| threshold at the given quantile of the in-sample divergence distribution.
    NOT tuned per token; one global number, calibrated in-sample only."""
    mags = [abs(float(d)) for d in d_values]
    if not mags:
        return 0.0
    return float(np.quantile(mags, quantile))


def decide(score: Score, *, theta_abs: float, allow_short: bool = False) -> Signal:
    d = score.divergence
    if theta_abs > 0 and d >= theta_abs:
        direction = "long"
    elif theta_abs > 0 and d <= -theta_abs:
        direction = "short" if allow_short else "flat"
    else:
        direction = "flat"

    if direction == "flat":
        confidence = 0.0
    else:
        confidence = min(1.0, abs(d) / (2.0 * theta_abs)) if theta_abs > 0 else 1.0
        if score.degraded:
            confidence *= _DEGRADED_CONF_FACTOR

    return Signal(token=score.token, day=score.day, divergence=d, direction=direction,
                  confidence=confidence, capital_score=score.capital_score,
                  crowd_score=score.crowd_score, drivers=score.drivers, degraded=score.degraded)
