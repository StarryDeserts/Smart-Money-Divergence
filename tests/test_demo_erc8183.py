"""The demo must run fully offline (synthetic window, no CMC/RPC), exit 0, and
print a parseable, deterministic manifest hash line."""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _run():
    return subprocess.run(
        [sys.executable, "scripts/demo_erc8183.py"],
        cwd=ROOT, capture_output=True, text=True,
    )


def test_demo_runs_offline_and_prints_manifest_hash():
    r = _run()
    assert r.returncode == 0, r.stderr
    m = re.search(r"manifest_hash=0x([0-9a-fA-F]{64})", r.stdout)
    assert m is not None, r.stdout


def test_demo_hash_is_deterministic():
    a = _run().stdout
    b = _run().stdout
    ha = re.search(r"manifest_hash=0x[0-9a-fA-F]{64}", a).group(0)
    hb = re.search(r"manifest_hash=0x[0-9a-fA-F]{64}", b).group(0)
    assert ha == hb
