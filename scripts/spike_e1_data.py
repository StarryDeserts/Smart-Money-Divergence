"""E1 spike: probe CMC Pro history depth for the hero + supporting signals.
Run: CMC_PRO_API_KEY=... python scripts/spike_e1_data.py
Prints, per token, how many daily rows each signal returns, the date span,
and a compact structural fingerprint (top-level keys + first-record keys) so
the frame extractors in adapters/fetch.py can be confirmed/fixed (E1 variation pts).
Values are NOT printed (avoids dumping payloads / leaking anything sensitive)."""
import os, sys, json
from divergence.adapters.cmc_client import CMCClient, PATHS

TOKENS = ["BTC", "ETH", "SOL", "BNB", "DOGE"]


def _shape(obj, depth=0):
    """Compact structural fingerprint: keys only, no values, capped depth."""
    if isinstance(obj, dict):
        keys = list(obj.keys())
        head = keys[:12]
        return "{" + ", ".join(str(k) for k in head) + ("..." if len(keys) > 12 else "") + "}"
    if isinstance(obj, list):
        return f"[len={len(obj)}]" + (" first=" + _shape(obj[0], depth + 1) if obj and depth < 2 else "")
    return type(obj).__name__


def probe(client, path, params, label):
    try:
        js = client.get_json(path, params)
        top = _shape(js)
        data = js.get("data", js) if isinstance(js, dict) else js
        if isinstance(data, dict):
            n = "?(dict)"
            inner = "data=" + _shape(data)
        elif hasattr(data, "__len__"):
            n = len(data)
            inner = "data" + _shape(data)
        else:
            n = "?"
            inner = "data=" + type(data).__name__
        print(f"  {label:18} rows={n:>8}  top={top}")
        print(f"  {'':18} {inner}")
    except Exception as e:  # spike: we WANT to see which endpoints fail
        msg = str(e)
        print(f"  {label:18} ERROR {type(e).__name__}: {msg[:160]}")


def main():
    c = CMCClient()
    if not c.api_key:
        sys.exit("set CMC_PRO_API_KEY")
    for t in TOKENS:
        print(t)
        probe(c, PATHS["fear_greed"], {"start": 1, "limit": 500}, "fear_greed")
        probe(c, PATHS["ohlcv"], {"symbol": t, "count": 500, "interval": "daily"}, "ohlcv")
        probe(c, PATHS["whale_retail"], {"symbol": t, "count": 500}, "whale_retail(hero)")


def build(tokens):
    c = CMCClient()
    from divergence.adapters.fetch import build_frame
    for t in tokens:
        df = build_frame(c, t)
        cols = [col for col in df.columns if col not in ("day", "price")]
        print(f"{t}: {len(df)} rows, signals present = {cols}")


if __name__ == "__main__":
    main()
