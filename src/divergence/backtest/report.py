from __future__ import annotations
from pathlib import Path


def _metrics_row(label, m):
    return (f"| {label} | {m['sharpe']:+.2f} | {m['total_return']:+.1%} | "
            f"{m['max_drawdown']:+.1%} | {m['hit_rate']:.0%} | {m['turnover']:.1f} | {m['n_days']} |")


def render_report(result, *, sensitivity=None, notes: str = "") -> str:
    lines = ["# Divergence Strategy — Backtest Report", "",
             f"**θ (abs divergence threshold):** {result.theta_abs:.3f}  ",
             f"**Days (in-sample / out-of-sample):** {result.in_sample_days} / {result.oos_days}",
             "", "## Performance", "",
             "| Split | Sharpe | Return | Max DD | Hit | Turnover | Days |",
             "|---|---|---|---|---|---|---|",
             _metrics_row("In-sample", result.is_metrics),
             _metrics_row("Out-of-sample", result.oos_metrics),
             _metrics_row("OOS buy&hold", result.oos_benchmark), "",
             "_Headline = OOS strategy vs OOS buy&hold (risk-adjusted)._", "",
             "## Signal attribution (OOS mean signed contribution)", ""]
    for sig, v in sorted(result.attribution.items(), key=lambda kv: -abs(kv[1])):
        lines.append(f"- `{sig}`: {v:+.4f}")
    if sensitivity:
        lines += ["", "## Sensitivity (robustness across knobs)", "",
                  "| θ-quantile | lookback | cost(bps) | OOS Sharpe | OOS Return |",
                  "|---|---|---|---|---|"]
        for r in sensitivity:
            lines.append(f"| {r['theta_quantile']} | {r['lookback']} | {r['cost_bps']} | "
                         f"{r['oos_sharpe']:+.2f} | {r['oos_return']:+.1%} |")
    if notes:
        lines += ["", "## Honest limitations", "", notes]
    return "\n".join(lines) + "\n"


def write_report(result, path="reports/backtest_report.md", *, sensitivity=None, notes="") -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(render_report(result, sensitivity=sensitivity, notes=notes), encoding="utf-8")
    return p
