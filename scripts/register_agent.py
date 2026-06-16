"""Register the Smart-Money Divergence Skill as an ERC-8004 on-chain agent identity
on BSC testnet (gasless via the MegaFuel paymaster — no tBNB, no real money).

Produces reports/agent_registration.json: the agentId (ERC-721) + tx hash that are
the hackathon's on-chain proof. Secrets are read from .env.local (gitignored) —
never from argv, never echoed, never committed.

Setup (one time) — add to .env.local (already gitignored):
    PRIVATE_KEY=0x...        # a BSC *testnet* key only — never a mainnet key
    WALLET_PASSWORD=...      # OPTIONAL; only encrypts the local keystore. If unset,
                             # an ephemeral random one is used (the key is re-imported
                             # from PRIVATE_KEY every run, so the keystore is never read back).

Run:
    python scripts/register_agent.py            # register, gasless via paymaster (idempotent)
    python scripts/register_agent.py --self-pay # register, wallet pays its own gas — reliable
                                                #   fallback when the testnet paymaster relay
                                                #   accepts a sponsored tx but never lands it
    python scripts/register_agent.py --dry-run  # build + preview, no on-chain tx
    python scripts/register_agent.py --update-endpoints
                                                # update an already-registered agent's on-chain
                                                #   agentURI to advertise the ERC-8183 endpoint
                                                #   (requires AGENT_ERC8183_URL); combine with
                                                #   --dry-run to preview without sending a tx.

Re-running is safe: if this wallet already registered the agent name, the script
reports the existing agentId instead of registering a duplicate.
"""
from __future__ import annotations

import json
import os
import secrets
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENV_LOCAL = ROOT / ".env.local"
EVIDENCE = ROOT / "reports" / "agent_registration.json"

# A public BSC-testnet RPC verified reachable from here. The SDK's built-in
# default (data-seed-prebsc-2-s2.binance.org) can be geo-blocked; overriding it
# keeps the gasless paymaster on (only an http://localhost RPC disables it).
DEFAULT_RPC = "https://bsc-testnet-rpc.publicnode.com"

DEFAULT_DESCRIPTION = (
    "Flags divergence between crowd sentiment and real whale-vs-retail capital "
    "flow for a token; returns a long/short/flat bias with a plain-language rationale."
)


def _load_env_local() -> None:
    """Load .env.local into the environment without overriding real env vars."""
    if not ENV_LOCAL.is_file():
        return
    try:
        from dotenv import load_dotenv

        load_dotenv(ENV_LOCAL, override=False)
        return
    except Exception:
        pass
    # Fallback parser so the script works even without python-dotenv installed.
    for line in ENV_LOCAL.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))


def _repo_web_url() -> str:
    """https URL for the agent's 'web' endpoint, derived from git origin."""
    override = os.environ.get("AGENT_REPO_URL")
    if override:
        return override
    try:
        url = subprocess.check_output(
            ["git", "remote", "get-url", "origin"], cwd=ROOT, text=True
        ).strip()
    except Exception:
        return "https://example.com/smart-money-divergence"
    if url.startswith("git@"):  # git@github.com:owner/repo.git -> https://github.com/owner/repo
        host, _, path = url[4:].partition(":")
        url = f"https://{host}/{path}"
    if url.endswith(".git"):
        url = url[:-4]
    return url


def _build_endpoints(web_url: str):
    """Declared endpoints (all must be http/https). Ties the BNB agent identity to
    the CMC Agent Hub Skill manifest, and optionally to the ERC-8183 server."""
    from bnbagent import AgentEndpoint

    endpoints = [
        AgentEndpoint(name="web", endpoint=web_url, version="0.1.0"),
        AgentEndpoint(
            name="MCP",
            endpoint=f"{web_url}/blob/main/skill/manifest.json",
            version="0.1.0",
        ),
    ]
    erc8183_url = os.environ.get("AGENT_ERC8183_URL")  # set once Vertical C server is live
    if erc8183_url:
        endpoints.append(AgentEndpoint(name="ERC-8183", endpoint=erc8183_url, version="0.1.0"))
    return endpoints


def _write_evidence(sdk, agent_name, *, agent_id, tx_hash, agent_uri, web_url, status,
                    gas_mode="self-paid", path: Path = EVIDENCE) -> None:
    chain_id = sdk.network.get("chain_id")
    wallet = sdk.wallet_address
    evidence = {
        "agent_name": agent_name,
        "agent_id": agent_id,
        "transaction_hash": tx_hash,
        "wallet_address": wallet,
        "network": sdk.network.get("name"),
        "chain_id": chain_id,
        "gas_mode": gas_mode,
        "registry_contract": sdk.contract_address,
        "web_endpoint": web_url,
        "agent_uri": agent_uri,
        "tx_explorer": f"https://testnet.bscscan.com/tx/{tx_hash}" if tx_hash else None,
        "wallet_explorer": f"https://testnet.bscscan.com/address/{wallet}",
        "scan_site": "https://www.8004scan.io",
        "scan_api": f"https://www.8004scan.io/api/v1/agents?chain_id={chain_id}",
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "status": status,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(evidence, indent=2) + "\n")


def _resolve_network(self_pay: bool):
    """Return (network_arg, rpc_url, gasless) for ERC8004Agent.

    Default: the 'bsc-testnet' preset — gasless via the MegaFuel paymaster.
    self_pay: an explicit NetworkConfig with the paymaster OFF, so the funded wallet
    pays its own (tiny) gas. More reliable when the testnet paymaster relay accepts a
    sponsored tx (returns a hash) but it never lands on-chain (observed 2026-06-15)."""
    rpc = os.environ.get("RPC_URL") or DEFAULT_RPC
    if not self_pay:
        os.environ["RPC_URL"] = rpc  # the preset path reads RPC_URL from env
        return "bsc-testnet", rpc, True
    from dataclasses import replace
    from bnbagent.config import resolve_network

    base = resolve_network("bsc-testnet")
    return replace(base, rpc_url=rpc, use_paymaster=False), rpc, False


UPDATE_EVIDENCE = ROOT / "reports" / "agent_identity_update.json"


def _update_endpoints(sdk, agent_name, agent_description, existing, web_url, gas_mode,
                      dry_run) -> int:
    """Update an already-registered agent's on-chain agentURI so it advertises the
    ERC-8183 endpoint. Uses the registry's setAgentURI (a real on-chain update);
    a plain re-register is idempotent and would skip."""
    agent_id = existing["agent_id"]
    endpoints = _build_endpoints(web_url)
    agent_uri = sdk.generate_agent_uri(
        name=agent_name, description=agent_description, endpoints=endpoints,
        agent_id=agent_id,
    )
    print(f"\n  updating agentId={agent_id} endpoints: {[e.name for e in endpoints]}")
    if dry_run:
        print("  --dry-run: built updated agentURI, skipped on-chain setAgentURI. Nothing sent.")
        return 0
    result = sdk.set_agent_uri(agent_id=agent_id, agent_uri=agent_uri)
    tx_hash = result.get("transactionHash")
    print(f"  OK  setAgentURI tx = {tx_hash}")
    _write_evidence(
        sdk, agent_name, agent_id=agent_id, tx_hash=tx_hash,
        agent_uri=result.get("agentURI", agent_uri), web_url=web_url,
        status="endpoints-updated", gas_mode=gas_mode, path=UPDATE_EVIDENCE,
    )
    print(f"  evidence written: {UPDATE_EVIDENCE.relative_to(ROOT)}")
    print(f"  verify tx: https://testnet.bscscan.com/tx/{tx_hash}")
    return 0


def _resolve_existing_agent(sdk, agent_name):
    """Find this wallet's already-registered agent, robustly.

    Primary: the SDK's name-keyed indexer lookup. It scans only the first
    indexer page, so an agent past page 0 reads as 'not found' (observed:
    agentId 1395 sits beyond the first 100). Fallback: the agentId tracked in
    reports/agent_registration.json, accepted ONLY after an on-chain ownerOf
    check confirms this wallet owns it. Never guesses — a miss returns None so
    --update-endpoints stops instead of minting a throwaway agent."""
    found = sdk.get_local_agent_info(agent_name)
    if found:
        return found
    if not EVIDENCE.is_file():
        return None
    try:
        agent_id = int(json.loads(EVIDENCE.read_text())["agent_id"])
    except Exception:
        return None
    try:
        info = sdk.get_agent_info(agent_id=agent_id)
    except Exception:
        return None
    if str(info.get("owner", "")).lower() != sdk.wallet_address.lower():
        return None
    return {
        "agent_id": agent_id,
        "name": agent_name,
        "agent_uri": info.get("agentURI", ""),
        "owner_address": info.get("owner"),
        "_source": "reports/agent_registration.json + on-chain ownerOf",
    }


def main() -> int:
    dry_run = "--dry-run" in sys.argv[1:]
    self_pay = "--self-pay" in sys.argv[1:]
    update_endpoints = "--update-endpoints" in sys.argv[1:]
    _load_env_local()

    if update_endpoints and not os.environ.get("AGENT_ERC8183_URL"):
        print(
            "--update-endpoints requires AGENT_ERC8183_URL (the live ERC-8183 "
            "provider endpoint to advertise).\n"
            f"Set it in {ENV_LOCAL} (gitignored), then re-run.",
            file=sys.stderr,
        )
        return 2

    agent_name = os.environ.get("AGENT_NAME", "smart-money-divergence")
    agent_description = os.environ.get("AGENT_DESCRIPTION", DEFAULT_DESCRIPTION)

    private_key = os.environ.get("PRIVATE_KEY")
    if not private_key:
        print(
            "Missing PRIVATE_KEY.\n"
            f"Add it to {ENV_LOCAL} (gitignored):\n"
            "    PRIVATE_KEY=0x...      # BSC TESTNET key only\n"
            "Then re-run: python scripts/register_agent.py",
            file=sys.stderr,
        )
        return 2
    # WALLET_PASSWORD only encrypts the local Keystore V3 file. Because we always
    # import from PRIVATE_KEY (never decrypt an existing keystore), an ephemeral
    # random password is safe when none is set — the private key stays the only
    # real secret.
    wallet_password = os.environ.get("WALLET_PASSWORD") or secrets.token_urlsafe(24)

    network_arg, rpc_url, gasless = _resolve_network(self_pay)
    gas_mode = "gasless (MegaFuel paymaster)" if gasless else "self-paid (funded wallet)"

    from bnbagent import ERC8004Agent, EVMWalletProvider

    web_url = _repo_web_url()
    wallet = EVMWalletProvider(password=wallet_password, private_key=private_key)
    sdk = ERC8004Agent(wallet_provider=wallet, network=network_arg, debug=False)

    print("== ERC-8004 agent registration (BSC testnet) ==")
    print(f"  agent name : {agent_name}")
    print(f"  wallet     : {sdk.wallet_address}")
    print(f"  network    : {sdk.network.get('name')} (chain_id {sdk.network.get('chain_id')})")
    print(f"  registry   : {sdk.contract_address}")
    print(f"  rpc        : {rpc_url}")
    print(f"  gas mode   : {gas_mode}")
    print(f"  web        : {web_url}")

    # Idempotency: if this wallet already registered this name, report and stop.
    existing = _resolve_existing_agent(sdk, agent_name)
    if existing:
        if existing.get("_source"):
            print(f"  resolved   : agentId={existing['agent_id']} via {existing['_source']}")
        if update_endpoints:
            return _update_endpoints(
                sdk, agent_name, agent_description, existing, web_url, gas_mode, dry_run
            )
        print(f"\n  already registered: agentId={existing['agent_id']} — skipping.")
        _write_evidence(
            sdk, agent_name, agent_id=existing["agent_id"], tx_hash=None,
            agent_uri=existing.get("agent_uri", ""), web_url=web_url, status="pre-existing",
            gas_mode=gas_mode,
        )
        print(f"  evidence written: {EVIDENCE.relative_to(ROOT)}")
        return 0

    if update_endpoints:
        print(
            f"\n--update-endpoints: could not resolve an agent named {agent_name!r} "
            f"owned by {sdk.wallet_address} (indexer page-0 miss and no verifiable "
            f"{EVIDENCE.relative_to(ROOT)} record). Refusing to fall through to a fresh "
            "registration (that would mint a throwaway agentId). Nothing sent.",
            file=sys.stderr,
        )
        return 2

    endpoints = _build_endpoints(web_url)
    agent_uri = sdk.generate_agent_uri(
        name=agent_name, description=agent_description, endpoints=endpoints
    )
    print(f"\n  endpoints  : {[e.name for e in endpoints]}")
    print(f"  agent_uri  : {agent_uri[:64]}... ({len(agent_uri)} chars)")

    if dry_run:
        print("\n  --dry-run: built the agent URI, skipped on-chain registration. Nothing sent.")
        return 0

    print(f"\n  submitting registration ({gas_mode})...")
    result = sdk.register_agent(agent_uri=agent_uri)
    agent_id = result["agentId"]
    tx_hash = result["transactionHash"]
    print(f"\n  OK  agentId = {agent_id}")
    print(f"      txHash  = {tx_hash}")

    _write_evidence(
        sdk, agent_name, agent_id=agent_id, tx_hash=tx_hash,
        agent_uri=result.get("agentURI", agent_uri), web_url=web_url, status="registered",
        gas_mode=gas_mode,
    )
    print(f"\n  evidence written: {EVIDENCE.relative_to(ROOT)}")
    print(f"  verify tx: https://testnet.bscscan.com/tx/{tx_hash}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
