"""ERC-8183 priced-provider façade for the Smart-Money Divergence Skill.

Presents the shipped Skill (`run_skill`) as a payable ERC-8183 service: it
negotiates a signed price quote, packages a verdict into the canonical
``DeliverableManifest`` whose keccak is the exact ``bytes32`` a provider would
pass to ``AgenticCommerce.submit``, and (live) reads the on-chain kernel binding.

Honest scope (Vertical C): this proves the *provider* half of ERC-8183 —
negotiation, the on-chain-exact deliverable hash, identity binding. It does NOT
settle a job: settlement needs the *client* to fund the escrow in the U payment
token, whose testnet ``mint`` is ``onlyOwner`` (our wallet holds 0 U). The
manifest hash and the signed quote are real and verifiable; the escrow
round-trip is out of scope and is called out in the demo + README.

bnbagent is a venv-only integration dependency: every symbol from it is imported
lazily inside the function that needs it, so importing this module never drags
the SDK into the core Skill.
"""
from __future__ import annotations

import json
import os

AGENT_ID = 1395                       # our ERC-8004 identity (reports/agent_registration.json)
DEFAULT_NETWORK = "bsc-testnet"
DEFAULT_RPC = "https://bsc-testnet-rpc.publicnode.com"
DEFAULT_SERVICE_PRICE = "1000000000000000000"   # 1 U (18 decimals)
TESTNET_PAYMENT_TOKEN = "0xc70B8741B8B07A6d61E54fd4B20f22Fa648E5565"  # U token; not in the preset (read on-chain), so the live smoke test pins it to payment_token


def testnet_chain_id(network: str = DEFAULT_NETWORK) -> int:
    """EVM chain id for the preset (97 for bsc-testnet). Offline — preset lookup."""
    from bnbagent.config import resolve_network
    return resolve_network(network).chain_id


def testnet_contracts(network: str = DEFAULT_NETWORK) -> dict[str, str]:
    """Deployed ERC-8183 kernel/router/policy addresses for the preset.

    Offline — reads the SDK's NetworkConfig preset, no RPC. Single source of
    truth so the demo's manifest hash matches what the live client would submit.
    """
    from bnbagent.config import resolve_network
    nc = resolve_network(network)
    return {
        "commerce": nc.commerce_contract,
        "router": nc.router_contract,
        "policy": nc.policy_contract,
    }


def sample_request(token: str = "BTC") -> dict:
    """A well-formed ERC-8183 negotiation request for a divergence verdict.

    Shape required by ``NegotiationRequest.from_dict``: ``task_description`` plus
    ``terms`` with non-empty ``deliverables`` and ``quality_standards``.
    """
    return {
        "task_description": f"Smart-money divergence verdict for {token.upper()}",
        "terms": {
            "deliverables": (
                "A long/short/flat bias for the token with divergence + "
                "confidence scores and a plain-language rationale."
            ),
            "quality_standards": (
                "Verdict derived from the backtested signal path (whale-vs-retail "
                "capital flow vs crowd sentiment); degraded flag set when the "
                "capital axis is unavailable."
            ),
        },
    }


def build_deliverable_manifest(
    verdict: dict,
    *,
    chain_id: int,
    contracts: dict[str, str],
    job_id: int = 0,
    agent_id: int = AGENT_ID,
):
    """Package a ``run_skill`` verdict as the canonical ERC-8183 deliverable.

    ``manifest_hash()`` on the result is the exact ``bytes32`` that
    ``AgenticCommerce.submit(jobId, deliverable, optParams)`` expects — pure,
    no chain write. Verifiers reproduce it via
    ``DeliverableManifest.from_dict(fetched).manifest_hash()``.
    """
    from bnbagent.erc8183.schema import DeliverableManifest, SCHEMA_VERSION
    return DeliverableManifest(
        version=SCHEMA_VERSION,
        job_id=job_id,
        chain_id=chain_id,
        contracts=contracts,
        response={
            "content": json.dumps(verdict, sort_keys=True, separators=(",", ":")),
            "content_type": "application/json",
        },
        metadata={"agent_id": agent_id, "schema": "smart-money-divergence/v1"},
    )


def make_negotiation_handler(
    wallet,
    *,
    currency: str,
    chain_id: int,
    verifying_contract: str,
    service_price: str = DEFAULT_SERVICE_PRICE,
):
    """Seller-side negotiation handler bound to a chain + commerce contract.

    Passing ``wallet`` makes the handler sign the quote (provider_sig) via local
    EIP-191 — no RPC. Binding ``chain_id`` + ``verifying_contract`` prevents
    cross-chain replay of that signature. Offline-constructable with a throwaway
    key. The stock handler accepts any well-formed request at ``service_price``
    and rejects only empty/ambiguous terms (``AMBIGUOUS_TERMS``) or an over-cap
    description (``TASK_TOO_LONG``).
    """
    from bnbagent.erc8183.negotiation import NegotiationHandler
    return NegotiationHandler(
        service_price=service_price,
        currency=currency,
        wallet_provider=wallet,
        chain_id=chain_id,
        verifying_contract=verifying_contract,
    )


def build_job_anchor(result) -> str:
    """Serialize an *accepted* negotiation result into the on-chain createJob
    ``description`` (a compact Schema-v1 JSON string).

    Embeds ``negotiation_hash`` + ``provider_sig`` so anyone can ``ecrecover``
    that the provider agreed to these exact terms. Pure — no chain write. Inverse:
    ``parse_job_description`` / ``JobDescription.from_str``. Raises on a rejected
    result (no agreed price)."""
    from bnbagent.erc8183.negotiation import build_job_description
    return build_job_description(result.to_dict())


class DivergenceProvider:
    """Live ERC-8183 provider façade.

    Construction touches the RPC — the SDK's ``ERC8183Client`` verifies the RPC's
    chain_id against the NetworkConfig — so this is the network-bound half. The
    module-level helpers above are what the offline tests + demo exercise.
    """

    def __init__(self, wallet, *, network="bsc-testnet",
                 service_price: str = DEFAULT_SERVICE_PRICE):
        from bnbagent.erc8183.client import ERC8183Client
        from bnbagent.erc8183.negotiation import NegotiationHandler
        self.client = ERC8183Client(wallet, network=network)
        self.service_price = service_price
        self.handler = NegotiationHandler.from_erc8183_client(
            erc8183_client=self.client,
            service_price=service_price,
            wallet_provider=wallet,
        )

    @classmethod
    def from_env(cls, *, network: str = DEFAULT_NETWORK, rpc_url: str | None = None,
                 service_price: str = DEFAULT_SERVICE_PRICE) -> "DivergenceProvider":
        """Build a live provider from PRIVATE_KEY in the environment / .env.local.

        ERC8183Client reads ``NetworkConfig.rpc_url`` directly (it ignores the
        RPC_URL env var), so we resolve the preset and ``replace`` its rpc_url
        with a reachable endpoint to dodge geo-blocked defaults.
        """
        import secrets
        from dataclasses import replace
        from bnbagent import EVMWalletProvider
        from bnbagent.config import resolve_network
        pk = os.environ.get("PRIVATE_KEY")
        if not pk:
            raise RuntimeError("PRIVATE_KEY not set (add it to .env.local, gitignored)")
        password = os.environ.get("WALLET_PASSWORD") or secrets.token_urlsafe(24)
        wallet = EVMWalletProvider(password=password, private_key=pk, persist=False)
        rpc = rpc_url or os.environ.get("RPC_URL") or DEFAULT_RPC
        nc = replace(resolve_network(network), rpc_url=rpc)
        return cls(wallet, network=nc, service_price=service_price)

    def quote_price(self) -> str:
        return self.service_price

    def negotiate(self, request: dict):
        return self.handler.negotiate(request)

    def build_manifest(self, verdict: dict, *, job_id: int = 0):
        return build_deliverable_manifest(
            verdict,
            chain_id=self.client.network.chain_id,
            contracts={
                "commerce": self.client.commerce.address,
                "router": self.client.router.address,
                "policy": self.client.policy.address,
            },
            job_id=job_id,
        )

    def kernel_binding(self) -> dict:
        """Live reads proving the provider is bound to the real kernel."""
        return {
            "chain_id": self.client.network.chain_id,
            "agent_address": self.client.address,
            "commerce": self.client.commerce.address,
            "router": self.client.router.address,
            "policy": self.client.policy.address,
            "payment_token": self.client.payment_token,
            "token_symbol": self.client.token_symbol(),
            "token_decimals": self.client.token_decimals(),
            "job_counter": self.client.commerce.job_counter(),
            "dispute_window_s": self.client.policy.dispute_window(),
        }
