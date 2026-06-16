"""The CLI's contract is its stdout: JSON ONLY, so JS/Go/Rust callers can pipe it
to a parser. resolve_provider is forced to the offline SyntheticProvider so the
test never depends on a cached `data/` frame or the network."""
import json

import cli
from divergence.adapters.synthetic import SyntheticProvider


def test_cli_prints_pure_json_to_stdout(capsys, monkeypatch):
    monkeypatch.setattr(cli, "resolve_provider",
                        lambda token, **kw: (SyntheticProvider(), "note->stderr"))
    rc = cli.main(["BTC"])
    assert rc == 0
    cap = capsys.readouterr()
    payload = json.loads(cap.out)                 # stdout must be parseable as-is
    assert set(payload) == {"verdict", "detail"}
    assert payload["detail"]["token"] == "BTC"
    assert "note->stderr" in cap.err              # the human note went to stderr, not stdout


def test_cli_no_arg_is_usage_error(capsys):
    rc = cli.main([])
    assert rc == 2
    cap = capsys.readouterr()
    assert cap.out == ""                          # nothing on stdout on error
    assert "usage" in cap.err.lower()
