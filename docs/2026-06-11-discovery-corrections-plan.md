# Discovery + Corrections Plan — BNB Hack (CMC Strategy Skill)

**Date:** 2026-06-11
**Product stage:** New concept (hackathon entry, unvalidated demand)
**Discovery question:** As a BNB Hack **Track 2** project, what must we correct to maximize win probability?

---

## 0. Lens (locked)

- **Optimize for:** *Pure win the hackathon.* The **judging panel + special-prize rubrics are the only customer.**
- **Target real-world user (for the "real-world relevance" scored criterion):** retail trader running their **own AI agent**.
- **Implication:** every decision is judged against the 4 panel criteria (technical execution, originality, real-world relevance, demo) + the Agent Hub / BNB SDK special rubrics + the competitive field — not abstract product success.

---

## 1. Track decision (settled earlier)

- **Track 2 (Strategy Skills, $6k pool, discretionary panel).** Not Track 1 (live PnL) — user will not touch real on-chain trading.
- **Prize ceiling ~$7k, all craft-based:** main 1st $3k + Best Use of Agent Hub $2k + Best Use of BNB SDK $2k (last one downgraded — see C5).
- **Hard deadline:** submit Skill + strategy spec on DoraHacks by **2026-06-21** (end of build window). No on-chain registration, no live-trading window for Track 2.

---

## 2. Concept (v2, corrected)

**A CMC Strategy Skill detecting divergence between crowd sentiment and real capital flow — "smart money vs the crowd."**

- **Hero signal:** CMC on-chain **whale-vs-retail** flow (rare, hard for other teams to replicate). *(F&G demoted to background context — it is commodity data everyone uses.)*
- **Supporting signals:** derivatives funding-rate / OI extremes, F&G, social heat.
- **Thesis:** short-term price = crowd (social / F&G / momentum); medium-term price = where capital is positioned (whale flow, funding). When they disagree, capital usually wins → trade with capital, against the crowd.
- **Value anchor (corrected):** a transparent, reproducible, CMC-data-driven **signal framework + honest evaluation + plain-language explainability** — NOT a "magic PnL" number.
- **Default form:** ONE parameterized strategy authored as a Skill (generation-engine is a stretch option — see C7).

---

## 3. Ideas explored

| Idea | Verdict |
|---|---|
| **A. Sentiment/Capital divergence** ("smart vs dumb money") | **Selected** — best balance of originality × feasibility × demo; lowest backtest-data risk |
| B. Derivatives regime-switching | Parked — more original-systems feel but more parts → harder to make airtight in 10 days |
| C. KOL/news event-driven alpha | Parked — best demo/originality but high history-availability + small-sample risk |

---

## 4. Critical assumptions (Impact × Uncertainty)

| # | Assumption | Category | Impact | Uncertainty | Priority |
|---|---|---|---|---|---|
| A1 | Divergence signal has real edge in an **honest** backtest | Value (core) | High | High | 🔴 leap-of-faith |
| A3 | CMC whale-vs-retail / funding have **usable history** for backtest | Feasibility · data | High | High | 🔴 leap-of-faith |
| A2 | Concept is **differentiated** vs a crowded field | Originality | High | Med-High | 🔴 leap-of-faith |
| A4 | Current scope ships by **6/21** | Feasibility · schedule | High | Med | 🟡 cut scope |
| A6 | Required **"CMC Skill" format** is known | Feasibility | Med | High | 🟡 Day-1 check |
| A5 | **BNB SDK special** winnable without execution (not bolted-on) | Viability · prize | Med | High | 🟡 don't distort core |
| A7 | Demo lands the "aha" (equity curve ≠ story) | Demo | High | Low-Med | 🟢 design choice |
| A8 | Retail+own-agent user would adopt → relevance | Relevance | Med | Med | 🟢 design choice |

---

## 5. Corrections (the answer to "what needs fixing")

- **C1 — Decouple "win" from "strategy is profitable."** The more honest the backtest, the more a marginal edge can evaporate. Re-anchor value on the transparent CMC-driven framework + rigor + explainability, and **anchor the strategy on signals with prior evidence of edge** (funding-rate / F&G extreme mean-reversion) so the backtest shows something real. *(treats A1)*
- **C2 — Make whale-vs-retail the hero, F&G the background.** High-level thesis is shared by the field; differentiation must come from the **rarest CMC-exclusive data**. Also drives Agent Hub depth. *(treats A2)* — contingent on A3.
- **C3 — Day-1 data spike before committing.** Confirm history depth/quality for whale-vs-retail + funding, and the exact CMC Skill format. Keep a fallback ready: if hero signal has no history → backtest on F&G+funding+price, whale-vs-retail becomes live-only + case-study. *(treats A3, A6)*
- **C4 — Cut scope hard.** Daily timeframe, ~20–30 liquid tokens (not 149), one clean walk-forward split, long-short optional. A tight airtight backtest beats a sprawling buggy one. *(treats A4)*
- **C5 — Downgrade the BNB SDK special.** In a no-execution strategy Skill the SDK risks looking cosmetic (panel penalizes that). Don't distort the core for $2k; pursue only if the SDK becomes the genuine agent runtime hosting the Skill. Realistic prize stack = **main + Agent Hub**. *(treats A5)*
- **C6 — Layer the output.** Retail-facing surface = simple, explainable signal ("CAUTION on X — crowd greedy, whales leaving"); quant rigor lives in the repo/report for the technical-execution score. *(treats A7, A8)*
- **C7 — Decision: single strategy vs generator.** Default = single parameterized strategy as a Skill. Upgrade to a lightweight strategy-generation Skill only if chasing a higher ceiling and willing to accept steep schedule risk. *(treats the Quantopian-"generation" framing ambiguity)*

---

## 6. Validation experiments (build-window spikes)

| # | Tests | Method | Success criteria | Effort | When |
|---|---|---|---|---|---|
| E1 | A3 + A6 | Connect CMC Pro/Agent Hub; pull F&G/price/funding/whale-retail history for 5 tokens; identify Skill delivery format | ≥6–12 mo daily history × ≥20 tokens; format known | 0.5–1d | Day 1–2 |
| E2 | A1 | Minimal "is there a pulse" backtest on anchor signals, 20 tokens, daily, costs included | Out-of-sample positive risk-adjusted return (Sharpe > 0.5 or drawdown beats buy&hold), or clearly explainable signal | 1–2d | Day 2–4 |
| E3 | A2 | Scan DoraHacks submissions / TG / past CMC-hackathon winners for how many do F&G/momentum/sentiment | whale-retail/smart-money framing is rare; we have a distinct hook | 0.5d | Day 1–2 (parallel) |
| E4 | A7 | Mine backtest data for 1–2 vivid real cases; script the 3-min demo | ≥1 crisp "crowd said X, whales did Y, then Z" case | 0.5d | Day 7–8 |

**Sequence:** E1 + E3 first (cheap, unblock everything) → **E2 is the go/no-go gate** → full build (Day 4–9) → E4 → buffer + submit (Day 9–10).

---

## 7. Build timeline (2026-06-11 → 06-21)

- **Day 1–2 (6/11–6/13):** E1 data spike + E3 differentiation scan. Lock data plan + Skill format.
- **Day 2–4 (6/13–6/15):** E2 edge smoke-test → **go/no-go gate**.
- **Day 4–9 (6/15–6/20):** Build `signal_core`, backtest harness + report, live CMC Skill, (optional) BNB SDK runtime.
- **Day 7–8:** E4 demo case-mining + script.
- **Day 9–10 (6/20–6/21):** Polish, public repo, demo video, **submit on DoraHacks by 6/21**.

---

## 8. Decision framework

- **E1 fails** (no history) → activate fallback data plan; whale-retail = live-only + case-study.
- **E2 fails** (no edge) → **do NOT proceed to full build**; reframe to decision-support tool (C1) or re-anchor the signal (funding-only / regime).
- **E3 fails** (field is crowded) → escalate differentiation (C7 generator angle, or rarer data combo).

---

## 9. Next steps (pick one)

1. Resume design → fold C1–C7 into a **corrected strategy spec** → implementation plan. *(recommended)*
2. Start the **E1 data spike + E2 edge smoke-test** now (highest-risk, everything depends on it).
3. Write a **PRD** for the corrected concept.
