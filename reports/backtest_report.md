# Divergence Strategy — Backtest Report

**θ (abs divergence threshold):** 1.444  
**Days (in-sample / out-of-sample):** 237 / 128

## Performance

| Split | Sharpe | Return | Max DD | Hit | Turnover | Days |
|---|---|---|---|---|---|---|
| In-sample | +0.92 | +6.5% | -2.1% | 36% | 9.6 | 237 |
| Out-of-sample | -0.63 | -4.5% | -5.9% | 20% | 2.0 | 128 |
| OOS buy&hold | -0.84 | -22.9% | -27.5% | 46% | 1.0 | 128 |

_Headline = OOS strategy vs OOS buy&hold (risk-adjusted)._

## Signal attribution (OOS mean signed contribution)

- `momentum`: +0.0002
- `fear_greed`: +0.0002

## Sensitivity (robustness across knobs)

| θ-quantile | lookback | cost(bps) | OOS Sharpe | OOS Return |
|---|---|---|---|---|
| 0.7 | 60 | 15.0 | -1.34 | -11.8% |
| 0.7 | 90 | 15.0 | -0.98 | -8.4% |
| 0.8 | 60 | 15.0 | -0.95 | -7.8% |
| 0.8 | 90 | 15.0 | -0.63 | -4.5% |
| 0.9 | 60 | 15.0 | -0.77 | -4.9% |
| 0.9 | 90 | 15.0 | -0.36 | -2.2% |

## Honest limitations

**Tier: AMBER (framework-first per spec C1).** The free CMC key exposes no capital side (on-chain whale-vs-retail flow and funding/OI are unavailable), so the rule runs in degraded **crowd-contrarian** mode `D = -crowd_score` over price + fear&greed + momentum. Treat the value here as the *honest, validated framework*, not headline PnL.

**The OOS edge is risk reduction, not alpha.** Out-of-sample the strategy returns -4.5% vs buy&hold's -22.9% over the same broad crypto drawdown — 4.7x smaller max drawdown (-5.9% vs -27.5%) and higher Sharpe (-0.63 vs -0.84) — but its absolute return is still negative. The divergence rule kept the book *out of trouble*; it did not generate positive return on this key.

**It is not a single lucky setting (anti-overfit).** Across the whole sensitivity grid OOS return stays in -11.8%..-2.2% and every cell beats the -22.9% benchmark; OOS improves monotonically with a tighter threshold (q=0.9) and longer lookback (90d). Leave-one-out is tight: dropping any single token holds OOS Sharpe in -0.72..-0.51 and OOS return in -5.7%..-3.6% — no one name drives the result. One global in-sample-only theta, causal trailing z-scores, ~3 knobs.

**The missing alpha is the differentiator.** Attribution carries only momentum + fear&greed (both ~0); there is no hero `whale_retail_flow` term because it is absent in Amber. Restoring the on-chain whale axis (a CMC key upgrade re-runs this report at the Green tier with zero code change — the fail-soft extractors are already wired) is what would turn defensive risk-reduction into a real smart-money-vs-crowd edge.
