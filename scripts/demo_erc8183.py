"""Vertical C demo — the Smart-Money Divergence Skill as a priced ERC-8183 provider.

Deterministic and OFFLINE: a synthetic 90-day window drives the *exact* shipped
signal path (`run_skill`), the seller signs a price quote, and the verdict is
packaged into the canonical DeliverableManifest. The printed `manifest_hash` is
the exact bytes32 that `AgenticCommerce.submit(jobId, deliverable, optParams)`
would receive on BSC testnet (chain 97) — reproducible by anyone from the
manifest JSON.

Honest scope: this proves the PROVIDER half (negotiation + on-chain-exact
deliverable + identity). It does NOT settle a job — settlement needs the client
to fund escrow in the U token (testnet `mint` is onlyOwner; our wallet holds 0
U). The escrow round-trip (fund -> submit -> settle) is out of scope.

Run:
    python scripts/demo_erc8183.py            # offline, deterministic (video path)
    python scripts/demo_erc8183.py --token ETH
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from divergence.types import Snapshot                       # noqa: E402
from divergence.skill.runtime import run_skill              # noqa: E402
from divergence.adapters import erc8183_provider as ep      # noqa: E402


class _Provider:
    def __init__(self, window): self._w = window
    def trailing_window(self, token, end, lookback): return self._w[-lookback:]


def _synthetic_window(token: str, n: int = 90):
    """A fixed window where whales accumulate into peak fear on the last day —
    deterministic, so the demo's verdict + hash never drift between runs."""
    start = date(2025, 1, 1)
    out = []
    for i in range(n):
        last = i == n - 1
        out.append(Snapshot(token=token.upper(), day=start + timedelta(days=i),
                            price=100.0,
                            whale_retail_flow=(10.0 if last else 0.0),
                            fear_greed=(5.0 if last else 50.0)))
    return out


def build_demo_payload(token: str = "BTC", *, job_id: int = 0) -> dict:
    """Offline: synthetic verdict -> signed quote -> manifest. Returns the
    printable payload (no network, no wallet funds)."""
    verdict = run_skill(token, _Provider(_synthetic_window(token)), theta_abs=0.5)

    wallet = _demo_wallet()
    handler = ep.make_negotiation_handler(
        wallet,
        currency="0xc70B8741B8B07A6d61E54fd4B20f22Fa648E5565",   # U token (testnet)
        chain_id=ep.testnet_chain_id(),
        verifying_contract=ep.testnet_contracts()["commerce"],
    )
    quote = handler.negotiate(ep.sample_request(token))

    manifest = ep.build_deliverable_manifest(
        verdict, chain_id=ep.testnet_chain_id(),
        contracts=ep.testnet_contracts(), job_id=job_id,
    )
    return {
        "token": token.upper(),
        "verdict": verdict["verdict"],
        "quote_accepted": quote.accepted,
        "price": ep.DEFAULT_SERVICE_PRICE,
        "provider_sig": quote.provider_sig,
        "manifest_hash": "0x" + manifest.manifest_hash().hex(),
        "contracts": ep.testnet_contracts(),
        "chain_id": ep.testnet_chain_id(),
    }


def _demo_wallet():
    """Throwaway in-memory key — signs locally, holds no funds, never persisted."""
    from bnbagent import EVMWalletProvider
    return EVMWalletProvider(password="demo", private_key="0x" + "22" * 32, persist=False)


def main() -> int:
    parser = argparse.ArgumentParser(description="ERC-8183 priced-provider demo (offline)")
    parser.add_argument("--token", default="BTC")
    args = parser.parse_args()

    p = build_demo_payload(args.token)
    print("== Smart-Money Divergence as an ERC-8183 priced provider (BSC testnet, offline) ==")
    print(f"  token          : {p['token']}")
    print(f"  verdict        : {p['verdict']}")
    print(f"  price (quote)  : {p['price']} (1 U, 18 decimals)")
    print(f"  quote accepted : {p['quote_accepted']}  provider_sig={p['provider_sig'][:18]}...")
    print(f"  chain_id       : {p['chain_id']}")
    print(f"  contracts      : {json.dumps(p['contracts'])}")
    print(f"  manifest_hash={p['manifest_hash']}")
    print("  ^ exact bytes32 for AgenticCommerce.submit(jobId, deliverable, optParams)")
    print()
    print("  scope: provider half proven (signed quote + on-chain-exact deliverable +")
    print("         identity). Settlement is OUT OF SCOPE — the client must fund escrow")
    print("         in the U token (testnet mint is onlyOwner; this wallet holds 0 U).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
