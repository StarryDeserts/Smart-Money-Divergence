# E1 — Data Availability Spike (2026-06-12)

**Purpose:** probe the supplied `CMC_PRO_API_KEY` to determine which signals have
real daily history, and lock the spec §6 fallback tier the backtest will run in.

## Key tier

`/v1/key/info` → `plan name=None, credit_limit_monthly=15000, rate_limit_minute=50`.
This is the **free / Basic** CMC tier: no historical OHLCV, no DEX / on-chain
holder data, no derivatives.

## Per-signal results (5 tokens: BTC, ETH, SOL, BNB, DOGE)

| Signal | Endpoint | Result | Usable? |
|---|---|---|---|
| **fear_greed** | CMC `/v3/fear-and-greed/historical` | 500 rows, `2025-01-28 .. 2026-06-11`, market-wide `{timestamp(unix-s), value}` | ✅ yes |
| **price** | CMC `/v2/cryptocurrency/ohlcv/historical` | **HTTP 403** (not on free tier) | ❌ → substituted |
| **price (sub)** | CoinGecko free `/coins/{id}/market_chart?days=365&interval=daily` | 366 rows/token, `2025-06-13 .. 2026-06-12`, no gaps | ✅ yes |
| **whale_retail_flow** (hero) | CMC `/v4/dex/networks/holders/historical` | HTTP 200 but `error_code 500 "system busy", credit_count 0` — no `data` | ❌ no |
| **funding_rate / open_interest** | CMC `/v1/derivatives/funding-rate/historical` | not on free tier | ❌ no |
| **funding (fallback)** | Binance `fapi/api.binance.com` | **HTTP 451** (geo-blocked from this environment) | ❌ no |
| **social_heat** | (not probed) | optional; omitted by default | — |

**Backtestable overlap (price ∩ F&G):** `2025-06-13 .. 2026-06-11` ≈ **364 days × 5 tokens**.
Cached frames: `data/{TOKEN}_frame.parquet`, columns `[day, price, fear_greed]`,
price gap-free, F&G 364/366 non-null.

## Chosen fallback tier: **AMBER** (degraded crowd-contrarian)

- **No capital side at all** — the hero whale-vs-retail signal and funding/OI are
  unavailable on this key, so `capital_score` is always `None`.
- **Crowd side is solid** — two crowd signals land: `fear_greed` (CMC) +
  price-`momentum` (derived from the CoinGecko series inside `score_window`).
- The degradation path is **confirmed live end-to-end** on real BTC data:
  `score_window` → `capital_score=None, crowd_score=-0.805, degraded=True`,
  `D = −crowd_score` (crowd-contrarian). No code redesign needed (spec §6 GATE NOTE).

This is Amber, not Red: we have a clean price series + two crowd signals over a
year of daily data — a functioning backtest, just without the differentiator.

## Path / extractor corrections applied (in `adapters/fetch.py`)

- **Price** now from CoinGecko (`_price_frame`); `PATHS["ohlcv"]` retained for a paid tier.
- **fear_greed** extractor (`_fear_greed_frame`, unix-seconds `timestamp` + `value`) **CONFIRMED correct**.
- **whale** extractor (`_whale_frame`, keys `timestamp` / `net_whale_flow`) **UNCONFIRMED** —
  endpoint never returned a body; re-verify the response shape if the key is upgraded.
- **whale / funding** extractors made **fail-soft** (return empty → column absent →
  degradation path) so they light up automatically on a key upgrade with zero code change.

## Open items

- **Agent Hub Skill delivery format** (spec Phase 5): NOT yet confirmed here — defer to Phase 5.
- **GO/NO-GO (the gate):** the hackathon's headline differentiator (on-chain
  smart-money whale flow) is unavailable on the free key. Options, in
  recommendation order:
  1. **Upgrade / add-on the CMC key** to unlock the DEX-holders + OHLCV endpoints →
     restores the Green tier and the actual "smart money vs the crowd" thesis. Re-run E1.
  2. **Proceed Amber** — run the backtest now in crowd-contrarian mode over 364
     days × 5 tokens, and demo the hero signal *live* in the Skill + as a documented
     case study (spec §6 GATE NOTE explicitly sanctions this).
  3. Abandon the differentiator (not recommended — collapses to a generic F&G play).
