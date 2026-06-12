from datetime import date, timedelta
from divergence.types import Snapshot


def make_window(n=90, *, token="TEST", price=100.0,
                whale=0.0, funding=0.0, oi=0.0, social=0.0, fg=50.0,
                whale_last=None, funding_last=None, social_last=None,
                fg_last=None, price_last=None):
    """Build a flat window of length n, optionally spiking the LAST day of a field
    so a causal z-score becomes strongly +/-. None for a field => that field is absent."""
    start = date(2025, 1, 1)
    out = []
    for i in range(n):
        last = (i == n - 1)
        out.append(Snapshot(
            token=token, day=start + timedelta(days=i),
            price=(price_last if (last and price_last is not None) else price),
            whale_retail_flow=None if whale is None else (whale_last if (last and whale_last is not None) else whale),
            funding_rate=None if funding is None else (funding_last if (last and funding_last is not None) else funding),
            open_interest=None if oi is None else oi,
            social_heat=None if social is None else (social_last if (last and social_last is not None) else social),
            fear_greed=None if fg is None else (fg_last if (last and fg_last is not None) else fg),
        ))
    return out


import pytest

@pytest.fixture
def make_window_fixture():
    return make_window
