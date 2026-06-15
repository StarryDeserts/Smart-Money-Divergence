# Special-prize feasibility spike — Agent Hub (CMC) + BNB AI Agent SDK

**Date:** 2026-06-15 · **Branch:** `spike/agent-hub-bnb` · **Mode:** read-only spike, baseline
`main` + tag `v0.1.0-submission` untouched. Goal: turn "should we spend the remaining ~6
days chasing *Best Use of CMC Agent Hub* + *Best Use of BNB AI Agent SDK*" into a
fact-based decision.

## Verified environment facts (checked this session, not from prior export)

- **`pip install bnbagent` works** in `.venv` → `bnbagent 0.3.6`, `web3 7.16.0`,
  `eth-account 0.13.7`. Clean wheels on Python 3.12, no build failures.
- **Baseline regression check passed:** the 63 tests are still green *after* adding the
  web3 stack to the venv (`63 passed`). New deps don't break the submission.
- **BSC testnet RPC reachable from here:** `eth_chainId → 0x61` from
  `bsc-testnet-rpc.publicnode.com` and `data-seed-prebsc-1-s1.bnbchain.org:8545`.
  (Only Binance's *own* fapi endpoints are region-blocked; testnet RPC is fine.)
- **ERC-8004 API surface confirmed locally:** `from bnbagent import ERC8004Agent,
  AgentEndpoint, EVMWalletProvider` imports; `register_agent`, `generate_agent_uri`,
  `get_all_agents`, `set_metadata`, `wallet_address` all present.

## Vertical A — ERC-8004 identity registration  →  *Best Use of BNB AI Agent SDK*

- **Flow:** `EVMWalletProvider(password, private_key)` → `ERC8004Agent(network="bsc-testnet")`
  → `generate_agent_uri(name, description, endpoints=[AgentEndpoint(...)])` →
  `register_agent(agent_uri)` → returns `{agentId (ERC-721), tx hash}`.
- **Gasless** on bsc-testnet via MegaFuel paymaster — **no tBNB, no real money.**
- **Reuse:** `AgentEndpoint` accepts `name="MCP"` and `name="web"` → the agent identity can
  *declare* endpoints pointing at our existing `skill/manifest.json` / Skill runtime. Ties
  the two prize narratives together.
- **Needs from user:** one testnet `PRIVATE_KEY` + any `WALLET_PASSWORD`. Nothing else.
- **Effort:** low (hours, one script). **Risk:** low. **Real money:** none.
- **Payoff:** a real `agentId` + tx hash = the hackathon's required *on-chain proof*.

## Vertical B — CMC Agent Hub consumption  →  *Best Use of CMC Agent Hub*

Today the Skill consumes bare CMC **Pro REST** (`cmc_client.py`) → surface coverage = 1
(the Skill manifest only). Two ways to deepen:

- **B1 — Agent Hub MCP (API-key, zero money).** Swap `LiveAdapter.fetch` to go through the
  Agent Hub MCP server instead of raw REST. Same free key, same data tier, but now "via
  Agent Hub MCP" → surface 1 → 2. **Open item:** the concrete MCP endpoint/config isn't on
  the marketing page; needs the real Agent Hub setup doc (or the user's CMC account).
- **B2 — x402 pay-per-call (real money).** Base `https://pro-api.coinmarketcap.com/x402/`,
  endpoints incl. `/x402/mcp`, `/x402/v3/cryptocurrency/quotes/latest`,
  `/x402/v4/dex/pairs/quotes/latest`. HTTP 402 → sign `PAYMENT-SIGNATURE` (JWT) → 200.
  **Rail = USDC on Base mainnet, $0.01/request.** This is *real money on a mainnet* — it
  crosses the standing "zero real money" line. Upside: the `/v4/dex/...` endpoints are the
  kind of on-chain/whale data the free key paywalls, so x402 could unlock a real Green-tier
  signal pay-per-call. Surface 2 → 3.
- **Effort:** B1 low-med (gated on finding the MCP endpoint); B2 med. **Risk:** B1 medium
  (undocumented endpoint), B2 medium + money-line.

## Vertical C — ERC-8183 full commerce  →  *Best Use of BNB AI Agent SDK* (inventive)

The "full suite" picked in the prior session. Reframes the project as a payable on-chain
research agent selling divergence verdicts.

- **What it takes (all examples exist in the SDK repo):** a FastAPI **provider server**
  (`bnbagent.erc8183.server.create_erc8183_app`, the `[server]` extra) running a funded-job
  poll loop; a **client driver** (createJob → registerJob → setBudget → fund → submit →
  settle); a **test ERC-20** budget token (client funds 1 token into escrow); a **storage
  backend** for the deliverable (LocalStorageProvider needs a public base URL, or IPFS via a
  Pinata JWT); **two wallets** (client + provider); a settle loop that waits the dispute
  window. Our `run_skill(token)` verdict becomes the provider's `on_job` deliverable.
- **Effort:** high (≈2–4 days incl. live-testnet contract friction: test-token acquisition,
  nonces, dispute-window timing). **Risk:** high. **Real money:** none (testnet), but needs
  test ERC-20 units + 2 keypairs.

## Deadline math

- Deadline **2026-06-21**, today **2026-06-15** → **~6 days.**
- **Demo video is now mandatory** (confirmed) — a real deliverable; reserve ~1 day for it +
  the DoraHacks form.
- So the real integration budget is ~4–5 working days.

## Recommended sequencing (honors the ambition, de-risks the clock)

1. **A (ERC-8004)** first — banks on-chain proof + BNB prize, ~zero risk, zero money,
   needs only the testnet PK. **Do this first.**
2. **B1 (Agent Hub MCP)** — pin the MCP endpoint, swap the fetch transport. Banks the CMC
   prize surface with zero money. (B2/x402 only if the money-line is opened.)
3. **C (ERC-8183)** — the inventive stretch, **hard time-box (~2 days).** If it slips,
   A + B1 + the honest baseline still stand as a complete submission.
4. Reserve Day 5–6 for the **mandatory video** + form.

## Needs from the user (when we proceed)

- **A:** testnet `PRIVATE_KEY` in `.env.local` (gitignored — never pasted in chat).
- **C (if chosen):** a 2nd testnet wallet + test ERC-20 budget units (faucet/mint); optional
  Pinata JWT if we use IPFS storage instead of local.
- **B2 (only if money-line opened):** a Base wallet funded with a few USDC.

## Decision gate

1. **x402 money line:** keep zero-money (CMC prize via MCP/API-key only), or allow a few
   real USDC on Base to demo x402 pay-per-call?
2. **Scope/sequencing:** A+B1 first then time-box C (recommended), or all-in on full
   ERC-8183 now, or just A+B1 and skip C?

## Reversibility

Everything here is on `spike/agent-hub-bnb`. To fully revert: `git checkout main` (+ delete
branch) and `.venv/bin/pip uninstall -y bnbagent web3 eth-account` (or rebuild the venv).
