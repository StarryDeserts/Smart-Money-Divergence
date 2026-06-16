# Smart-Money Divergence — a CMC Strategy Skill

**Trade with the smart money, against the crowd.**

A backtestable CoinMarketCap Strategy Skill for **BNB Hack — AI Trading Agent
Edition, Track 2**. It flags when **crowd sentiment and real capital flow disagree**
and turns that gap into a long / short / flat bias with a plain-language rationale.

## The thesis

Short-term price is driven by the **crowd** (social heat, Fear & Greed, momentum).
Medium-term price is driven by **capital positioning** — where the *whales* actually
move size (on-chain whale-vs-retail flow, funding / open interest). When the two
diverge — the crowd is euphoric while whales quietly distribute, or the crowd is
fearful while whales accumulate — the capital side tends to win. The Skill scores
both and trades the divergence:

```
D = capital_score − crowd_score        (causal trailing z-scores, no look-ahead)
```

## What's the edge, and how it's validated

Full scorecard: [`reports/backtest_report.md`](reports/backtest_report.md). Run on
365 daily bars × 5 tokens (BTC/ETH/SOL/BNB/DOGE), one in-sample/out-of-sample split,
θ calibrated **in-sample only**.

| Split | Sharpe | Return | Max DD | vs buy&hold |
|---|---|---|---|---|
| Out-of-sample **strategy** | −0.63 | **−4.5%** | **−5.9%** | — |
| Out-of-sample **buy&hold** | −0.84 | −22.9% | −27.5% | benchmark |

**Honest reading (this is the whole point):** on the supplied free CMC key the
capital side — the hero on-chain whale signal — is **unavailable**, so the Skill
runs in a degraded **crowd-contrarian** tier (see [§ Scope](#scope--honesty)). In
that tier the out-of-sample result is **risk reduction, not alpha**: it loses 4.5%
through a broad crypto drawdown where buy-&-hold lost 22.9% (4.7× smaller drawdown,
higher Sharpe) — but its absolute return is still negative. The divergence rule kept
the book *out of trouble*; it did not print money. That honesty is the submission's
spine, not a footnote.

## Architecture

One **pure** `signal_core` is called byte-for-byte by both the offline backtest and
the live Skill — so what we backtest is exactly what runs live.

```
   CMC Pro  ───▶ │ HistoricalAdapter │ ┐
   (history)     └───────────────────┘ │   same
                 ┌───────────────────┐ ├─▶ normalized Snapshot
   Agent Hub ──▶ │ LiveAdapter       │ ┘        │
   (MCP, live)   └───────────────────┘          ▼
                              ┌────────────────────────────┐
                              │ signal_core  (PURE)        │
                              │  Snapshot → Signal          │
                              │  D = capital − crowd,       │
                              │  direction, confidence,     │
                              │  structured rationale       │
                              └────────────────────────────┘
                                   │                    │
                                   ▼                    ▼
                        ┌────────────────────┐  ┌────────────────────┐
                        │ backtest_harness   │  │ skill_runtime      │
                        │ positions+costs,   │  │ live signal → the  │
                        │ metrics, report    │  │ layered output     │
                        └────────────────────┘  └────────────────────┘
                                   └────────┐  ┌────────┘
                                            ▼  ▼
                                   ┌────────────────────┐
                                   │ explain (shared)   │
                                   │ rationale → plain  │
                                   │ language           │
                                   └────────────────────┘
```

## Quickstart

```bash
pip install -e ".[dev]" && pytest -q          # 63 tests, all green
python scripts/demo.py BTC                     # live Skill path on one token
python scripts/run_backtest.py --tokens BTC,ETH,SOL,BNB,DOGE   # the gate scorecard
```

## Anti-overfit

The edge is not a single lucky setting. Only **~3 knobs** (θ-quantile, lookback,
cost), **one global θ** calibrated on in-sample data only, **causal** trailing
z-scores (a no-look-ahead test tampers the future and asserts the past is
unchanged). A **sensitivity grid** and **leave-one-out** check (drop each token
once) both stay in a tight band and beat buy-&-hold in every cell — see the
[report](reports/backtest_report.md#sensitivity-robustness-across-knobs).

## Scope & honesty

- **No live trading, no wallets, no funds.** This is Track 2 by design — a
  *backtestable signal Skill*, judged as quant research, not an execution agent.
- **Tiered graceful degradation** (Green / Amber / Red). The Skill states its own
  data confidence: when the capital side is absent it says so (`degraded: true`)
  and falls back to crowd-contrarian instead of pretending. This run is **Amber**.
- **The missing alpha is the differentiator.** The on-chain whale-vs-retail axis is
  what lifts this out of the crowded sentiment cluster. A CMC key upgrade unlocks it
  and re-runs the *same* report at the Green tier with **zero code change** (the
  fail-soft adapters are already wired) — the headline pitch is to demo that hero
  signal live.

## Track 2 + Agent Hub

A CMC Strategy Skill with an Agent-Hub manifest at
[`skill/manifest.json`](skill/manifest.json) (`entrypoint:
divergence.skill.runtime:run_skill`). Returns the layered output the Hub surfaces:
a retail-facing **verdict** string plus a structured **detail** block (direction,
divergence, confidence, ranked drivers, degraded flag).

## Vertical C — ERC-8183 priced provider (Best Use of BNB AI Agent SDK)

Building on the shipped Vertical A (ERC-8004 on-chain identity, agentId 1395) and
Vertical B (CMC Agent Hub MCP live-data adapter), the Smart-Money Divergence Skill
is wrapped as a payable ERC-8183 provider:

- **Signed price negotiation** — `make_negotiation_handler` returns a seller-side
  `NegotiationHandler` that quotes a fixed price (1 U) and signs the quote
  (EIP-191 `provider_sig`), bound to chain 97 + the commerce contract to block
  cross-chain replay.
- **On-chain-exact deliverable** — `build_deliverable_manifest` packages a
  `run_skill` verdict into the canonical `DeliverableManifest`; its keccak is the
  exact `bytes32` that `AgenticCommerce.submit` expects, reproducible by any
  verifier from the manifest JSON.
- **Identity binding** — `register_agent.py --update-endpoints` advertises the
  ERC-8183 endpoint on the existing ERC-8004 identity (agentId 1395) via the
  registry's `setAgentURI`.
- **Runnable provider** — `scripts/serve_erc8183.py` wires the Skill into the
  SDK's `create_erc8183_app`; `--check` validates the wiring offline.

Try it (offline, deterministic):

```bash
python scripts/demo_erc8183.py
```

**Honest scope.** This proves the *provider* half of ERC-8183 — negotiation, the
on-chain-exact deliverable hash, and identity. It does **not** settle a job:
settlement requires the *client* to fund the escrow in the U payment token, whose
BSC-testnet `mint` is `onlyOwner` (our wallet holds 0 U). The signed quote and the
manifest hash are real and verifiable; the escrow round-trip (fund → submit →
settle) is out of scope and deliberately not faked.
