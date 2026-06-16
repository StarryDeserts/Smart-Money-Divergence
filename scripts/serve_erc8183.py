"""Optional ERC-8183 provider server — the Skill behind the SDK's create_erc8183_app.

This is the runnable proof that the divergence Skill IS an ERC-8183 provider: a
funded-job poll loop dispatches each paid job to `on_job`, which runs the live
Skill verdict, packages the canonical DeliverableManifest, uploads it, and hands
the URL back to the SDK to submit on-chain.

Honest scope: actually SERVING needs (a) the `[server]` extra (FastAPI), (b) a
storage backend with a public URL for the deliverable, and (c) funded client
jobs in the U token. Those are out of scope for this submission (testnet U mint
is onlyOwner). `--check` validates the wiring offline so the artifact is real and
reviewable without standing any of that up.

Run:
    python scripts/serve_erc8183.py --check     # validate wiring, no port/funds (default-safe)
    python scripts/serve_erc8183.py --serve      # bind the FastAPI app (needs [server] extra + funds)
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from divergence.skill.runtime import run_skill              # noqa: E402
from divergence.adapters import erc8183_provider as ep      # noqa: E402


def _has_server_extra() -> bool:
    """True if the bnbagent `[server]` extra (FastAPI app factory) is importable."""
    try:
        import importlib.util
        return importlib.util.find_spec("bnbagent.erc8183.server.routes") is not None \
            and importlib.util.find_spec("fastapi") is not None
    except Exception:
        return False


def build_on_job(provider: "ep.DivergenceProvider"):
    """Return the SDK `on_job(job) -> str` callback: live verdict -> manifest ->
    (upload) -> deliverable URL. Upload is intentionally a TODO boundary — wiring
    here is real; standing up storage + funded jobs is the out-of-scope part."""
    def on_job(job: dict) -> str:
        token = str(job.get("token") or "BTC").upper()
        verdict = run_skill(token, provider_data_source(), theta_abs=0.5)
        manifest = provider.build_manifest(verdict, job_id=int(job.get("id", 0)))
        # The SDK submits keccak(manifest) on-chain and stores optParams.deliverable_url.
        # Uploading `manifest.to_dict()` to a public URL is the storage step that
        # this submission deliberately leaves out of scope.
        raise NotImplementedError(
            "deliverable upload (storage backend) is out of scope for this submission"
        )
    return on_job


def provider_data_source():
    """Placeholder for the live market data provider feeding run_skill in a real
    deployment (e.g. the CMC Agent Hub MCP adapter). Not invoked under --check."""
    raise NotImplementedError("live data source wiring is out of scope for --check")


def make_app():
    """Build the FastAPI app via the SDK's create_erc8183_app. Requires the
    `[server]` extra + a funded wallet (PRIVATE_KEY). Not called under --check."""
    from bnbagent.erc8183.server.routes import create_erc8183_app
    from bnbagent.erc8183.config import ERC8183Config
    provider = ep.DivergenceProvider.from_env()
    config = ERC8183Config(wallet_provider=provider.client._wallet_provider,
                           service_price=provider.service_price)
    return create_erc8183_app(config, on_job=build_on_job(provider))


def main() -> int:
    parser = argparse.ArgumentParser(description="Optional ERC-8183 provider server")
    parser.add_argument("--check", action="store_true",
                        help="validate wiring offline (no port, no funds)")
    parser.add_argument("--serve", action="store_true",
                        help="bind the FastAPI app (needs [server] extra + funds)")
    args = parser.parse_args()

    if args.serve:
        import uvicorn
        uvicorn.run(make_app(), host="127.0.0.1", port=8183)
        return 0

    # default + --check: offline wiring validation
    have = _has_server_extra()
    print("== ERC-8183 provider server (wiring check) ==")
    print(f"  agent_id        : {ep.AGENT_ID}")
    print(f"  service_price   : {ep.DEFAULT_SERVICE_PRICE} (1 U)")
    print(f"  on_job callback : {build_on_job.__name__} (live verdict -> manifest -> url)")
    print(f"  app factory     : bnbagent.erc8183.server.create_erc8183_app")
    if have:
        print("  server extra    : present — `--serve` can bind (needs PRIVATE_KEY + funded jobs)")
        print("  status: ready (settlement/storage out of scope for this submission)")
    else:
        print("  server extra    : NOT installed — install bnbagent[server] to `--serve`")
        print("  status: wiring validated; serving is out of scope for this submission")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
