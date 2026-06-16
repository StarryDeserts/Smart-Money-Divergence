"""Cross-language entry point: print the Smart-Money-Divergence result as pure JSON.

    python scripts/cli.py BTC

stdout carries ONLY the JSON object ({"verdict": ..., "detail": {...}}), so
JS/Go/Rust callers can parse it directly (e.g. `python scripts/cli.py BTC | jq`).
All human notes and usage text go to stderr. Exit codes: 0 ok, 2 usage error."""
import json
import os
import sys
from divergence.adapters.synthetic import resolve_provider
from divergence.skill.runtime import run_skill, DEFAULT_THETA


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if not argv:
        print("usage: python scripts/cli.py <TOKEN>", file=sys.stderr)
        return 2
    token = argv[0]
    provider, note = resolve_provider(token)
    if note:
        print(note, file=sys.stderr)
    theta_abs = float(os.environ.get("DIVERGENCE_THETA", DEFAULT_THETA))
    out = run_skill(token, provider, theta_abs=theta_abs)
    json.dump(out, sys.stdout, separators=(",", ":"))
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
