# Smart-Money Divergence — CMC Strategy Skill (Design Spec)

**Date:** 2026-06-12
**Status:** Design approved (sections ①–⑤), ready for implementation planning
**Event:** BNB Hack: AI Trading Agent Edition — **Track 2 (Strategy Skills)**
**Submit by:** 2026-06-21 on DoraHacks
**Companion docs:** [`../../2026-06-11-discovery-corrections-plan.md`](../../2026-06-11-discovery-corrections-plan.md) (discovery + corrections C1–C7, assumption matrix, validation experiments)

---

## 1. Summary

A CMC Strategy Skill that detects **divergence between crowd sentiment and real capital flow** — "smart money vs the crowd." The **hero signal is CMC on-chain whale-vs-retail flow** (rare, hard to replicate); F&G, funding-rate, social heat, and momentum are supporting/background context. When the crowd is positioned one way and patient capital the other, capital usually wins over the medium term → the strategy trades **with capital, against the crowd**, and acts only at divergence extremes (where funding/F&G mean-reversion has prior documented edge).

The deliverable is **one parameterized strategy authored as a Skill**, backed by a pure-function core that is **shared byte-for-byte between an offline backtest and the live Skill**, so the honest evaluation we publish provably reflects what the Skill does live.

**What this project is optimized for:** winning the hackathon. The judging panel + special-prize rubrics are the customer. The "real-world user" we design the surface for (because *real-world relevance* is a scored criterion) is a **retail trader running their own AI agent**.

**The value we sell judges is not a magic PnL number.** It is a transparent, reproducible, CMC-data-driven **signal framework + honest evaluation + plain-language explainability**. Reporting a stable, modest, rigorously-measured edge beats claiming a suspicious one — judges in a trading track know the difference.

---

## 2. Goals & non-goals

### Goals
- A single, parameterized, explainable divergence strategy delivered as a CMC Skill.
- An **honest, reproducible backtest** whose code path is identical to the live Skill.
- A **layered output**: a plain-language retail verdict on top, full quant detail underneath.
- Win the **main Track 2 prize**; credibly contend for **Best Use of Agent Hub**.

### Non-goals
- **No real on-chain trading, no live funds, no wallet/execution.** (This is why we are in Track 2, not Track 1.)
- No high-frequency / intraday execution — daily timeframe only.
- No sprawling universe — ~20–30 liquid tokens, not the full market.
- No per-token parameter tuning, no strategy "zoo." One strategy, a handful of honest knobs.
- BNB AI Agent SDK is **not** a goal unless it becomes the genuine runtime hosting the Skill (see §9, C5).

---

## 3. Concept (v2, corrected)

- **Hero signal:** CMC on-chain **whale-vs-retail** flow. This is the differentiator; the high-level "smart vs dumb money" thesis is shared by the field, so the edge has to come from the rarest CMC-exclusive data.
- **Supporting signals:** derivatives funding-rate / OI extremes, F&G (market-wide background), social heat, short-term momentum.
- **Thesis:** short-term price ≈ the crowd (social / F&G / momentum); medium-term price ≈ where capital is positioned (whale flow, funding). When they disagree, capital usually wins → trade with capital.
- **Form:** ONE parameterized strategy as a Skill. A strategy-*generation* engine is an explicit stretch option, not the default (C7).

---

## 4. Architecture & module boundaries (Section ①)

The spine: **one pure-function `signal_core` that both the backtest and the live Skill call**, so what we backtest is byte-for-byte what runs live. That property is the credibility foundation — if judges trust nothing else, they should trust that the evaluation reflects the Skill.

```
                 ┌─────────────────────────────┐
   CMC Pro  ───▶ │ HistoricalAdapter           │ ┐
   (history)     └─────────────────────────────┘ │   same
                 ┌─────────────────────────────┐ ├─▶ normalized
   Agent Hub ──▶ │ LiveAdapter                 │ ┘   Snapshot
   (MCP, live)   └─────────────────────────────┘        │
                                                         ▼
                                        ┌────────────────────────────┐
                                        │ signal_core  (PURE)        │
                                        │  Snapshot -> Signal         │
                                        │  D = capital − crowd,       │
                                        │  direction, confidence,     │
                                        │  structured rationale       │
                                        └────────────────────────────┘
                                             │                    │
                              ┌──────────────┘                    └─────────────┐
                              ▼                                                  ▼
                   ┌────────────────────┐                          ┌────────────────────┐
                   │ backtest_harness   │                          │ skill_runtime      │
                   │ positions+costs,   │                          │ live signal -> the │
                   │ metrics, report,   │                          │ layered output     │
                   │ demo cases         │                          │                    │
                   └────────────────────┘                          └────────────────────┘
                              └──────────────┐      ┌───────────────┘
                                             ▼      ▼
                                        ┌────────────────────┐
                                        │ explain (shared)   │
                                        │ rationale -> plain │
                                        │ language           │
                                        └────────────────────┘
```

**Module responsibilities (one job each):**

| Module | Job | Depends on |
|---|---|---|
| **`signal_core`** | Pure, no I/O, no clock. `Snapshot → Signal`. Deterministic, unit-testable. The only place strategy logic lives. | nothing (pure) |
| **`data_adapters`** | Two impls of one interface, both emitting the identical `Snapshot` schema. `HistoricalAdapter` (CMC Pro) for backtest; `LiveAdapter` (Agent Hub MCP) for the Skill. **The C3 data risk is quarantined here.** | CMC Pro / Agent Hub MCP |
| **`backtest_harness`** | Drives history through `signal_core`, simulates positions with costs, emits metrics + report + demo cases. | `signal_core`, `HistoricalAdapter`, `explain` |
| **`skill_runtime`** | CMC Skill entry point: `LiveAdapter → signal_core → explain → layered output`. | `signal_core`, `LiveAdapter`, `explain` |
| **`explain`** | Shared formatter: structured rationale → plain language. Used by both the report and the live Skill so they tell the *same* story. | nothing (pure formatter) |

**Why this shape wins:** the riskiest unknown (data history) is sealed behind one interface, and the credibility claim (backtest == live) is structural, not a promise.

---

## 5. Signal logic (Section ②)

### Inputs — `Snapshot` (per token, per day)
`whale_retail_flow`, `funding_rate`, `open_interest`, `fear_greed`, `social_heat`, `price` (for momentum/returns). Every field nullable.

Each input is converted to a **causal trailing z-score** vs a rolling ~90-day window, computed **only from past data** (no look-ahead). Z-scores make unlike signals comparable and keep the logic unit-free. Cross-sectional rank across the ~25-token universe is the robustness alternative.

### Two composites
- **`capital_score`** — where *patient* money sits. Driven by the **hero signal, whale-vs-retail flow** (C2). High = whales accumulating. Kept to one clean signal — no overfit blending.
- **`crowd_score`** — where the *leveraged/emotional* crowd sits. Equal-weight blend of standardized **F&G (background), social heat, short-term momentum, and funding-rate / OI crowding**. High = crowd greedy / longs over-crowded.

### Divergence & direction
`D = capital_score − crowd_score`

| D | Reading | Action |
|---|---|---|
| **D ≫ 0** | whales accumulating *into* crowd fear | **long** (smart money buying the fear) |
| **D ≪ 0** | whales distributing *into* crowd greed | **short / flat** (smart money selling the greed) |
| D ≈ 0 | aligned, no edge | flat |

### Decision rule (edge-anchored, C1)
Act **only at extremes** — enter when `|D|` exceeds **θ**, where **θ is a percentile of historical |D| (e.g. top quintile), not a hand-tuned number per token.** Extreme funding / extreme F&G have *prior documented mean-reversion*, so leaning on the tails is where a real, explainable edge most plausibly lives — and "only the strongest 20% of divergences" is a story a judge immediately gets.

- Size ∝ `|D|` (capped).
- Daily rebalance.
- Long-only by default; long-short as one parameter (C4).

### Missing-data behavior (this *is* the fallback mechanism)
`signal_core` has one defined degradation path, so the §6 data fallback needs **no separate code branch** — it is just the core reacting to null fields:
- **`crowd_score`** is the mean over its *available* standardized inputs. It is a genuine multi-signal composite, so dropping one input (e.g. `social_heat = None`) simply renormalizes the average over the rest.
- **`capital_score`** is the single hero and has **no proxy**. If `whale_retail_flow` is null, the capital side is unavailable.
- **Both sides present** → `D = capital_score − crowd_score` (full divergence).
- **Capital side unavailable, crowd present** → degrade to **crowd-extreme contrarian**: `D = −crowd_score`, act on crowd tails only, **confidence capped + flagged.** This mode is honestly labeled as mean-reversion, not pretend-divergence — and it is exactly the funding / F&G tail edge C1 anchors on.
- **Crowd side unavailable** → flat (this strategy does not trade on the capital side alone).

### Anti-overfit posture (the credibility win)
The whole strategy is **~3 honest knobs** — lookback window, θ percentile, long-only vs long-short. Equal-weight composites, one global θ, no per-token tuning. Even if the *divergence* edge is marginal, the funding/F&G tails it rests on have known mean-reversion, so the backtest shows something real rather than curve-fit noise. **This is exactly the E2 go/no-go bet.**

---

## 6. Data layer & fallback ladder (Section ③)

### The `Snapshot` contract (both adapters emit this; every field nullable)
```
Snapshot { token, date, price,
           whale_retail_flow?,   # hero, per-token
           funding_rate?, open_interest?,   # per-token (perps)
           social_heat?,         # per-token
           fear_greed? }         # MARKET-WIDE (one number/day, broadcast)
```
Honest modeling note: **F&G is a market-wide index, not per-token** — which reinforces C2 (F&G = background; the per-token *hero* is whale-vs-retail).

### `HistoricalAdapter` (backtest) — endpoint risk map
| Field | Source | History confidence |
|---|---|---|
| price / OHLCV | CMC Pro historical | ✅ solid, long |
| fear_greed | CMC `fear_and_greed/historical` | ✅ confirmed |
| funding / OI | CMC derivatives → **Binance funding history** as fallback | 🟡 Binance is the safety net |
| social_heat | CMC community/social historical | 🟡 uncertain |
| **whale_retail_flow** | CMC on-chain / address-distribution | 🔴 **hero, and riskiest for history (A3)** |

### `LiveAdapter` (Skill)
Agent Hub MCP, all current-snapshot. Low risk: live values are exposed even where *history* isn't.

### Fallback ladder (C3) — and why it costs almost no new code
1. **Green (E1 best case):** all signals have ≥6–12 mo daily history → full backtest *with* the hero included.
2. **Amber (most likely):** price + F&G + funding (Binance) have history but whale-retail is thin → the **backtest runs in the degraded crowd-extreme contrarian mode** (§5), honestly labeled as mean-reversion; **the hero goes live-only.** `signal_core` just sees `whale_retail_flow = None` and takes its defined degradation path (confidence capped + flagged). The full divergence version runs live in the Skill + ships as a documented case study.
3. **Red (E1 worst case):** anchor the backtest purely on funding + F&G *extremes* (known mean-reversion, good history); whale-retail is presented entirely as a live differentiator with case studies.

Because the core has one defined degradation path for `None` (§5), **the fallback is not a code branch — it's just the adapter emitting nulls.** That is the payoff of the §4 boundary.

### Reproducibility details (credibility, C1/C6)
- Adapters **cache pulled history to local parquet/csv**, so the backtest re-runs offline, deterministically, without judges needing API keys or hitting rate limits.
- The **~25-token universe is selected once by liquidity at the *start* of the window** (not the end) and documented — avoids survivorship / look-ahead cherry-picking.

---

## 7. Backtest harness & honest evaluation (Section ④)

### One clean walk-forward split (C4)
Timeline cut once: in-sample (first ~65%) is the *only* place θ-percentile and the lookback window are chosen; out-of-sample (last ~35%) is touched **once**, and its number is the headline. No peeking at OOS to tune anything — that single discipline is what makes the result trustworthy.

### Position simulation (no look-ahead, costs real)
- Signal computed from data **up to day t** → position taken at **t+1 open**. Never act on same-bar info. (This is the most common silent backtest cheat; we structurally forbid it.)
- Transaction costs **included** (~10–20 bps/side fee+slippage, realistic for the liquid universe). The edge must survive friction — the E2 bar.
- Daily rebalance, size ∝ `|D|` capped, long-only default.

### Metrics — risk-adjusted, vs a real benchmark (not vs zero)
- **OOS Sharpe** + **max drawdown vs equal-weight buy&hold of the same universe** → this pair *is* the E2 go/no-go gate.
- Hit rate, avg win/loss, **turnover** (proves it's not over-trading).
- **Per-signal attribution: hero (whale-retail) vs crowd composite** — tests whether the hero earns its billing (C2); also a strong demo artifact.

### Robustness checks (cheap, the real anti-cherry-pick proof)
- **θ / lookback sensitivity grid** — report the *distribution* of outcomes across nearby parameters, not the single best cell. Flat surface ⇒ stable edge; spiky ⇒ overfit. We show whichever it is.
- **Subsample stability** — does it hold in more than one period/regime.

### Report artifacts (the C6 repo-rigor layer)
OOS equity curve, metrics table, attribution chart, sensitivity heatmap, and the mined demo cases (E4) — emitted as a reproducible, committed report.

### Negative-result posture (C1, important)
The harness reports the **truth even if the edge is marginal.** Its design does not change with the outcome — it just measures. If OOS edge is weak, we pivot the *framing* to honest decision-support, not a faked number.

---

## 8. Live Skill output, explainability & testing (Section ⑤)

### `skill_runtime` — the Skill a retail agent calls
Input: a token or watchlist (+ optional params). Flow: `LiveAdapter → signal_core → explain → layered output`. The output is layered per C6:

- **Layer 1 — retail-facing verdict (simple, one breath):**
  > ⚠️ **CAUTION · SOL** — crowd is greedy (F&G 82, social hot, longs crowded) but whales have net-distributed 3 days running. Divergence in the **top decile** → smart money is selling into the greed. **Bias: reduce / short.**
- **Layer 2 — structured detail (machine + quant judge):** the full `Signal` — `D`, `capital_score`, `crowd_score`, per-component z-scores, confidence, and **data-completeness flags** — consumable by a downstream agent or inspected by a technical judge.

### `explain` — one formatter, two surfaces
The same `explain` module renders both the live verdict *and* the historical case annotations in the report. The story a user hears live is generated by the identical code that narrated the demo cases — demo and product can't drift apart. To keep `signal_core` pure, the core returns a **structured rationale** (a ranked list of drivers like `{signal: whale_retail_flow, z: −1.8, side: capital, label: "whales distributing"}`), and `explain` is a thin deterministic template over the top-k drivers.

### Testing strategy (proportionate — tests as *proof*, not hygiene theater)
| Target | Tests | What it proves |
|---|---|---|
| **`signal_core`** (pure → test hard) | golden Snapshots → asserted D sign/direction; aligned/all-flat → flat, no div-by-zero; **`whale_retail_flow=None` → degrades to crowd-contrarian + confidence flagged**; a missing crowd input → `crowd_score` renormalizes over the rest | core logic + that the **C3 fallback actually works** |
| **`backtest_harness`** | **look-ahead guard:** inject a future spike, assert today's signal is unmoved; cost round-trip deducts expected bps; cached data → identical re-run | the **no-look-ahead + reproducibility** claims |
| **`data_adapters`** | both adapters emit schema-valid identical `Snapshot` shape (network mocked) | **backtest == live** equivalence at the boundary |
| **`explain`** | structured rationale → expected sentence | demo/live narrative consistency |

TDD weight lands on `signal_core` and the **look-ahead guard** on purpose: those two tests are the literal evidence for our two central claims (honest evaluation, graceful fallback). We deliberately *don't* test CMC's data correctness — a trusted boundary, not our code.

---

## 9. How the design embodies corrections C1–C7

| Correction | Where it lives in this design |
|---|---|
| **C1** decouple "win" from "profitable" | §1 value anchor; §5 edge-anchored rule on funding/F&G tails; §7 negative-result posture |
| **C2** whale-vs-retail = hero, F&G = background | §3 concept; §5 `capital_score` = hero only; §6 F&G market-wide note; §7 per-signal attribution |
| **C3** Day-1 data spike + fallback | §6 fallback ladder; §10 E1 + decision framework |
| **C4** cut scope | §2 non-goals; §5 daily/long-only/~3 knobs; §7 one walk-forward split; ~25 tokens |
| **C5** downgrade BNB SDK | §2 non-goals; below |
| **C6** layer the output | §8 Layer 1 / Layer 2; §7 repo-rigor report |
| **C7** single strategy vs generator | §3 single strategy default; generator = explicit stretch |

**BNB SDK (C5):** pursue *only* if the BNB AI Agent SDK becomes the genuine runtime that **hosts** `skill_runtime` — never bolted on. Otherwise skip. Realistic prize stack stays **main + Agent Hub**.

---

## 10. Open risks & the go/no-go gate

The riskiest assumption is **A1 — does the divergence signal have real edge in an honest backtest.** This design is built to *measure* that truthfully rather than assume it. Validation experiments (full detail in the discovery doc):

| # | Tests | Gate |
|---|---|---|
| **E1** | data history depth/quality + Skill format | unblocks everything; picks fallback tier |
| **E2** | minimal honest backtest on anchor signals | **GO/NO-GO** — OOS Sharpe > 0.5 or drawdown beats buy&hold, or clearly explainable signal |
| **E3** | differentiation scan of the field | escalate hook if crowded |
| **E4** | mine 1–2 vivid demo cases | ≥1 crisp "crowd said X, whales did Y, then Z" |

**Decision framework:**
- **E1 fails** → activate fallback data plan; whale-retail = live-only + case study.
- **E2 fails** → do **not** proceed to full build; reframe to decision-support (C1) or re-anchor the signal (funding-only / regime).
- **E3 fails** → escalate differentiation (rarer data combo, or the C7 generator angle).

---

## 11. Build timeline (2026-06-12 → 06-21)

- **Day 1–2:** E1 data spike + E3 differentiation scan. Lock data plan + Skill format.
- **Day 2–4:** E2 edge smoke-test → **go/no-go gate**.
- **Day 4–9:** Build `signal_core`, `data_adapters`, `backtest_harness` + report, `skill_runtime` live Skill, (optional) BNB SDK host.
- **Day 7–8:** E4 demo case-mining + 3-min script.
- **Day 9–10:** Polish, public repo, demo video, **submit on DoraHacks by 6/21**.

---

## 12. Out of scope / future

- Strategy-generation engine (C7 stretch).
- Intraday / HFT timeframes.
- Full-market universe.
- Live execution / wallet integration (structurally excluded — Track 2).
- Multi-strategy portfolio construction.
