# Smart-Money Divergence — a CMC Strategy Skill

**Trade with the smart money, against the crowd.**

A backtestable CoinMarketCap Strategy Skill for **BNB Hack — AI Trading Agent
Edition, Track 2**. It flags when **crowd sentiment and real capital flow disagree**
and turns that gap into a long / short / flat bias with a plain-language rationale.

> **This branch (`spike/agent-hub-bnb`) is additive** and targets two special prizes
> on top of the Track-2 Skill — **Best Use of CMC Agent Hub** (a live MCP data
> adapter) and **Best Use of BNB AI Agent SDK** (on-chain ERC-8004 identity + an
> ERC-8183 priced provider). All three reuse the *same pure signal core* — see
> [§ Special-prize verticals](#special-prize-verticals). Baseline `main`
> (`v0.1.0-submission`) is the untouched pure Track-2 entry.

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
the live Skill — so what we backtest is exactly what runs live. The three
special-prize verticals all hang off the *same* core: the live `LiveAdapter` is fed
by **CMC Agent Hub (MCP)**, the layered Skill output is what the **ERC-8183 provider**
sells, and the whole Skill is published under one **ERC-8004 on-chain identity**.

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
# Full suite, incl. the on-chain verticals (adds the BNB AI Agent SDK):
pip install -e ".[dev]" bnbagent && pytest -q   # 98 passed, 1 skipped
python scripts/demo.py BTC                       # live Skill path on one token
python scripts/run_backtest.py --tokens BTC,ETH,SOL,BNB,DOGE   # the gate scorecard
```

The **pure Track-2 core needs no SDK at all** — `pip install -e ".[dev]" && pytest`
runs the signal + backtest tests; the BNB AI Agent SDK (`bnbagent`) adds the
ERC-8004 identity and ERC-8183 provider tests. The one skipped test is a live
BSC-testnet smoke test, gated behind `RUN_LIVE_ERC8183=1`.

## Integrate in your tool

The integration contract is **one method**. Any object with
`trailing_window(token, end, lookback) -> list[Snapshot]` is a valid provider —
plug in your own daily-series data source and call `run_skill`:

```python
from divergence.types import Snapshot
from divergence.skill.runtime import run_skill   # theta_abs defaults to the committed θ

class MyProvider:
    def trailing_window(self, token, end, lookback):
        # Map YOUR daily rows (oldest first) onto Snapshots. Any field may be None;
        # whale_retail_flow is the hero capital axis — omit it and the Skill degrades.
        return [
            Snapshot(token=token, day=r["day"], price=r["price"],
                     whale_retail_flow=r.get("whale_flow"), fear_greed=r.get("fear_greed"))
            for r in my_daily_rows(token)[-lookback:]
        ]

out = run_skill("BTC", MyProvider())
print(out["verdict"], out["detail"]["direction"])   # plain-language + structured
```

**No Python?** `python scripts/cli.py BTC` prints the same `{verdict, detail}` as
**pure JSON on stdout** (human notes go to stderr), so JS/Go/Rust callers can shell
out and parse it: `python scripts/cli.py BTC | jq .detail.direction`.

**Zero-config first run.** With no cached `data/` frame and no key, `demo.py` /
`cli.py` fall back to a `SyntheticProvider` and print a clearly-labelled *degraded*
signal — a fresh clone runs with no setup and never crashes.

## Special-prize verticals

All three reuse the *same* `run_skill` output — no separate model, no
re-implementation. Each states its own honest boundary.

### A · CMC Agent Hub — live MCP data adapter  *(Best Use of CMC Agent Hub)*

`src/divergence/adapters/cmc_mcp.py` talks to the **CoinMarketCap Agent Hub MCP
server** (`https://mcp.coinmarketcap.com/mcp`, streamable HTTP, header-key auth —
**zero-money**, no x402/Base rail). It maps four Hub tools (`get_crypto_quotes_latest`,
`get_crypto_metrics`, `get_global_metrics_latest`, `get_global_crypto_derivatives_metrics`)
onto the Skill's `Snapshot` schema, surfacing the **per-token capital axis** that the
free REST tier paywalls. The Strategy Skill ships an Agent-Hub manifest
([`skill/manifest.json`](skill/manifest.json), entrypoint
`divergence.skill.runtime:run_skill`) returning a retail-facing **verdict** plus a
structured **detail** block (direction, divergence, confidence, ranked drivers,
degraded flag).

```bash
python scripts/demo_mcp.py BTC          # live; reads CMC_PRO_API_KEY from .env.local
```

**Honest scope.** The MCP tier is *latest-only* (no history), so it feeds the live
signal as a Green **ingredient**, not a full Green **verdict** — the backtest still
runs on CMC Pro history. The adapter is real and fail-soft; it never fabricates a
capital score it cannot source.

### B · ERC-8004 on-chain identity  *(BNB AI Agent SDK)*

The Skill is registered as an **ERC-721 agent on BSC testnet (chain 97)** via the
BNB AI Agent SDK (`bnbagent`):

| | |
|---|---|
| Agent | **agentId 1395** — `smart-money-divergence` |
| Owner wallet | [`0x4727165918986b69ff3F94aC1dAa94987B819cfD`](https://testnet.bscscan.com/address/0x4727165918986b69ff3F94aC1dAa94987B819cfD) |
| Registry | `0x8004A818BFB912233c491871b3d84c89A494BD9e` |
| Register tx | [`0x5367a3ae…74fbf8be`](https://testnet.bscscan.com/tx/0x5367a3ae19083fb19fafea8180f08f9e2b589869cbdd859e715cae8c74fbf8be) |
| `setAgentURI` tx | [`0xe4c8b9c1…cb682738`](https://testnet.bscscan.com/tx/0xe4c8b9c1b9fcdcae5aba9057f21749363b618c4f71d2c70f7f2100c2cb682738) |

The on-chain `agentURI` advertises three services — **web, MCP, ERC-8183** — so the
identity points at both the Agent-Hub manifest and the priced provider below.
Registration is gasless-capable (MegaFuel paymaster) but was settled self-paid for a
reliable receipt. Evidence: [`reports/agent_registration.json`](reports/agent_registration.json).

```bash
python scripts/register_agent.py --update-endpoints --dry-run   # safe: prints the planned setAgentURI, sends nothing
```

### C · ERC-8183 priced provider  *(Best Use of BNB AI Agent SDK)*

`src/divergence/adapters/erc8183_provider.py` wraps the Skill as a **payable
ERC-8183 provider**:

- **Signed price negotiation** — quotes a fixed price (1 U) and signs the quote
  (EIP-191 `provider_sig`), bound to chain 97 + the commerce contract to block
  cross-chain replay.
- **On-chain-exact deliverable** — packs a `run_skill` verdict into the canonical
  `DeliverableManifest`; its keccak is the exact `bytes32` that
  `AgenticCommerce.submit` expects, reproducible by any verifier from the manifest
  JSON. Deterministic hash:
  `0x8cb8f20cad17162aaa89bff41bc3d8b7adc2765e0ef09b39b6152400f65d67eb`.
- **Identity binding** — the same agentId 1395 advertises this provider's endpoint
  (the `setAgentURI` tx above).

Contracts (BSC-testnet preset): commerce `0xa206c0517b6371c6638cd9e4a42cc9f02a33b0de`,
router `0xd7d36d66d2f1b608a0f943f722d27e3744f66f25`,
policy `0x4f4678d4439fec812ac7674bb3efb4c8f5fb78a6`.

```bash
python scripts/demo_erc8183.py          # offline, deterministic — the video path
python scripts/serve_erc8183.py --check # validates the SDK wiring offline
```

**Honest scope.** This proves the **provider** half of ERC-8183 — negotiation, the
on-chain-exact deliverable hash, and identity. It does **not** settle a job:
settlement requires the *client* to fund escrow in the U payment token, whose
BSC-testnet `mint` is `onlyOwner` (our wallet holds 0 U). The signed quote and the
manifest hash are real and verifiable; the escrow round-trip (fund → submit →
settle) is out of scope and deliberately not faked.

## Anti-overfit

The edge is not a single lucky setting. Only **~3 knobs** (θ-quantile, lookback,
cost), **one global θ** calibrated on in-sample data only, **causal** trailing
z-scores (a no-look-ahead test tampers the future and asserts the past is
unchanged). A **sensitivity grid** and **leave-one-out** check (drop each token
once) both stay in a tight band and beat buy-&-hold in every cell — see the
[report](reports/backtest_report.md#sensitivity-robustness-across-knobs).

## Scope & honesty

- **No live trading and no real funds.** The Track-2 Skill is a *backtestable signal*,
  judged as quant research, not an execution agent. The special-prize verticals use a
  **testnet-only** wallet for identity + signing — zero real money, no x402/Base rail.
- **Tiered graceful degradation** (Green / Amber / Red). The Skill states its own
  data confidence: when the capital side is absent it says so (`degraded: true`)
  and falls back to crowd-contrarian instead of pretending. The headline backtest is
  **Amber**.
- **The missing alpha is the differentiator.** The on-chain whale-vs-retail axis is
  what lifts this out of the crowded sentiment cluster. A CMC key upgrade unlocks it
  and re-runs the *same* report at the Green tier with **zero code change** (the
  fail-soft adapters are already wired) — the headline pitch is to demo that hero
  signal live.
