from __future__ import annotations
from ..signal_core import score_window, decide
from ..explain import explain

# Committed E2 in-sample calibration (docs/superpowers/notes/2026-06-12-e2-gate.md).
# The single source of truth for the decision threshold — demo.py and cli.py import it.
DEFAULT_THETA = 1.444


def _driver_dict(d) -> dict:
    return {"signal": d.signal, "z": round(d.z, 3), "side": d.side, "label": d.label}


def run_skill(token, provider, *, theta_abs: float = DEFAULT_THETA, lookback: int = 90,
              allow_short: bool = False) -> dict:
    """Live Skill entrypoint. Reuses the exact backtested signal path.
    Returns C6 layered output: Layer-1 verdict string + Layer-2 structured detail."""
    window = provider.trailing_window(token, None, lookback)
    score = score_window(window, lookback=lookback)
    signal = decide(score, theta_abs=theta_abs, allow_short=allow_short)
    return {
        "verdict": explain(signal),
        "detail": {
            "token": signal.token,
            "day": signal.day.isoformat(),
            "direction": signal.direction,
            "divergence": round(signal.divergence, 3),
            "confidence": round(signal.confidence, 3),
            "capital_score": (None if signal.capital_score is None else round(signal.capital_score, 3)),
            "crowd_score": (None if signal.crowd_score is None else round(signal.crowd_score, 3)),
            "drivers": [_driver_dict(d) for d in signal.drivers],
            "degraded": signal.degraded,
        },
    }
