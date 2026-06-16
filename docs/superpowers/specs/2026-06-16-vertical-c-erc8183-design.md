# Vertical C — ERC-8183 Priced Provider + Identity Wiring (Design Spec)

**Date:** 2026-06-16
**Status:** Design approved (approach B), ready for implementation planning
**Event:** BNB Hack — special prize **Best Use of BNB AI Agent SDK** (additive to Track 2)
**Branch:** `spike/agent-hub-bnb` (baseline `main` + tag `v0.1.0-submission` untouched)
**Submit by:** 2026-06-21 on DoraHacks · demo video mandatory
**Companion docs:**
[`../notes/2026-06-15-special-prize-spike.md`](../notes/2026-06-15-special-prize-spike.md) (feasibility spike, vertical A/B/C),
[`../specs/2026-06-12-divergence-strategy-skill-design.md`](../specs/2026-06-12-divergence-strategy-skill-design.md) (the core Skill),
[`../../../reports/agent_registration.json`](../../../reports/agent_registration.json) (agentId 1395 on-chain proof)

---

## 1. Summary

Vertical A already minted the Smart-Money Divergence agent as **ERC-8004 on-chain identity agentId 1395** on BSC testnet. Vertical C makes that identity *commercial*: it presents the divergence Skill as a **priced ERC-8183 agent service** — one that **negotiates a signed quote**, **quotes an HTTP-402 price floor**, and **produces the exact `DeliverableManifest` (with its on-chain `keccak256` hash) that the kernel would verify** — and **binds that service to agentId 1395's on-chain identity**, proven by live reads of the deployed testnet commerce kernel.

**What we claim — and what we don't.** We claim a *registered, priced, negotiating ERC-8183 provider bound to the live testnet kernel*. We do **not** claim a settled, paid job: a full settlement requires escrowing the payment token U (mint is `onlyOwner`; our wallet holds 0 U) and waiting out the **86 400 s (24 h) dispute window** — out of reach inside the deadline, and we say so plainly. This honest boundary mirrors the core Skill's posture (§7 of the core spec: report the truth, don't fake a number).

**Why approach B (not a live server demo).** The proof runs through a **deterministic in-process script + tests** that exercise the *same* SDK commerce code paths a live server composes — so the mandatory video can't be derailed by a live listener or an unroutable `localhost` identity URL. The runnable `create_erc8183_app(...)` server ships as a thin, inspectable wrapper so "stand up the provider server" is literally true; it is simply not on the demo's critical path. This mirrors how B1 (`cmc_mcp`) shipped: adapter + demo + tests.

---

## 2. Goals & non-goals

### Goals
- Present the divergence Skill as a **priced ERC-8183 provider service**: negotiate → signed quote → HTTP-402 floor → `DeliverableManifest`.
- **Bind** that service to **agentId 1395** by advertising an `ERC-8183` endpoint on its ERC-8004 identity.
- **Prove live-kernel binding** with on-chain reads of the deployed testnet AgenticCommerce / Router / Policy contracts.
- Ship a **runnable** `create_erc8183_app(...)` provider server (thin wrapper) + a **deterministic demo** + **tests**.
- Keep it **zero-money, testnet-only**, and **honest** about settlement being out of scope.

### Non-goals
- **No funded/settled job.** No U-token escrow, no `fund`, no `settle`, no dispute-window wait. (Infeasible: `onlyOwner` mint + 24 h window.)
- **No second wallet, no faucet hunt, no real funds.** One existing testnet key, reused from vertical A.
- **No new strategy logic.** The deliverable content is the *existing* divergence verdict — Vertical C is a commerce + identity wrapper, nothing in `signal_core` changes.
- **No mainnet, no x402.** The money-line stays "zero-money, MCP only."
- No live-listener dependency in the demo/video (the server exists but isn't the proof path).

---

## 3. Scope boundary — what is provable vs out of scope

| ERC-8183 job lifecycle step | In this vertical? | Why |
|---|---|---|
| `negotiate` → signed quote (EIP-191) | ✅ provable offline | `NegotiationHandler` signs with our wallet; no chain write |
| HTTP-402 price floor | ✅ provable offline | `service_price` view + `verify_job` 402 path |
| `DeliverableManifest` + on-chain `keccak256` hash | ✅ provable offline | `manifest_hash()` is pure (`schema.py:67`) — no write |
| `JobDescription` (the on-chain `createJob` payload) | ✅ built offline | `build_job_description` produces it from the quote |
| Identity advertises `ERC-8183` endpoint on agentId 1395 | ✅ on-chain write (idempotent re-register) | reuses vertical A's gasless/self-pay path |
| Live kernel reads (payment token, job counter, dispute window) | ✅ on-chain read | proves the service is bound to the *deployed* kernel |
| `createJob` / `setBudget` / `fund` / `submit` / `settle` | ❌ out of scope | needs U-token escrow (0 balance, `onlyOwner` mint) + 24 h window |

**The honest one-liner (for README + demo output):** *"Smart-Money Divergence is a registered, priced ERC-8183 provider bound to the live BSC-testnet commerce kernel. It negotiates signed quotes and produces verifiable deliverable manifests; a funded settlement is out of scope for the testnet demo (owner-minted payment token + 24 h dispute window)."*

---

## 4. Architecture & module boundaries

One new adapter wraps the SDK; a demo script and an optional server compose it; identity wiring reuses the existing hook. Nothing in the core engine changes.

```
   existing divergence engine ──▶ run a real verdict (Signal)
              │
              ▼
   ┌─────────────────────────────────────────────┐
   │ erc8183_provider.py  (NEW adapter)           │
   │  - wallet from PRIVATE_KEY (EVMWalletProvider)│
   │  - ERC8183Client (read-capable)              │
   │  - negotiate()      → signed quote           │
   │  - quote_price()    → HTTP-402 floor         │
   │  - build_manifest() → DeliverableManifest    │
   │  - kernel_binding() → live on-chain reads    │
   └─────────────────────────────────────────────┘
        │                    │                  │
        ▼                    ▼                  ▼
 scripts/demo_erc8183.py   scripts/serve_   tests/test_erc8183_
 (deterministic proof,     erc8183.py       provider.py
  runs in the video)       (runnable        (offline,
        │                   server wrapper)  deterministic)
        ▼
 scripts/register_agent.py  (EXISTING hook: AGENT_ERC8183_URL
   → AgentEndpoint("ERC-8183") on agentId 1395)
```

| Module | Job | Depends on |
|---|---|---|
| **`erc8183_provider.py`** (new) | Thin façade: wallet, read-capable client, `negotiate / quote_price / build_manifest / kernel_binding`. The only place SDK-commerce wiring lives. | `bnbagent.erc8183`, existing engine |
| **`scripts/demo_erc8183.py`** (new) | Deterministic, no live socket: prints kernel binding, a signed quote, the 402 floor, and a manifest + its `keccak256`. The video path. | `erc8183_provider` |
| **`scripts/serve_erc8183.py`** (new) | Thin wrapper over `create_erc8183_app(...)` so the provider is literally runnable (`uvicorn`). Not on the proof path. | `bnbagent.erc8183.server` |
| **`scripts/register_agent.py`** (existing) | Already appends `AgentEndpoint("ERC-8183")` when `AGENT_ERC8183_URL` is set (lines 101–103). Idempotent re-register. | vertical A |
| **`tests/test_erc8183_provider.py`** (new) | Offline asserts: signed-quote shape, 402 value, manifest hash determinism, negotiation rejects. | `erc8183_provider` |

**Why this shape:** the riskiest surface (live-testnet contract friction) is sealed behind one adapter; the credibility claim (bound to the *deployed* kernel) is structural (live reads), not a promise; and the demo path has zero live-network fragility.

---

## 5. `erc8183_provider.py` — the adapter (detail)

Construction reuses vertical A's proven wallet path (`register_agent.py:181`) — **no keystore password needed**, sidestepping `ERC8183Config.from_env()`'s `WALLET_PASSWORD` requirement:

```python
wallet = EVMWalletProvider(password=secrets.token_urlsafe(24), private_key=PRIVATE_KEY)
client = ERC8183Client(wallet_provider=wallet, network="bsc-testnet")
```

**`kernel_binding() -> dict`** — live on-chain reads proving the service points at the deployed kernel:
`agent_address`, `payment_token`, token `symbol`/`decimals`, the AgenticCommerce/Router/Policy addresses, the current **job counter**, and the **dispute window** (the same reads the spike used: counter 160, window 86 400 s). Read via `ERC8183Client` and its `CommerceClient`/`PolicyClient` sub-clients; exact getter names confirmed at implementation time.

**`negotiate(request) -> NegotiationResult`** — `NegotiationHandler.from_erc8183_client(client, service_price)` (auto-fills currency / chain_id / verifying_contract from the live kernel), then `.negotiate(request)` → an EIP-191 `provider_sig` over the `negotiation_hash`. Rejects with a `ReasonCode` (e.g. `PRICE_TOO_LOW`, `DEADLINE_TOO_TIGHT`) when terms don't clear.

**`quote_price() -> int|str`** — the HTTP-402 price floor (`service_price`, default `1 U` = `10**18`, overridable via `ERC8183_SERVICE_PRICE`). This is the value a real `verify_job` returns as 402 when a job's budget is under the floor.

**`build_manifest(verdict, *, job_id=0) -> DeliverableManifest`** — wraps a **real divergence verdict** in the canonical deliverable:
```python
DeliverableManifest(version=1, job_id=job_id, chain_id=97,
                    contracts={"commerce":..., "router":..., "policy":...},
                    response={"content": verdict_json, "content_type": "application/json"},
                    metadata={"agent_id": 1395, "skill": "smart-money-divergence"})
```
`.manifest_hash()` (`schema.py:67`) returns the `bytes32` `keccak256(canonical JSON)` the provider would pass to `submit` — computed **purely, no chain write**. `job_id=0` is a documented "unfunded / illustrative" sentinel, labeled as such in output (honest: no real job exists).

**Boundaries / errors:** missing `PRIVATE_KEY` → clear exit (like `register_agent.py`). `kernel_binding()` wraps RPC errors so the demo degrades to "kernel unreachable" rather than crashing. **No write/settlement method is exposed** — the adapter is read + sign + hash only.

---

## 6. `scripts/demo_erc8183.py` — the video path

Deterministic, no live socket, single command (`python scripts/demo_erc8183.py`). Sections, each clearly labeled:

1. **Identity** — agentId 1395, wallet, registry (from `reports/agent_registration.json`).
2. **Live kernel binding** — `kernel_binding()` reads, printed with the testnet explorer addresses → proves we talk to the *deployed* contracts.
3. **Negotiation** — a sample buyer request → a **signed quote** (print `negotiation_hash` + `provider_sig`), plus a rejection example (`PRICE_TOO_LOW`).
4. **Price floor** — the HTTP-402 value in human units (`1 U`).
5. **Deliverable** — run a **real divergence verdict**, wrap it in a `DeliverableManifest`, print the canonical JSON + its `keccak256` `bytes32`; note it's the exact `submit` payload, unfunded by design.
6. **Honest boundary** — one line stating settlement is out of scope and why.

---

## 7. `scripts/serve_erc8183.py` — runnable provider (optional, off the proof path)

Composes `create_erc8183_app(config, prefix="/erc8183")` and serves it under `uvicorn`, exposing `/status`, `/negotiate`, `/health`, root manifest. Included so the provider server genuinely exists and is inspectable; **not** required by the demo or tests. `config` is built around the same `wallet`/`client` the adapter uses (constructed directly, not via `from_env`, to avoid the keystore-password path). Documented as "run locally to poke the live endpoints"; the on-chain identity advertises a **stable manifest URL** (the repo's `skill/manifest.json` or the documented `/status` route), never `localhost`.

---

## 8. Identity wiring — reuse the existing hook

No new registration code. `register_agent.py` already appends the endpoint when the env var is set:

```python
erc8183_url = os.environ.get("AGENT_ERC8183_URL")   # lines 101–103
if erc8183_url:
    endpoints.append(AgentEndpoint(name="ERC-8183", endpoint=erc8183_url, version="0.1.0"))
```

Flow: set `AGENT_ERC8183_URL` to the stable manifest URL → re-run `register_agent.py` (`--self-pay`, the verified-reliable path). Registration is idempotent (`get_local_agent_info` short-circuits a duplicate), so this **updates agentId 1395's advertised endpoints** and refreshes `reports/agent_registration.json`. This is the one on-chain **write** in the vertical; like all writes here it is a shared-state action requiring explicit user confirmation at run time.

---

## 9. Testing strategy (offline, deterministic — tests as proof)

| Target | Test | What it proves |
|---|---|---|
| `build_manifest` | same verdict → identical `manifest_hash()`; a changed field → different hash | the on-chain hash contract is deterministic & reproducible (what a verifier reruns) |
| `negotiate` | a valid request → result carries `negotiation_hash` + non-empty `provider_sig`; sub-floor price → `PRICE_TOO_LOW`; too-tight deadline → `DEADLINE_TOO_TIGHT` | the quote is genuinely signed and terms are enforced |
| `quote_price` | returns the configured floor; honors `ERC8183_SERVICE_PRICE` | the 402 price is real and configurable |
| `JobDescription` round-trip | `build_job_description(result)` → `from_str(...)` → fields preserved, `provider_sig` survives | the on-chain `createJob` payload is well-formed |

Network-dependent reads (`kernel_binding()`) are exercised by the **demo**, not asserted in CI — mirroring B1's split (live reads are demoed, pure logic is unit-tested). Wallet/sign is real (deterministic key), so signatures are asserted without mocking.

---

## 10. Honest framing (the credibility win, consistent with the core)

- The demo's final line and the README state the **scope boundary** verbatim (§3): registered + priced + negotiating + bound, settlement out of scope, and *why*.
- The `DeliverableManifest` is the **real** verdict, with the **real** on-chain hash — not a mock. The only fiction is the `job_id` sentinel, explicitly labeled.
- Same posture as the core Skill: showing exactly what is and isn't proven beats overclaiming — judges in this space know the difference.

---

## 11. Build sequence

1. `erc8183_provider.py` — adapter (wallet, client, the four methods). Confirm sub-client getter names against the SDK while wiring.
2. `tests/test_erc8183_provider.py` — offline asserts (TDD weight on `build_manifest` hash + signed-quote shape).
3. `scripts/demo_erc8183.py` — the deterministic video path.
4. `scripts/serve_erc8183.py` — thin runnable server wrapper.
5. Identity wiring — set `AGENT_ERC8183_URL`, re-run `register_agent.py --self-pay` (**explicit user confirmation** for the on-chain write).
6. README section — the honest scope boundary + how to run the demo.
7. Commit to `spike/agent-hub-bnb` (**explicit user confirmation**; no push).

---

## 12. Risks & out of scope

| Risk | Mitigation |
|---|---|
| SDK sub-client getter names differ from assumption | adapter is the single touch-point; confirmed during step 1, tests catch drift |
| Testnet RPC flaky during demo | `kernel_binding()` degrades gracefully; demo still shows signed quote + manifest offline |
| Identity URL must be publicly meaningful | advertise the stable repo `manifest.json` URL, never `localhost` |
| Scope creep toward settlement | explicitly out of scope (§2/§3); no write/escrow method exists in the adapter |

**Out of scope / future:** funded + settled job (needs owner-minted U + 24 h window); a publicly hosted live provider endpoint; UMA-style dispute/vote flows; second-wallet buyer simulation.
