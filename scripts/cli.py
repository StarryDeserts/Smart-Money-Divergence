"""Cross-language entry point: print the Smart-Money-Divergence result as pure JSON.

    python scripts/cli.py BTC

stdout carries ONLY a single JSON object — on success {"verdict": ..., "detail": {...}},
on any runtime failure {"error": {"type", "message", "token"}}. It is NEVER a Python
traceback and NEVER contains non-RFC-8259 NaN/Infinity tokens, so JS/Go/Rust callers
can parse stdout directly (e.g. `python scripts/cli.py BTC | jq`). Human notes and
usage text go to stderr. Exit codes: 0 ok, 1 runtime error, 2 usage error."""
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
    try:
        provider, note = resolve_provider(token)
        if note:
            print(note, file=sys.stderr)
        theta_abs = float(os.environ.get("DIVERGENCE_THETA", DEFAULT_THETA))
        out = run_skill(token, provider, theta_abs=theta_abs)
        # Serialize to a STRING first with allow_nan=False: this raises on any NaN/Inf
        # BEFORE a byte reaches stdout, so dirty-data signals can't emit invalid JSON.
        text = json.dumps(out, separators=(",", ":"), allow_nan=False)
    except Exception as e:
        # Never leak a traceback onto stdout — downstream parsers get a typed error
        # object instead; the human gets the same line on stderr.
        print(f"error: {type(e).__name__}: {e}", file=sys.stderr)
        json.dump({"error": {"type": type(e).__name__, "message": str(e), "token": token}},
                  sys.stdout, separators=(",", ":"), allow_nan=False)
        sys.stdout.write("\n")
        return 1
    sys.stdout.write(text + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
