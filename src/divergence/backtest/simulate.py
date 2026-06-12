from collections.abc import Sequence


def simulate(positions: Sequence[float], asset_returns: Sequence[float], *, cost_bps: float) -> list[float]:
    """Daily net strategy returns. positions[t] is the position held entering day t+1,
    so it earns asset_returns[t+1]. Cost charged on |positions[t] - positions[t-1]| (prior = 0)."""
    if len(positions) != len(asset_returns):
        raise ValueError("positions and asset_returns must be equal length")
    cost = cost_bps / 10_000.0
    out: list[float] = []
    prev = 0.0
    for t in range(len(positions)):
        turn = abs(positions[t] - prev)
        pnl = positions[t - 1] * asset_returns[t] if t > 0 else 0.0
        out.append(pnl - turn * cost)
        prev = positions[t]
    return out
