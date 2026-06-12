from divergence.universe import select_universe


def test_picks_top_n_by_liquidity():
    liq = {"BTC": 9, "ETH": 8, "SOL": 7, "DOGE": 1}
    assert select_universe(liq, n=3) == ["BTC", "ETH", "SOL"]


def test_deterministic_tie_break_by_token():
    liq = {"AAA": 5, "BBB": 5, "CCC": 5}
    assert select_universe(liq, n=2) == ["AAA", "BBB"]  # value desc, then token asc


def test_n_larger_than_candidates_returns_all_sorted():
    liq = {"X": 1, "Y": 2}
    assert select_universe(liq, n=10) == ["Y", "X"]
