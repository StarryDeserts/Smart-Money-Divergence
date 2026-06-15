# Submission checklist — BNB Hack Track 2

**Deadline:** submit on **DoraHacks by 2026-06-21**. (Hard gate — everything below
must be green before pushing public + submitting.)

## What ships

- **Repo (public):** the GitHub URL — push `master` and confirm the tree is
  legible top-down. Judge reads the README first.
- **Report (evidence):** `reports/backtest_report.md` — committed, NOT gitignored.
- **Demo:** `python scripts/demo.py BTC` (offline-safe via cached frames) +
  `python scripts/run_backtest.py --tokens BTC,ETH,SOL,BNB,DOGE` for the scorecard.
- **Skill manifest:** `skill/manifest.json` (`entrypoint:
  divergence.skill.runtime:run_skill`).
- **Demo video link (if DoraHacks requires one):** TODO — record the 90-second
  run (README hook → `demo.py` verdict → `run_backtest.py` scorecard → the honest
  Amber framing). _Confirm whether a video is mandatory for Track 2._

## DoraHacks form fields (fill at submit time)

- Project name: **Smart-Money Divergence**
- Track: **Track 2 — Strategy Skills** (CMC × Trust Wallet × BNB Chain).
- One-liner: "Trade with the smart money, against the crowd — a backtestable CMC
  divergence Skill."
- Repo URL: TODO (post-push).
- Special prize box: **Best Use of CMC Agent Hub** — manifest + layered output wired
  for the Hub. (Check any other applicable prize boxes at submit time.)

## Honesty framing (lead with this — per spec C1)

This run is **Amber**: the free CMC key has no capital/whale side, so the Skill runs
crowd-contrarian. Out-of-sample it is **defensive risk-reduction** (−4.5% vs
buy&hold −22.9%), **not alpha**. Value = the honest, causal, byte-for-byte
backtested **framework** + the whale-axis differentiator demoed live. Do not
overclaim PnL. See [E2 gate](2026-06-12-e2-gate.md) and
[differentiation scan](2026-06-12-e3-differentiation.md).

## Final pre-submit gate

- [ ] `pytest -q` — all green (currently **63 passed**).
- [ ] `reports/backtest_report.md` committed and current.
- [ ] `python scripts/demo.py BTC` runs clean (no traceback).
- [ ] `python scripts/run_backtest.py` prints the gate scorecard.
- [ ] README renders top-down: hook → thesis → edge+validation → architecture →
      quickstart → anti-overfit → scope/honesty → Track 2/Agent Hub.
- [ ] `docs/superpowers/specs/` + `docs/superpowers/plans/` committed (GitHub link
      needs them visible).
- [ ] Tag `v0.1.0-submission`.
- [ ] **Push public + submit on DoraHacks** (shared-state action — confirm with the
      human before pushing).
