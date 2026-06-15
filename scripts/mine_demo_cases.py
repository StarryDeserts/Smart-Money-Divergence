"""E4: surface the cleanest 2-3 demo cases from an OOS backtest run.
Run: python scripts/mine_demo_cases.py --tokens BTC,ETH,SOL,...
Prints the highest-|divergence| OOS calls (each flagged [degraded] when the capital side is
absent, as in the Amber tier) + their plain-language verdict, for the demo script."""
import argparse
from divergence.adapters.cmc_client import CMCClient
from divergence.adapters.historical import HistoricalAdapter
from divergence.backtest.harness import run_backtest
from divergence.explain import explain


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tokens", default="BTC,ETH,SOL,BNB,DOGE")
    ap.add_argument("--top", type=int, default=5)
    args = ap.parse_args()
    adapter = HistoricalAdapter(CMCClient())
    history = {t.strip(): adapter.history(t.strip()) for t in args.tokens.split(",")}
    res = run_backtest(history)
    ranked = sorted(res.signals, key=lambda ts: abs(ts[1].divergence), reverse=True)
    print("=== candidate demo cases (highest |divergence| OOS) ===")
    for token, sig in ranked[: args.top]:
        flag = " [degraded]" if sig.degraded else ""
        print(f"\n{token} {sig.day} dir={sig.direction} |D|={abs(sig.divergence):.2f}{flag}")
        print(f"  {explain(sig)}")


if __name__ == "__main__":
    main()
