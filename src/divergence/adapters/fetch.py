from __future__ import annotations
import pandas as pd
import requests
from .cmc_client import CMCClient, PATHS

# --- E1 variation points: response-shape extractors. Probed 2026-06-12 against
# the supplied CMC key (free tier): OHLCV -> 403, whale/DEX-holders -> 500
# (credit_count 0), and Binance is 451 geo-blocked from this environment.
# Price therefore comes from the CoinGecko free daily series; the whale/funding
# extractors are kept fail-soft so they light up automatically on a key upgrade.
# Downstream frame schema is fixed regardless of which sources land. ---

_COINGECKO_IDS = {"BTC": "bitcoin", "ETH": "ethereum", "SOL": "solana",
                  "BNB": "binancecoin", "DOGE": "dogecoin"}
_COINGECKO_URL = "https://api.coingecko.com/api/v3/coins/{id}/market_chart"


def _price_frame(token: str) -> pd.DataFrame:
    """Daily close from CoinGecko free market_chart (CMC OHLCV is 403 on free tier)."""
    cid = _COINGECKO_IDS[token]
    r = requests.get(_COINGECKO_URL.format(id=cid),
                     params={"vs_currency": "usd", "days": 365, "interval": "daily"},
                     headers={"Accept": "application/json"}, timeout=30)
    r.raise_for_status()
    prices = r.json().get("prices", [])
    return pd.DataFrame([{"day": pd.to_datetime(int(ms), unit="ms").date(),
                          "price": float(px)} for ms, px in prices])


def _fear_greed_frame(client: CMCClient) -> pd.DataFrame:
    js = client.get_json(PATHS["fear_greed"], {"start": 1, "limit": 500})
    return pd.DataFrame([{"day": pd.to_datetime(int(d["timestamp"]), unit="s").date(),
                          "fear_greed": float(d["value"])} for d in js["data"]])   # market-wide


def _whale_frame(client: CMCClient, token: str) -> pd.DataFrame:
    """Hero signal. CMC free tier returns 500/credit_count=0 here (probed 2026-06-12);
    empty -> column absent -> score_window degrades to crowd-contrarian mode."""
    try:
        js = client.get_json(PATHS["whale_retail"], {"symbol": token, "count": 500})
        data = js.get("data") or []
        return pd.DataFrame([{"day": pd.to_datetime(d["timestamp"]).date(),
                              "whale_retail_flow": float(d["net_whale_flow"])} for d in data])
    except Exception:
        return pd.DataFrame()


def _funding_frame(client: CMCClient, token: str) -> pd.DataFrame:
    """CMC derivatives first, then Binance fallback (§6). Both unavailable on this
    tier/region (probed 2026-06-12) -> empty -> open_interest/funding render None."""
    try:
        js = client.get_json("/v1/derivatives/funding-rate/historical",
                             {"symbol": token, "count": 500})
        return pd.DataFrame([{"day": pd.to_datetime(d["timestamp"]).date(),
                              "funding_rate": float(d["funding_rate"]),
                              "open_interest": float(d.get("open_interest", "nan"))}
                             for d in js["data"]])
    except Exception:
        try:
            return _binance_funding_frame(token)
        except Exception:
            return pd.DataFrame()


def _binance_funding_frame(token: str) -> pd.DataFrame:
    r = requests.get("https://fapi.binance.com/fapi/v1/fundingRate",
                     params={"symbol": f"{token}USDT", "limit": 1000}, timeout=30)
    r.raise_for_status()
    df = pd.DataFrame([{"day": pd.to_datetime(int(x["fundingTime"]), unit="ms").date(),
                        "funding_rate": float(x["fundingRate"])} for x in r.json()])
    return df.groupby("day", as_index=False)["funding_rate"].mean() if not df.empty else df


def build_frame(client: CMCClient, token: str) -> pd.DataFrame:
    """Outer-join all available signals into one row/day frame and cache it as {token}_frame.
    A signal that errors or is empty is simply left out -> HistoricalAdapter renders it None,
    and signal_core takes its degradation path. social_heat is optional and omitted by default."""
    frame = _price_frame(token)
    for part in (_fear_greed_frame(client), _whale_frame(client, token), _funding_frame(client, token)):
        if part is not None and not part.empty:
            frame = frame.merge(part, on="day", how="left")
    frame = frame.sort_values("day").reset_index(drop=True)
    client.cache_put(f"{token}_frame", frame)
    return frame
