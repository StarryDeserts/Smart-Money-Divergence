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
