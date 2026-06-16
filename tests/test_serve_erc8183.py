"""The optional server wrapper must expose a `--check` mode that validates wiring
WITHOUT binding a port, touching the network, or needing funds. It exits 0 in
both cases (server extra present or absent) and reports which."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_serve_check_reports_wiring_and_exits_zero():
    r = subprocess.run(
        [sys.executable, "scripts/serve_erc8183.py", "--check"],
        cwd=ROOT, capture_output=True, text=True,
    )
    assert r.returncode == 0, r.stderr
    out = r.stdout.lower()
    assert "erc-8183" in out
    assert ("server extra" in out) or ("ready" in out)
