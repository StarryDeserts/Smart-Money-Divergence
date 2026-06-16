"""Zero-config fallback provider for a crash-proof first run.

`data/` is gitignored, so a fresh clone has no cached frames and the
HistoricalAdapter would raise FileNotFoundError. SyntheticProvider lets
`python scripts/demo.py` (and cli.py) run with zero setup by emitting a
deterministic window that exercises the real signal path's *degraded* tier.
It depends only on `types` — no pandas, no network, no key."""
from __future__ import annotations
from datetime import date, timedelta

from ..types import Snapshot

_SYNTH_START = date(2025, 1, 1)
_FG_BASELINE = 52.0
_FG_LAST = 8.0  # extreme-fear spike on the most recent day


class SyntheticProvider:
    """Deterministic offline provider. The capital axis is absent
    (whale_retail_flow=None) and crowd sentiment crashes into extreme fear on
    the last day. score_window therefore has no capital z-score and a strongly
    negative crowd z-score -> contrarian long, flagged degraded with confidence
    capped. It fabricates nothing about real markets; it exists only so the demo
    never crashes on a fresh clone."""

    def trailing_window(self, token: str, end: date | None, lookback: int) -> list[Snapshot]:
        n = max(2, lookback)
        out: list[Snapshot] = []
        for i in range(n):
            last = i == n - 1
            out.append(Snapshot(
                token=token,
                day=_SYNTH_START + timedelta(days=i),
                price=100.0,
                whale_retail_flow=None,  # capital axis unavailable -> degraded path
                fear_greed=(_FG_LAST if last else _FG_BASELINE),
            ))
        return out


def resolve_provider(token: str, *, client=None):
    """Return (provider, note). Prefer the cached historical frame; if it's
    absent (fresh clone, no data/), fall back to SyntheticProvider so callers
    never hit FileNotFoundError. `note` is None on the real path, else a
    human-readable stderr warning. `client` is injectable for tests."""
    from .cmc_client import CMCClient
    from .historical import HistoricalAdapter
    client = client or CMCClient()
    if client.cache_get(f"{token}_frame") is not None:
        return HistoricalAdapter(client), None
    note = (f"[synthetic] no cached frame for {token} (data/ is gitignored) — "
            "using SyntheticProvider: a degraded demo signal, NOT real market data. "
            "Run the fetch scripts with CMC_PRO_API_KEY to populate real history.")
    return SyntheticProvider(), note
