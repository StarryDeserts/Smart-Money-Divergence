from __future__ import annotations
from collections.abc import Callable
from datetime import date
from ..types import Snapshot
from .base import assert_schema

_OPT = ("whale_retail_flow", "funding_rate", "open_interest", "social_heat", "fear_greed")
Row = dict
FetchFn = Callable[[str, int], list[Row]]


def _to_snapshot(token: str, row: Row) -> Snapshot:
    return Snapshot(token=token, day=row["day"], price=float(row["price"]),
                    **{k: (None if row.get(k) is None else float(row[k])) for k in _OPT})


class LiveAdapter:
    """Live provider for the Skill runtime. `fetch(token, lookback) -> list[dict rows]`
    is injected so the transport (CMC Pro REST today, Agent Hub MCP later) is swappable
    without touching the signal path. Emits the SAME schema the backtest consumed."""

    def __init__(self, fetch: FetchFn):
        self._fetch = fetch

    def trailing_window(self, token: str, end: date | None, lookback: int) -> list[Snapshot]:
        rows = self._fetch(token, lookback)
        snaps = sorted((_to_snapshot(token, r) for r in rows), key=lambda s: s.day)
        if end is not None:
            snaps = [s for s in snaps if s.day <= end]
        for s in snaps:
            assert_schema(s)
        return snaps[-lookback:]
