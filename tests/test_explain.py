from datetime import date
from divergence.types import Signal, Driver
from divergence.explain import explain


def _sig(direction, drivers, degraded=False):
    return Signal(token="SOL", day=date(2025, 1, 1), divergence=-2.5, direction=direction,
                  confidence=0.7, capital_score=-1.8, crowd_score=0.7, drivers=drivers, degraded=degraded)


def test_explain_names_token_direction_and_top_driver():
    drivers = [Driver("whale_retail_flow", -1.8, "capital", "distributing"),
               Driver("fear_greed", 1.6, "crowd", "elevated")]
    text = explain(_sig("short", drivers))
    assert "SOL" in text
    assert "whales" in text.lower()
    assert "reduce" in text.lower() or "short" in text.lower()


def test_degraded_is_flagged_in_text():
    text = explain(_sig("short", [Driver("fear_greed", 1.6, "crowd", "elevated")], degraded=True))
    assert "mean-reversion" in text.lower() or "crowd-only" in text.lower()


def test_flat_reads_as_no_edge():
    text = explain(_sig("flat", []))
    assert "no" in text.lower()
