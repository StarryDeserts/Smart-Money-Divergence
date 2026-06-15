"""90-second demo: run the live Skill path on a token and print the layered verdict.
Run: CMC_PRO_API_KEY=... python scripts/demo.py BTC
Falls back to the cached HistoricalAdapter window if no live key is set."""
import sys
from datetime import date
from divergence.adapters.cmc_client import CMCClient
from divergence.adapters.historical import HistoricalAdapter
from divergence.skill.runtime import run_skill


def main():
    token = sys.argv[1] if len(sys.argv) > 1 else "BTC"
    # Demo uses the cached historical window as the provider (offline-safe);
    # the live Skill swaps in LiveAdapter with the same interface.
    provider = HistoricalAdapter(CMCClient())
    # theta_abs is the committed E2 calibration (docs/.../2026-06-12-e2-gate.md): theta_abs=1.444.
    theta_abs = float(__import__("os").environ.get("DIVERGENCE_THETA", "1.444"))
    out = run_skill(token, provider, theta_abs=theta_abs)
    print(f"\n  VERDICT: {out['verdict']}\n")
    d = out["detail"]
    print(f"  direction={d['direction']}  |D|={abs(d['divergence']):.2f}  "
          f"confidence={d['confidence']:.2f}  degraded={d['degraded']}")
    print("  drivers:")
    for dr in d["drivers"]:
        print(f"    {dr['signal']:18} z={dr['z']:+.2f} ({dr['side']}, {dr['label']})")


if __name__ == "__main__":
    main()
