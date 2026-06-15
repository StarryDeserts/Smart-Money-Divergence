"""E2 entrypoint: build history from cached frames, run the backtest, print the gate scorecard.
Run: python scripts/run_backtest.py --tokens BTC,ETH,SOL,... [--allow-short]
Prereq: Task 12 spike has populated data/<TOKEN>_frame.parquet."""
import argparse
from divergence.adapters.cmc_client import CMCClient
from divergence.adapters.historical import HistoricalAdapter
from divergence.backtest.harness import run_backtest


def load_history(tokens):
    client = CMCClient()
    adapter = HistoricalAdapter(client)
    history, missing = {}, []
    for t in tokens:
        try:
            history[t] = adapter.history(t)
        except FileNotFoundError:
            missing.append(t)
    if missing:
        print(f"WARNING: no cached frame for {missing} (run scripts/spike_e1_data.py first)")
    return history


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tokens", default="BTC,ETH,SOL,BNB,DOGE")
    ap.add_argument("--allow-short", action="store_true")
    ap.add_argument("--lookback", type=int, default=90)
    ap.add_argument("--theta-quantile", type=float, default=0.8)
    ap.add_argument("--cost-bps", type=float, default=15.0)
    ap.add_argument("--split", type=float, default=0.65)
    args = ap.parse_args()

    history = load_history([t.strip() for t in args.tokens.split(",")])
    if not history:
        raise SystemExit("no usable history — cannot run E2")

    res = run_backtest(history, lookback=args.lookback, theta_quantile=args.theta_quantile,
                       allow_short=args.allow_short, cost_bps=args.cost_bps, split=args.split)

    print("\n=== E2 GATE SCORECARD ===")
    print(f"tokens={list(history)}  theta_abs={res.theta_abs:.3f}  "
          f"days IS/OOS={res.in_sample_days}/{res.oos_days}")
    for label, m in (("IN-SAMPLE", res.is_metrics), ("OUT-OF-SAMPLE", res.oos_metrics),
                     ("OOS BUY&HOLD", res.oos_benchmark)):
        print(f"  {label:13} sharpe={m['sharpe']:+.2f}  total_return={m['total_return']:+.1%}  "
              f"max_dd={m['max_drawdown']:+.1%}  hit={m['hit_rate']:.0%}  turnover={m['turnover']:.1f}")
    print("  attribution (OOS mean signed contribution):")
    for sig, v in sorted(res.attribution.items(), key=lambda kv: -abs(kv[1])):
        print(f"    {sig:18} {v:+.4f}")


if __name__ == "__main__":
    main()
