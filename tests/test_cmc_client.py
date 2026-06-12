import pandas as pd
from divergence.adapters.cmc_client import CMCClient


class _FakeResp:
    def __init__(self, payload): self._p = payload; self.status_code = 200
    def raise_for_status(self): pass
    def json(self): return self._p


def test_get_json_calls_endpoint_with_key(monkeypatch):
    calls = {}
    def fake_get(url, headers=None, params=None, timeout=None):
        calls["url"] = url; calls["headers"] = headers; calls["params"] = params
        return _FakeResp({"data": [{"x": 1}]})
    monkeypatch.setattr("requests.get", fake_get)
    c = CMCClient(api_key="KEY", cache_dir=None)
    out = c.get_json("/v1/x", {"a": "b"})
    assert out["data"] == [{"x": 1}]
    assert calls["headers"]["X-CMC_PRO_API_KEY"] == "KEY"
    assert calls["params"]["a"] == "b"


def test_cache_round_trips_dataframe(tmp_path):
    c = CMCClient(api_key="KEY", cache_dir=tmp_path)
    df = pd.DataFrame({"day": ["2025-01-01"], "v": [1.0]})
    c.cache_put("BTC_price", df)
    again = c.cache_get("BTC_price")
    assert again is not None and again.iloc[0]["v"] == 1.0


def test_cache_get_missing_returns_none(tmp_path):
    c = CMCClient(api_key="KEY", cache_dir=tmp_path)
    assert c.cache_get("nope") is None
