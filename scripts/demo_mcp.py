"""CMC Agent Hub MCP demo: fetch a live tip for a token and surface the per-token
whale-vs-retail capital axis — the data the free CMC *REST* tier paywalls (500/
credit_count=0 in fetch._whale_frame), served live on the same free key via the
Agent Hub MCP server (header-key auth, zero money — NOT the x402/Base rail).

Run:  python scripts/demo_mcp.py BTC      (reads CMC_PRO_API_KEY from .env.local/env)

Honest scope: MCP is latest-only (one bar). The backtest needs trailing history to
z-score, so this live capital structure is the missing Green *ingredient*, not a
Green *verdict* — the shipped backtest stays Amber on the free tier.
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from divergence.adapters.cmc_mcp import MCP_URL, live_snapshot  # noqa: E402


def _load_env_local() -> None:
    env = ROOT / ".env.local"
    if not env.is_file():
        return
    for line in env.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))


def _fmt(v, suffix="", nd=2):
    return f"{v:,.{nd}f}{suffix}" if isinstance(v, (int, float)) else "n/a"


def main() -> int:
    _load_env_local()
    token = (sys.argv[1] if len(sys.argv) > 1 else "BTC").upper()

    print(f"\n== CMC Agent Hub MCP — live tip for {token} ==")
    print(f"   transport : {MCP_URL}  (free key, header auth, zero money)")

    snap = live_snapshot(token)

    print(f"\n  {snap['name']} ({snap['token']}, CMC id {snap['cmc_id']})  @ {snap['day']}")
    print(f"    price          = {_fmt(snap['price'], nd=2)} USD")
    print("\n  crowd axis (market-wide):")
    print(f"    fear_greed     = {_fmt(snap['fear_greed'], nd=0)}  (0=fear, 100=greed)")
    print(f"    funding_rate   = {_fmt(snap['funding_rate'], nd=6)}")
    print(f"    open_interest  = {_fmt(snap['open_interest'], nd=0)} USD")

    cs = snap["capital_structure"]
    print("\n  >> CAPITAL AXIS (per-token, via Agent Hub MCP — paywalled on free REST):")
    print(f"     whale share of supply   = {_fmt(cs['whale_supply_pct'], '%')}")
    print(f"     retail share of supply  = {_fmt(cs['retail_supply_pct'], '%')}")
    print(f"     addresses: traders={_fmt(cs['traders_pct'], '%')}  "
          f"cruisers={_fmt(cs['cruisers_pct'], '%')}  holders={_fmt(cs['holders_pct'], '%')}")

    print("\n  honest note: MCP is latest-only (one bar). The backtest z-scores a")
    print("  trailing window, so this is the Green *ingredient* live — not a Green")
    print("  verdict. The shipped backtest stays Amber (crowd-only) on the free tier.")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
