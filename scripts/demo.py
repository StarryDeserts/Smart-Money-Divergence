"""90-second demo: run the live Skill path on a token and print the layered verdict.
Run: CMC_PRO_API_KEY=... python scripts/demo.py BTC
Falls back to a SyntheticProvider (a degraded demo signal) when no cached frame
exists, so a fresh clone runs with zero setup and never crashes."""
import os
import sys
from divergence.adapters.synthetic import resolve_provider
from divergence.skill.runtime import run_skill, DEFAULT_THETA


def main():
    token = sys.argv[1] if len(sys.argv) > 1 else "BTC"
    # Prefer the cached historical window (offline-safe); fall back to synthetic
    # data on a fresh clone. The live Skill swaps in LiveAdapter, same interface.
    provider, note = resolve_provider(token)
    if note:
        print(note, file=sys.stderr)
    theta_abs = float(os.environ.get("DIVERGENCE_THETA", DEFAULT_THETA))
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
