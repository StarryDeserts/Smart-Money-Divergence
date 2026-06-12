from .types import Signal

_PHRASES = {
    "whale_retail_flow": {"capital": ("whales distributing", "whales accumulating")},
    "fear_greed": ("crowd fearful", "crowd greedy"),
    "social_heat": ("social quiet", "social hot"),
    "momentum": ("price weak", "price chasing"),
    "leverage": ("longs light", "longs crowded"),
}
_VERB = {"long": "accumulate / long", "short": "reduce / short", "flat": "no edge — stand aside"}


def _phrase(signal_name: str, z: float) -> str:
    spec = _PHRASES.get(signal_name)
    if spec is None:
        return signal_name
    pair = spec["capital"] if isinstance(spec, dict) else spec
    return pair[1] if z >= 0 else pair[0]


def explain(signal: Signal, *, top_k: int = 3) -> str:
    if signal.direction == "flat":
        return f"{signal.token}: signals aligned, no edge — stand aside."
    reasons = ", ".join(_phrase(d.signal, d.z) for d in signal.drivers[:top_k])
    tag = " (crowd-only mean-reversion mode)" if signal.degraded else ""
    return (f"{signal.token} — {reasons}. Divergence |{signal.divergence:.1f}|"
            f" → bias: {_VERB[signal.direction]}{tag}.")
