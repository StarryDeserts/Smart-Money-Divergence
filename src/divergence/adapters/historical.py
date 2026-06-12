from __future__ import annotations
from datetime import date
import math
import pandas as pd
from ..types import Snapshot
from .cmc_client import CMCClient

_OPT = ("whale_retail_flow", "funding_rate", "open_interest", "social_heat", "fear_greed")


def _cell(row, name):
    if name not in row or pd.isna(row[name]):
        return None
    return float(row[name])


class HistoricalAdapter:
    """Reads a per-token cached 'frame' (one row/day) into Snapshots.
    Frame is populated by fetch_* (CMC Pro); tests seed the cache directly."""

    def __init__(self, client: CMCClient):
        self.client = client

    def _frame(self, token: str) -> pd.DataFrame:
        df = self.client.cache_get(f"{token}_frame")
        if df is None:
            raise FileNotFoundError(f"no cached frame for {token}; run fetch first")
        return df.sort_values("day").reset_index(drop=True)

    def history(self, token: str) -> list[Snapshot]:
        df = self._frame(token)
        out: list[Snapshot] = []
        for _, row in df.iterrows():
            d = row["day"]
            out.append(Snapshot(token=token, day=d if isinstance(d, date) else pd.to_datetime(d).date(),
                                price=float(row["price"]),
                                **{k: _cell(row, k) for k in _OPT}))
        return out

    def trailing_window(self, token: str, end: date | None, lookback: int) -> list[Snapshot]:
        hist = self.history(token)
        if end is not None:
            hist = [s for s in hist if s.day <= end]
        return hist[-lookback:]

    def daterange(self, token: str) -> list[date]:
        return [s.day for s in self.history(token)]
