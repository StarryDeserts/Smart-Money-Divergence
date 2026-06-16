# Special-prize submission — Smart-Money Divergence

**Date:** 2026-06-16
**Branch:** `spike/agent-hub-bnb` (additive; baseline `main` = `v0.1.0-submission`)
**Repo:** https://github.com/StarryDeserts/Smart-Money-Divergence
**Targets:** Best Use of CMC Agent Hub · Best Use of BNB AI Agent SDK
**Deadline:** 2026-06-21 (demo video mandatory)

---

## One-paragraph pitch

Smart-Money Divergence is a backtestable CoinMarketCap Strategy Skill (BNB Hack
Track 2) that flags when crowd sentiment and real whale-vs-retail capital flow
disagree, and turns the gap into a long/short/flat bias with a plain-language
rationale. On top of the shipped Skill, this branch adds three on-chain / Agent-Hub
verticals — **all driven by the same pure `run_skill` core** — to compete for two
special prizes: a live **CMC Agent Hub MCP** data adapter, an **ERC-8004 on-chain
identity** (agentId 1395 on BSC testnet), and an **ERC-8183 priced provider** that
signs quotes and emits the exact on-chain deliverable hash.

## The three pillars (with proof)

### A · CMC Agent Hub — live MCP adapter  *(Best Use of CMC Agent Hub)*
- **Code:** `src/divergence/adapters/cmc_mcp.py`
- **Transport:** real MCP, streamable HTTP, `https://mcp.coinmarketcap.com/mcp`,
  header-key auth (`X-CMC-MCP-API-KEY`). **Zero money** — deliberately *not* the
  x402/Base-mainnet rail (declined: "zero-money, MCP only").
- **What it does:** maps 4 Hub tools (`get_crypto_quotes_latest`,
  `get_crypto_metrics`, `get_global_metrics_latest`,
  `get_global_crypto_derivatives_metrics`) onto the Skill `Snapshot`, surfacing the
  per-token capital axis the free REST tier paywalls.
- **Run:** `python scripts/demo_mcp.py BTC` (reads `CMC_PRO_API_KEY` from `.env.local`).
- **Honest scope:** MCP tier is latest-only → a Green **ingredient**, not a Green
  **verdict**. Backtest still runs on CMC Pro history. Fail-soft; never fabricates.

### B · ERC-8004 on-chain identity  *(BNB AI Agent SDK)*
- **Agent:** agentId **1395** (`smart-money-divergence`), chain 97 (BSC testnet).
- **Owner wallet:** `0x4727165918986b69ff3F94aC1dAa94987B819cfD`
- **Registry:** `0x8004A818BFB912233c491871b3d84c89A494BD9e`
- **Register tx:** `0x5367a3ae19083fb19fafea8180f08f9e2b589869cbdd859e715cae8c74fbf8be`
- **setAgentURI tx:** `0xe4c8b9c1b9fcdcae5aba9057f21749363b618c4f71d2c70f7f2100c2cb682738`
- **Advertises services:** `web`, `MCP`, `ERC-8183` (decoded from the on-chain
  `agentURI`) — the identity points at both the Agent-Hub manifest and the priced
  provider.
- **Evidence:** `reports/agent_registration.json` (tracked).
- **Safe demo:** `python scripts/register_agent.py --update-endpoints --dry-run`.

### C · ERC-8183 priced provider  *(Best Use of BNB AI Agent SDK)*
- **Code:** `src/divergence/adapters/erc8183_provider.py`
- **Signed negotiation:** fixed price (1 U), EIP-191 `provider_sig`, bound to chain
  97 + commerce contract (anti-replay).
- **On-chain-exact deliverable:** `DeliverableManifest` keccak = the `bytes32`
  `AgenticCommerce.submit` expects. Deterministic hash
  `0x8cb8f20cad17162aaa89bff41bc3d8b7adc2765e0ef09b39b6152400f65d67eb`.
- **Contracts (BSC-testnet preset):** commerce
  `0xa206c0517b6371c6638cd9e4a42cc9f02a33b0de`, router
  `0xd7d36d66d2f1b608a0f943f722d27e3744f66f25`, policy
  `0x4f4678d4439fec812ac7674bb3efb4c8f5fb78a6`.
- **Run:** `python scripts/demo_erc8183.py` (offline, deterministic) ·
  `python scripts/serve_erc8183.py --check` (offline wiring check).
- **Honest scope:** **provider half only**. Settlement needs the client to fund
  escrow in the U token (testnet `mint` is `onlyOwner`; our wallet holds 0 U).
  Quote + manifest hash are real; the fund→submit→settle round-trip is out of scope
  and not faked.

## Test suite

- Full suite (with the BNB AI Agent SDK in a venv): **98 passed, 1 skipped**.
  - `pip install -e ".[dev]" bnbagent && pytest -q`
  - 1 skipped = `tests/test_erc8183_provider.py::test_live_kernel_binding_smoke`
    (gated behind `RUN_LIVE_ERC8183=1`).
- Pure Track-2 core (no SDK): `pip install -e ".[dev]" && pytest` — signal +
  backtest tests only.

## Video script (~2.5 min, offline-safe path)

1. **Hook (15s).** "Trade with the smart money, against the crowd." Show the thesis:
   crowd vs capital divergence → long/short/flat.
2. **The Skill (30s).** `python scripts/demo.py BTC` → the layered verdict + detail
   block. Note the Amber honesty (degraded flag when the capital side is paywalled).
3. **Backtest gate (25s).** `reports/backtest_report.md` table: −4.5% vs −22.9%
   buy&hold — risk reduction, not alpha. Say it out loud; honesty is the spine.
4. **CMC Agent Hub (25s).** `python scripts/demo_mcp.py BTC` (or pre-recorded) —
   live MCP pulling the capital axis the free REST tier hides.
5. **ERC-8004 identity (25s).** Open the `setAgentURI` tx on testnet.bscscan.com;
   show agentId 1395 advertising web/MCP/ERC-8183 on-chain.
6. **ERC-8183 provider (25s).** `python scripts/demo_erc8183.py` — signed quote +
   the `bytes32` manifest hash. State the provider-half-only boundary.
7. **Close (10s).** One pure core, three on-chain/Agent-Hub surfaces, honest scope.

## Submission checklist

- [ ] Push `spike/agent-hub-bnb` to origin (otherwise judges see only baseline `main`).
- [ ] Record demo video (offline path = `demo_erc8183.py`; live = `demo_mcp.py BTC`).
- [ ] DoraHacks form: link repo + branch, both tx hashes, agentId 1395, manifest hash.
- [ ] Keep `.env.local` out of every commit (secrets: `CMC_PRO_API_KEY`, `PRIVATE_KEY`).
