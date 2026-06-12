def select_universe(liquidity_at_start: dict[str, float], *, n: int = 25) -> list[str]:
    """Top-n tokens by liquidity measured at the START of the backtest window
    (avoids survivorship / look-ahead). Ties broken by token name ascending."""
    ordered = sorted(liquidity_at_start.items(), key=lambda kv: (-kv[1], kv[0]))
    return [tok for tok, _ in ordered[:n]]
