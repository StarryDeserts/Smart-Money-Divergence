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


def test_cli_emits_error_json_not_traceback(capsys, monkeypatch):
    """A provider that explodes must NOT leak a traceback to stdout — downstream
    parsers must still receive a single valid JSON object carrying an "error" key."""
    class _Boom:
        def trailing_window(self, *a, **k):
            raise RuntimeError("simulated dirty data")
    monkeypatch.setattr(cli, "resolve_provider", lambda token, **kw: (_Boom(), None))
    rc = cli.main(["BTC"])
    assert rc == 1
    cap = capsys.readouterr()
    payload = json.loads(cap.out)                 # stdout still parseable as-is
    assert set(payload) == {"error"}
    assert payload["error"]["type"] == "RuntimeError"
    assert payload["error"]["token"] == "BTC"


def test_cli_nan_signal_becomes_error_not_invalid_json(capsys, monkeypatch):
    """Dirty data that drives divergence to NaN must surface as a typed error object,
    never as a bare `NaN` token (which Go/Rust/strict-JS parsers reject)."""
    from datetime import date, timedelta
    from divergence.types import Snapshot

    class _NaNProvider:
        def trailing_window(self, token, end, lookback):
            start = date(2025, 1, 1)
            return [Snapshot(token=token, day=start + timedelta(days=i), price=100.0,
                             whale_retail_flow=None,
                             fear_greed=(float("nan") if i == lookback - 2 else 50.0))
                    for i in range(lookback)]
    monkeypatch.setattr(cli, "resolve_provider", lambda token, **kw: (_NaNProvider(), None))
    rc = cli.main(["BTC"])
    assert rc == 1
    cap = capsys.readouterr()
    assert "NaN" not in cap.out                    # no bare NaN token on the pipe
    payload = json.loads(cap.out)                  # strictly parseable
    assert payload["error"]["type"] == "ValueError"  # allow_nan=False raised pre-stdout
    assert payload["error"]["token"] == "BTC"
