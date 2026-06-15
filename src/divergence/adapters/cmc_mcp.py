"""CMC Agent Hub MCP transport — the live-data seam for the Skill runtime.

The shipped backtest reads CMC Pro REST (cmc_client.py / fetch.py). On the free
tier the per-token whale-vs-retail capital axis is paywalled — `_whale_frame`
gets 500/credit_count=0 — so the backtest runs Amber (crowd-only). The CMC Agent
Hub MCP server exposes that same capital axis *live on the free key*:

    get_crypto_metrics(id) -> circulatingSupplyDistribution / addressesByHoldingTime

This module talks to that MCP server (streamable HTTP, header-key auth — zero
money, NOT the x402/Base rail) and maps the four relevant tools onto our schema.

Honest scope: MCP is **latest-only** (one bar, no history). `_causal_z` needs >=2
points, so a single live tip cannot produce a capital z-score / flip the backtest
to Green. MCP delivers the missing Green *ingredient* (the live capital structure),
not a Green *verdict*. `whale_retail_flow` stays None here on purpose: the metric
is holder *structure*, not the directional net-flow the backtest scores.
"""
from __future__ import annotations

import asyncio
import json
import os
from datetime import datetime, timezone

from .live import FetchFn, Row

MCP_URL = "https://mcp.coinmarketcap.com/mcp"
_AUTH_HEADER = "X-CMC-MCP-API-KEY"

# Demo basket (mirrors fetch._COINGECKO_IDS). CMC numeric ids; unknown tokens
# raise rather than guess — keeps the seam deterministic and offline-auditable.
_CMC_IDS = {"BTC": 1, "ETH": 1027, "SOL": 5426, "BNB": 1839, "DOGE": 74}

_SUFFIX = {"K": 1e3, "M": 1e6, "B": 1e9, "T": 1e12}


def _to_float(v) -> float | None:
    """Parse CMC's mixed numeric forms: 65671.7, '-0.00025221', '383.61 B', '+1.9%'."""
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip().replace(",", "")
    if not s:
        return None
    pct = s.endswith("%")
    if pct:
        s = s[:-1].strip()
    mult = 1.0
    if s and s[-1].upper() in _SUFFIX:
        mult = _SUFFIX[s[-1].upper()]
        s = s[:-1].strip()
    try:
        f = float(s)
    except ValueError:
        return None
    return f / 100.0 if pct else f * mult


def _get(d: dict, *path):
    cur = d
    for k in path:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(k)
    return cur


def _parse(result) -> dict | list:
    if not getattr(result, "content", None):
        raise RuntimeError("empty MCP tool result")
    txt = getattr(result.content[0], "text", None)
    if txt is None:
        raise RuntimeError("MCP tool result carried no text content")
    return json.loads(txt)


def resolve_id(token: str) -> int:
    cid = _CMC_IDS.get(token.upper())
    if cid is None:
        raise ValueError(
            f"no CMC id mapped for {token!r}; known: {sorted(_CMC_IDS)}. "
            "Add it to _CMC_IDS to extend the basket."
        )
    return cid


async def _fetch_live(cmc_id: int, api_key: str) -> dict:
    """One MCP session, four tool calls. Imports `mcp` lazily — it's a venv-only
    integration dep, never required to import the core Skill."""
    from mcp import ClientSession
    from mcp.client.streamable_http import streamablehttp_client

    async with streamablehttp_client(MCP_URL, headers={_AUTH_HEADER: api_key}) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            async def call(tool: str, args: dict):
                return _parse(await session.call_tool(tool, args))

            quotes = await call("get_crypto_quotes_latest", {"id": str(cmc_id)})
            metrics = await call("get_crypto_metrics", {"id": str(cmc_id)})
            glob = await call("get_global_metrics_latest", {})
            deriv = await call("get_global_crypto_derivatives_metrics", {})
    return {"quotes": quotes, "metrics": metrics, "global": glob, "deriv": deriv}


def _capital_structure(metrics: dict) -> dict:
    """The per-token whale/retail axis the free REST tier paywalls — surfaced live.
    Holder *structure* (a snapshot), which is the Green ingredient, not a flow."""
    csd = metrics.get("circulatingSupplyDistribution", {})
    abt = metrics.get("addressesByHoldingTime", {})
    return {
        "whale_supply_pct": _to_float(_get(csd, "whales", "percentOfSupply")),
        "retail_supply_pct": _to_float(_get(csd, "others", "percentOfSupply")),
        "traders_pct": _to_float(_get(abt, "traders", "percentOfAddresses")),
        "cruisers_pct": _to_float(_get(abt, "cruisers", "percentOfAddresses")),
        "holders_pct": _to_float(_get(abt, "holders", "percentOfAddresses")),
    }


def live_snapshot(token: str, api_key: str | None = None) -> dict:
    """Fetch one live tip for `token` via CMC Agent Hub MCP and map it to our schema.

    Crowd axis (fear_greed/funding/OI) is market-wide — same semantics the backtest
    used for fear_greed. `capital_structure` is the per-token whale/retail axis.
    `whale_retail_flow` is None by design (structure, not directional flow; and one
    latest bar can't be z-scored anyway).
    """
    api_key = api_key or os.environ.get("CMC_PRO_API_KEY", "")
    if not api_key:
        raise RuntimeError("no CMC_PRO_API_KEY (pass api_key= or set it in .env.local/env)")
    cmc_id = resolve_id(token)
    raw = asyncio.run(_fetch_live(cmc_id, api_key))

    quotes = raw["quotes"]
    q0 = quotes[0] if isinstance(quotes, list) and quotes else (quotes if isinstance(quotes, dict) else {})
    price = _to_float(q0.get("price"))
    if price is None:
        raise RuntimeError(f"MCP returned no price for {token!r} (id {cmc_id})")

    return {
        "token": token.upper(),
        "cmc_id": cmc_id,
        "name": q0.get("name"),
        "day": datetime.now(timezone.utc).date(),
        "price": price,
        "fear_greed": _to_float(_get(raw["global"], "sentiment", "fear_greed", "current", "index")),
        "funding_rate": _to_float(_get(raw["deriv"], "fundingRate", "current")),
        "open_interest": _to_float(_get(raw["deriv"], "totalOpenInterest", "current")),
        "whale_retail_flow": None,
        "capital_structure": _capital_structure(raw["metrics"]),
        "source": "CMC Agent Hub MCP",
        "mcp_url": MCP_URL,
    }


def make_mcp_fetch(api_key: str | None = None) -> FetchFn:
    """Build a `FetchFn` (LiveAdapter's injection point) backed by CMC Agent Hub MCP.

    Returns a single live row — MCP is latest-only, so this is a 'live tip', not a
    backtest history source. Plugged into LiveAdapter it yields one Snapshot; the
    signal path will degrade (no trailing window to z-score) — that's the honest
    free-tier behaviour, not a bug.
    """
    def fetch(token: str, lookback: int) -> list[Row]:
        snap = live_snapshot(token, api_key)
        return [{
            "day": snap["day"],
            "price": snap["price"],
            "whale_retail_flow": snap["whale_retail_flow"],
            "funding_rate": snap["funding_rate"],
            "open_interest": snap["open_interest"],
            "social_heat": None,
            "fear_greed": snap["fear_greed"],
        }]

    return fetch
