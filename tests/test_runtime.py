from datetime import date, timedelta
from divergence.types import Snapshot
from divergence.skill.runtime import run_skill, DEFAULT_THETA


class _Provider:
    def __init__(self, window): self._w = window
    def trailing_window(self, token, end, lookback): return self._w[-lookback:]


def _window(n=90, whale_last=10.0, fg_last=5.0):
    start = date(2025, 1, 1)
    out = []
    for i in range(n):
        last = i == n - 1
        out.append(Snapshot(token="BTC", day=start + timedelta(days=i), price=100.0,
                            whale_retail_flow=(whale_last if last else 0.0),
                            fear_greed=(fg_last if last else 50.0)))
    return out


def test_run_skill_returns_layered_output():
    out = run_skill("BTC", _Provider(_window()), theta_abs=0.5)
    assert isinstance(out["verdict"], str) and out["verdict"]            # Layer 1
    d = out["detail"]                                                     # Layer 2
    assert d["direction"] in {"long", "short", "flat"}
    assert "divergence" in d and "confidence" in d and "drivers" in d
    assert d["token"] == "BTC"


def test_run_skill_flags_degraded_when_hero_absent():
    w = _window()
    w = [Snapshot(token=s.token, day=s.day, price=s.price, fear_greed=s.fear_greed) for s in w]
    out = run_skill("BTC", _Provider(w), theta_abs=0.5)
    assert out["detail"]["degraded"] is True


def test_run_skill_long_when_whales_buy_into_fear():
    out = run_skill("BTC", _Provider(_window(whale_last=10.0, fg_last=5.0)), theta_abs=0.5)
    assert out["detail"]["direction"] == "long"


def test_default_theta_is_the_committed_calibration():
    assert DEFAULT_THETA == 1.444


def test_run_skill_uses_default_theta_when_omitted():
    # Omitting theta_abs must be identical to passing the committed default.
    w = _window()
    assert run_skill("BTC", _Provider(w)) == run_skill("BTC", _Provider(w), theta_abs=DEFAULT_THETA)


def test_degraded_detail_has_identical_keys_to_full():
    """Degraded mode must drop NO field — capital_score goes null, not absent — so a
    strongly-typed Go/Rust Unmarshal sees the same shape in both modes and can't panic."""
    full = run_skill("BTC", _Provider(_window()), theta_abs=0.5)["detail"]
    w = [Snapshot(token=s.token, day=s.day, price=s.price, fear_greed=s.fear_greed)
         for s in _window()]
    degraded = run_skill("BTC", _Provider(w), theta_abs=0.5)["detail"]
    assert degraded["degraded"] is True          # the degraded branch is genuinely exercised
    assert degraded["capital_score"] is None     # hero axis is null, not missing
    assert set(degraded) == set(full)            # identical key set — no field dropped
