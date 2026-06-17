from __future__ import annotations
import os
from pathlib import Path
import pandas as pd
import requests

_BASE = "https://pro-api.coinmarketcap.com"
# --- E1 variation points (confirm in Task 12) ---
PATHS = {
    "fear_greed": "/v3/fear-and-greed/historical",
    "ohlcv": "/v2/cryptocurrency/ohlcv/historical",
    # whale-vs-retail / on-chain holder distribution endpoint — CONFIRM in E1:
    "whale_retail": "/v4/dex/networks/holders/historical",
}


def _default_data_dir() -> Path:
    """Repo-root ``data/`` by default so the cache resolves identically from any CWD
    (running ``cli.py`` from elsewhere must not create a stray empty ``./data`` and
    silently fall back to synthetic). ``DIVERGENCE_DATA_DIR`` overrides it, e.g. a
    mounted volume in a container."""
    override = os.environ.get("DIVERGENCE_DATA_DIR")
    return Path(override) if override else Path(__file__).resolve().parents[3] / "data"


_DEFAULT_DATA_DIR = _default_data_dir()


class CMCClient:
    def __init__(self, api_key: str | None = None, cache_dir: Path | None = _DEFAULT_DATA_DIR):
        self.api_key = api_key or os.environ.get("CMC_PRO_API_KEY", "")
        self.cache_dir = Path(cache_dir) if cache_dir else None
        if self.cache_dir:
            self.cache_dir.mkdir(parents=True, exist_ok=True)

    def get_json(self, path: str, params: dict) -> dict:
        resp = requests.get(_BASE + path,
                            headers={"X-CMC_PRO_API_KEY": self.api_key, "Accept": "application/json"},
                            params=params, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def cache_get(self, key: str) -> pd.DataFrame | None:
        if not self.cache_dir:
            return None
        f = self.cache_dir / f"{key}.parquet"
        return pd.read_parquet(f) if f.exists() else None

    def cache_put(self, key: str, df: pd.DataFrame) -> None:
        if self.cache_dir:
            df.to_parquet(self.cache_dir / f"{key}.parquet", index=False)
