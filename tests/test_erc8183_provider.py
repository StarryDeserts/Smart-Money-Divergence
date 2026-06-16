"""Offline tests for the ERC-8183 provider façade.

Everything here runs without a network: a throwaway in-memory wallet signs
locally (EIP-191), the negotiation handler is built from fixed chain constants,
and the deliverable manifest hash is pure keccak. The live, network-bound
DivergenceProvider is covered by a skipped-by-default smoke test (Task 3).
"""
from __future__ import annotations

import json
import os
from datetime import date, timedelta

import pytest

from divergence.types import Snapshot
from divergence.skill.runtime import run_skill
from divergence.adapters import erc8183_provider as ep

# Known BSC-testnet ERC-8183 deployment (bnbagent NetworkConfig preset, chain 97).
_CHAIN_ID = 97
_CONTRACTS = {
    "commerce": "0xa206c0517b6371c6638cd9e4a42cc9f02a33b0de",
    "router": "0xd7d36d66d2f1b608a0f943f722d27e3744f66f25",
    "policy": "0x4f4678d4439fec812ac7674bb3efb4c8f5fb78a6",
}
_CURRENCY = "0xc70B8741B8B07A6d61E54fd4B20f22Fa648E5565"  # U token (testnet)


def _dummy_wallet():
    """In-memory, offline wallet from a throwaway key — no funds, no network."""
    from bnbagent import EVMWalletProvider
    return EVMWalletProvider(password="test", private_key="0x" + "11" * 32, persist=False)


class _Provider:
    def __init__(self, window): self._w = window
    def trailing_window(self, token, end, lookback): return self._w[-lookback:]


def _window(n=90, whale_last=10.0, fg_last=5.0):
    start = date(2025, 1, 1)
    out = []
    for i in range(n):
        last = i == n - 1
        out.append(Snapshot(token="BTC", day=start + timedelta(days=i), price=100.0,
                            whale_retail_flow=(whale_last if last else 0.0),
                            fear_greed=(fg_last if last else 50.0)))
    return out


def _verdict():
    return run_skill("BTC", _Provider(_window()), theta_abs=0.5)


def test_sample_request_is_well_formed():
    req = ep.sample_request("BTC")
    assert "BTC" in req["task_description"]
    assert req["terms"]["deliverables"]
    assert req["terms"]["quality_standards"]


def test_manifest_hash_is_deterministic_bytes32():
    v = _verdict()
    m1 = ep.build_deliverable_manifest(v, chain_id=_CHAIN_ID, contracts=_CONTRACTS, job_id=7)
    m2 = ep.build_deliverable_manifest(v, chain_id=_CHAIN_ID, contracts=_CONTRACTS, job_id=7)
    h = m1.manifest_hash()
    assert isinstance(h, bytes) and len(h) == 32
    assert m1.manifest_hash() == m2.manifest_hash()


def test_manifest_round_trips_and_verifies():
    from bnbagent.erc8183.schema import DeliverableManifest
    m = ep.build_deliverable_manifest(_verdict(), chain_id=_CHAIN_ID, contracts=_CONTRACTS, job_id=7)
    restored = DeliverableManifest.from_dict(m.to_dict())
    assert restored.manifest_hash() == m.manifest_hash()
    assert m.verify(restored.manifest_hash()) is True


def test_manifest_carries_agent_identity_and_verdict():
    m = ep.build_deliverable_manifest(_verdict(), chain_id=_CHAIN_ID, contracts=_CONTRACTS)
    assert m.metadata["agent_id"] == ep.AGENT_ID
    body = json.loads(m.response["content"])
    assert "verdict" in body and "detail" in body


def test_testnet_preset_matches_known_deployment():
    assert ep.testnet_chain_id() == _CHAIN_ID
    c = ep.testnet_contracts()
    assert set(c) == {"commerce", "router", "policy"}
    assert c["commerce"].lower() == _CONTRACTS["commerce"]


def test_negotiate_accepts_well_formed_request_and_signs():
    handler = ep.make_negotiation_handler(
        _dummy_wallet(), currency=_CURRENCY, chain_id=_CHAIN_ID,
        verifying_contract=_CONTRACTS["commerce"],
    )
    result = handler.negotiate(ep.sample_request("BTC"))
    assert result.accepted is True
    assert result.provider_sig.startswith("0x") and len(result.provider_sig) > 2
    assert result.response["terms"]["price"] == ep.DEFAULT_SERVICE_PRICE
    assert result.response["terms"]["currency"] == _CURRENCY


def test_negotiate_rejects_empty_quality_standards():
    from bnbagent.erc8183.negotiation import ReasonCode
    handler = ep.make_negotiation_handler(
        _dummy_wallet(), currency=_CURRENCY, chain_id=_CHAIN_ID,
        verifying_contract=_CONTRACTS["commerce"],
    )
    bad = ep.sample_request("BTC")
    bad["terms"]["quality_standards"] = ""   # present but empty -> AMBIGUOUS_TERMS
    result = handler.negotiate(bad)
    assert result.accepted is False
    assert result.response["reason_code"] == ReasonCode.AMBIGUOUS_TERMS


def test_job_anchor_round_trips_and_preserves_provider_sig():
    """The signed quote serializes into the exact on-chain createJob `description`
    (a compact Schema-v1 JSON) and parses back with price/currency/provider_sig
    intact — the payload a client anchors at createJob, verifiable by anyone."""
    from bnbagent.erc8183.negotiation import parse_job_description
    handler = ep.make_negotiation_handler(
        _dummy_wallet(), currency=_CURRENCY, chain_id=_CHAIN_ID,
        verifying_contract=_CONTRACTS["commerce"],
    )
    result = handler.negotiate(ep.sample_request("BTC"))
    anchor = ep.build_job_anchor(result)
    assert isinstance(anchor, str) and anchor.startswith("{")
    jd = parse_job_description(anchor)
    assert jd is not None
    assert jd.price == ep.DEFAULT_SERVICE_PRICE
    assert jd.currency == _CURRENCY
    assert jd.provider_sig == result.provider_sig


@pytest.mark.skipif(
    not os.environ.get("RUN_LIVE_ERC8183"),
    reason="live BSC-testnet RPC + PRIVATE_KEY required; set RUN_LIVE_ERC8183=1 to run",
)
def test_live_kernel_binding_smoke():
    provider = ep.DivergenceProvider.from_env()
    binding = provider.kernel_binding()
    assert binding["chain_id"] == _CHAIN_ID
    assert binding["dispute_window_s"] > 0
    assert binding["job_counter"] >= 0
    # the live quote + a signed negotiation also work end-to-end
    assert provider.quote_price() == ep.DEFAULT_SERVICE_PRICE
    assert provider.negotiate(ep.sample_request("BTC")).accepted is True
