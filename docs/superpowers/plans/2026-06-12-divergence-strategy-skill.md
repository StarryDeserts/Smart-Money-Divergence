# Smart-Money Divergence Strategy Skill — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a CMC Strategy Skill that flags divergence between crowd sentiment and real (whale-vs-retail) capital flow, backed by an honest backtest that shares its exact signal code path with the live Skill.

**Architecture:** A pure-function core (`signal_core`) consumes a trailing window of `Snapshot`s and emits a `Signal`. Two data adapters (historical CMC Pro for backtest, live Agent Hub for the Skill) emit the *identical* `Snapshot` schema, so the backtest is byte-for-byte the live logic. A lean backtest harness doubles as the E2 go/no-go instrument; the live Skill + report polish sit behind that gate.

**Tech Stack:** Python 3.11, numpy, pandas, pyarrow (parquet cache), requests (CMC Pro REST), pytest. Frozen dataclasses for the pure types. Conventional-commit messages, frequent commits.

**Source spec:** [`../specs/2026-06-12-divergence-strategy-skill-design.md`](../specs/2026-06-12-divergence-strategy-skill-design.md)

**Note on the E2 gate (DRY refinement of the spec timeline):** the spec's §11 timeline implies a throwaway "minimal E2 backtest" before the full harness. This plan instead builds the real-but-lean harness **once** (Phase 3) and runs E2 on it (Phase 4). Everything expensive and gate-dependent — the live Skill (Phase 5), report polish + robustness + demo (Phase 6), packaging (Phase 7) — stays behind the gate. If E2 is NO-GO, stop at Phase 4 and pivot per the spec's §10 decision framework.

---

## File Structure

```
pyproject.toml                     # deps + pytest config
.gitignore                         # data/, reports/, .env, __pycache__
README.md                          # (Phase 7) public-repo face
conftest.py                        # shared pytest fixtures (synthetic windows)
src/divergence/
  __init__.py
  types.py            # Snapshot, Driver, Score, Signal  (frozen dataclasses)
  universe.py         # select_universe() — liquidity at window START
  signal_core.py      # PURE: score_window(), decide(), calibrate_theta(), helpers
  explain.py          # Signal -> plain-language Layer-1 verdict
  adapters/
    __init__.py
    base.py           # SnapshotProvider protocol, assert_schema(), to_snapshot()
    cmc_client.py     # thin CMC Pro REST client + parquet cache
    fetch.py          # build_frame(): pull+join signals -> cached {token}_frame (E1)
    historical.py     # HistoricalAdapter: cached {token}_frame -> Snapshots
    live.py           # LiveAdapter (Agent Hub MCP) — Phase 5
  backtest/
    __init__.py
    simulate.py       # PURE: simulate() t+1 alignment + costs
    metrics.py        # sharpe, max_drawdown, hit_rate, turnover, buy&hold, attribution
    harness.py        # run_backtest(): calibrate -> evaluate -> simulate
    report.py         # write_report() artifacts (Phase 6)
    robustness.py     # sensitivity grid + subsample stability (Phase 6)
  skill/
    __init__.py
    runtime.py        # run_skill() -> layered output (Phase 5)
scripts/
  spike_e1_data.py    # E1 data-availability spike (Phase 2)
  run_backtest.py     # E2 + full backtest entrypoint (Phase 4)
  mine_demo_cases.py  # E4 demo case mining (Phase 6)
tests/
  test_types.py
  test_universe.py
  test_signal_core.py
  test_explain.py
  test_cmc_client.py
  test_adapters_contract.py
  test_historical.py
  test_simulate.py
  test_metrics.py
  test_harness.py
  test_live.py
  test_runtime.py
  test_robustness.py
data/                 # cached parquet (gitignored)
reports/              # generated reports (gitignored)
```

**Signature contract (locked — every task must match these exactly):**

```python
# types.py
@dataclass(frozen=True)
class Snapshot:
    token: str; day: date; price: float
    whale_retail_flow: float | None = None
    funding_rate: float | None = None
    open_interest: float | None = None
    social_heat: float | None = None
    fear_greed: float | None = None        # market-wide, broadcast per day

@dataclass(frozen=True)
class Driver:
    signal: str; z: float; side: str; label: str   # side in {"capital","crowd"}

@dataclass(frozen=True)
class Score:
    token: str; day: date; divergence: float
    capital_score: float | None; crowd_score: float | None
    drivers: list[Driver]; degraded: bool

@dataclass(frozen=True)
class Signal:
    token: str; day: date; divergence: float
    direction: str; confidence: float                # direction in {"long","short","flat"}
    capital_score: float | None; crowd_score: float | None
    drivers: list[Driver]; degraded: bool

# signal_core.py
def score_window(window: Sequence[Snapshot], *, lookback: int = 90) -> Score
def decide(score: Score, *, theta_abs: float, allow_short: bool = False) -> Signal
def calibrate_theta(d_values: Sequence[float], *, quantile: float = 0.8) -> float

# explain.py
def explain(signal: Signal, *, top_k: int = 3) -> str

# universe.py
def select_universe(liquidity_at_start: dict[str, float], *, n: int = 25) -> list[str]

# adapters/base.py
class SnapshotProvider(Protocol):
    def trailing_window(self, token: str, end: date | None, lookback: int) -> list[Snapshot]: ...
def assert_schema(s: Snapshot) -> None

# backtest/simulate.py
def simulate(positions: Sequence[float], asset_returns: Sequence[float], *, cost_bps: float) -> list[float]

# backtest/harness.py
def run_backtest(history: dict[str, list[Snapshot]], *, lookback: int = 90,
                 theta_quantile: float = 0.8, allow_short: bool = False,
                 cost_bps: float = 15.0, split: float = 0.65) -> "BacktestResult"

# skill/runtime.py
def run_skill(token: str, provider: SnapshotProvider, *, theta_abs: float,
              lookback: int = 90, allow_short: bool = False) -> dict
```

---

## Phase 0 — Scaffold + core types

### Task 1: Initialize repo + project scaffold

**Files:**
- Create: `pyproject.toml`, `.gitignore`, `conftest.py`, `src/divergence/__init__.py`, `tests/__init__.py`

- [ ] **Step 1: Initialize git and create the package skeleton**

```bash
cd /home/stardust/dev/bnb-hackthon
git init
mkdir -p src/divergence/adapters src/divergence/backtest src/divergence/skill scripts tests data reports
touch src/divergence/__init__.py src/divergence/adapters/__init__.py \
      src/divergence/backtest/__init__.py src/divergence/skill/__init__.py tests/__init__.py
```

- [ ] **Step 2: Write `pyproject.toml`**

```toml
[project]
name = "divergence"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = ["numpy>=1.26", "pandas>=2.1", "pyarrow>=14", "requests>=2.31"]

[project.optional-dependencies]
dev = ["pytest>=8.0"]

[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]
```

- [ ] **Step 3: Write `.gitignore`**

```gitignore
__pycache__/
*.pyc
.venv/
data/
reports/
.env
*.parquet
```

- [ ] **Step 4: Write `conftest.py` (shared synthetic-window fixture)**

```python
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
```

- [ ] **Step 5: Install dev deps and verify pytest runs**

Run: `python -m venv .venv && . .venv/bin/activate && pip install -e ".[dev]" && pytest -q`
Expected: pytest collects 0 tests, exits 0 ("no tests ran").

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml .gitignore conftest.py src tests
git commit -m "chore: scaffold divergence package + pytest"
```

---

### Task 2: Core types (`types.py`)

**Files:**
- Create: `src/divergence/types.py`
- Test: `tests/test_types.py`

- [ ] **Step 1: Write the failing test**

```python
from datetime import date
from divergence.types import Snapshot, Driver, Score, Signal


def test_snapshot_defaults_optional_fields_to_none():
    s = Snapshot(token="BTC", day=date(2025, 1, 1), price=42000.0)
    assert s.whale_retail_flow is None and s.fear_greed is None
    assert s.price == 42000.0


def test_types_are_frozen():
    s = Snapshot(token="BTC", day=date(2025, 1, 1), price=1.0)
    import dataclasses, pytest
    with pytest.raises(dataclasses.FrozenInstanceError):
        s.price = 2.0  # type: ignore[misc]


def test_signal_carries_direction_and_drivers():
    d = Driver(signal="whale_retail_flow", z=-1.8, side="capital", label="distributing")
    sig = Signal(token="BTC", day=date(2025, 1, 1), divergence=-2.0, direction="short",
                 confidence=0.7, capital_score=-1.8, crowd_score=0.2, drivers=[d], degraded=False)
    assert sig.direction == "short" and sig.drivers[0].side == "capital"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_types.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'divergence.types'`

- [ ] **Step 3: Write minimal implementation**

```python
from dataclasses import dataclass, field
from datetime import date


@dataclass(frozen=True)
class Snapshot:
    token: str
    day: date
    price: float
    whale_retail_flow: float | None = None
    funding_rate: float | None = None
    open_interest: float | None = None
    social_heat: float | None = None
    fear_greed: float | None = None


@dataclass(frozen=True)
class Driver:
    signal: str
    z: float
    side: str
    label: str


@dataclass(frozen=True)
class Score:
    token: str
    day: date
    divergence: float
    capital_score: float | None
    crowd_score: float | None
    drivers: list[Driver] = field(default_factory=list)
    degraded: bool = False


@dataclass(frozen=True)
class Signal:
    token: str
    day: date
    divergence: float
    direction: str
    confidence: float
    capital_score: float | None
    crowd_score: float | None
    drivers: list[Driver] = field(default_factory=list)
    degraded: bool = False
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_types.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add src/divergence/types.py tests/test_types.py
git commit -m "feat: core dataclasses Snapshot/Driver/Score/Signal"
```

---

### Task 3: Universe selection (`universe.py`)

**Files:**
- Create: `src/divergence/universe.py`
- Test: `tests/test_universe.py`

- [ ] **Step 1: Write the failing test**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_universe.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write minimal implementation**

```python
def select_universe(liquidity_at_start: dict[str, float], *, n: int = 25) -> list[str]:
    """Top-n tokens by liquidity measured at the START of the backtest window
    (avoids survivorship / look-ahead). Ties broken by token name ascending."""
    ordered = sorted(liquidity_at_start.items(), key=lambda kv: (-kv[1], kv[0]))
    return [tok for tok, _ in ordered[:n]]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_universe.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add src/divergence/universe.py tests/test_universe.py
git commit -m "feat: universe selection by start-of-window liquidity"
```

---

## Phase 1 — Pure core (safe to build regardless of E1/E2)

> This phase has **zero external dependency** — it is exercised entirely with synthetic windows from `conftest.py`. It is the credibility heart and is worth building first.

### Task 4: Z-score + momentum helpers (`signal_core.py` part 1)

**Files:**
- Create: `src/divergence/signal_core.py`
- Test: `tests/test_signal_core.py`

- [ ] **Step 1: Write the failing test**

```python
import numpy as np
from divergence.signal_core import _causal_z, _momentum_series


def test_causal_z_positive_when_last_value_spikes_up():
    series = [0.0] * 89 + [10.0]
    assert _causal_z(series) > 3.0


def test_causal_z_none_when_too_few_values():
    assert _causal_z([1.0]) is None
    assert _causal_z([None, None]) is None


def test_causal_z_zero_when_flat():
    assert _causal_z([5.0] * 10) == 0.0


def test_causal_z_ignores_none_gaps():
    assert _causal_z([None, 0.0, 0.0, 0.0, 4.0]) > 0.0


def test_momentum_series_is_k_day_returns():
    prices = [100.0, 100.0, 100.0, 110.0]  # k=2 -> returns at i>=2
    out = _momentum_series(prices, k=2)
    assert out[-1] == 0.10  # (110-100)/100 over last 2 days
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_signal_core.py -v`
Expected: FAIL — `ImportError: cannot import name '_causal_z'`

- [ ] **Step 3: Write minimal implementation**

```python
from collections.abc import Sequence
import numpy as np


def _causal_z(series: Sequence[float | None]) -> float | None:
    """Z-score of the most recent available value vs the window distribution.
    Causal: uses only values present in the window (no future data). None if <2 values."""
    vals = [float(v) for v in series if v is not None]
    if len(vals) < 2:
        return None
    arr = np.asarray(vals, dtype=float)
    sd = float(arr.std(ddof=0))
    if sd == 0.0:
        return 0.0
    return float((arr[-1] - arr.mean()) / sd)


def _momentum_series(prices: Sequence[float], k: int = 5) -> list[float]:
    """k-day trailing returns series, one value per day from index k onward."""
    p = list(prices)
    out: list[float] = []
    for i in range(k, len(p)):
        base = p[i - k]
        out.append((p[i] - base) / base if base else 0.0)
    return out
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_signal_core.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add src/divergence/signal_core.py tests/test_signal_core.py
git commit -m "feat: causal z-score and momentum helpers"
```

---

### Task 5: `score_window` — composites, divergence, degradation

**Files:**
- Modify: `src/divergence/signal_core.py`
- Test: `tests/test_signal_core.py`

Computes `capital_score` (hero whale-vs-retail only), `crowd_score` (mean of available standardized F&G / social / momentum / funding-OI crowding), `divergence = capital − crowd`, with the defined degradation path from spec §5.

- [ ] **Step 1: Write the failing tests**

```python
from conftest import make_window
from divergence.signal_core import score_window


def test_long_signal_when_whales_accumulate_into_crowd_fear():
    # whales spike up (accumulating) + fear&greed drops (fear) => capital>0, crowd<0 => D large +
    w = make_window(whale_last=10.0, fg_last=5.0)  # baseline whale=0, fg=50
    s = score_window(w)
    assert s.capital_score is not None and s.capital_score > 0
    assert s.crowd_score is not None and s.crowd_score < 0
    assert s.divergence > 0 and s.degraded is False


def test_short_signal_when_whales_distribute_into_crowd_greed():
    w = make_window(whale_last=-10.0, fg_last=95.0)
    s = score_window(w)
    assert s.divergence < 0 and s.degraded is False


def test_degraded_crowd_contrarian_when_hero_absent():
    # whale field entirely absent => capital unavailable => D = -crowd_score, degraded
    w = make_window(whale=None, fg_last=95.0)  # crowd greedy
    s = score_window(w)
    assert s.capital_score is None
    assert s.degraded is True
    assert s.divergence < 0  # -crowd_score, crowd greedy => negative => short bias


def test_crowd_score_renormalizes_over_available_inputs():
    # only fear_greed present on crowd side (social absent) -> crowd_score still computed
    w = make_window(whale=None, social=None, funding=None, oi=None, fg_last=95.0)
    s = score_window(w)
    assert s.crowd_score is not None


def test_flat_when_crowd_side_unavailable():
    # n=5 keeps the price series too short for momentum (needs >5 points), so with
    # fg/social/funding/oi all absent the crowd side genuinely evaporates to None.
    w = make_window(n=5, whale_last=10.0, fg=None, social=None, funding=None, oi=None)
    s = score_window(w)
    assert s.crowd_score is None
    assert s.divergence == 0.0


def test_drivers_tag_sides():
    w = make_window(whale_last=10.0, fg_last=95.0)
    s = score_window(w)
    sides = {d.signal: d.side for d in s.drivers}
    assert sides["whale_retail_flow"] == "capital"
    assert sides["fear_greed"] == "crowd"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_signal_core.py -k score_window -v` plus the new tests by name
Expected: FAIL — `ImportError: cannot import name 'score_window'`

- [ ] **Step 3: Write minimal implementation (append to `signal_core.py`)**

```python
from datetime import date
from .types import Snapshot, Driver, Score

_MOM_K = 5


def _field(window, name):
    return [getattr(s, name) for s in window]


def _mean(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


def score_window(window, *, lookback: int = 90) -> Score:
    w = list(window)[-lookback:]
    last = w[-1]

    capital_z = _causal_z(_field(w, "whale_retail_flow"))
    capital_score = capital_z  # hero only, no proxy

    fg_z = _causal_z(_field(w, "fear_greed"))
    social_z = _causal_z(_field(w, "social_heat"))
    funding_z = _causal_z(_field(w, "funding_rate"))
    oi_z = _causal_z(_field(w, "open_interest"))
    leverage_z = _mean([funding_z, oi_z])  # funding/OI crowding
    mom_series = _momentum_series(_field(w, "price"), k=_MOM_K)
    momentum_z = _causal_z(mom_series) if mom_series else None

    crowd_parts = [z for z in (fg_z, social_z, momentum_z, leverage_z) if z is not None]
    crowd_score = sum(crowd_parts) / len(crowd_parts) if crowd_parts else None

    degraded = False
    if capital_score is not None and crowd_score is not None:
        divergence = capital_score - crowd_score
    elif capital_score is None and crowd_score is not None:
        divergence = -crowd_score
        degraded = True
    else:
        divergence = 0.0

    drivers: list[Driver] = []
    if capital_z is not None:
        drivers.append(Driver("whale_retail_flow", capital_z, "capital",
                              "accumulating" if capital_z >= 0 else "distributing"))
    for name, z in (("fear_greed", fg_z), ("social_heat", social_z),
                    ("momentum", momentum_z), ("leverage", leverage_z)):
        if z is not None:
            drivers.append(Driver(name, z, "crowd", "elevated" if z >= 0 else "depressed"))
    drivers.sort(key=lambda d: abs(d.z), reverse=True)

    return Score(token=last.token, day=last.day, divergence=divergence,
                 capital_score=capital_score, crowd_score=crowd_score,
                 drivers=drivers, degraded=degraded)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_signal_core.py -v`
Expected: PASS (all score_window tests green)

- [ ] **Step 5: Commit**

```bash
git add src/divergence/signal_core.py tests/test_signal_core.py
git commit -m "feat: score_window composites, divergence, degradation path"
```

---

### Task 6: `calibrate_theta` — threshold from in-sample |D|

**Files:**
- Modify: `src/divergence/signal_core.py`
- Test: `tests/test_signal_core.py`

- [ ] **Step 1: Write the failing test**

```python
from divergence.signal_core import calibrate_theta


def test_theta_is_quantile_of_abs_divergence():
    ds = [-1.0, 1.0, -2.0, 2.0, -3.0, 3.0, -4.0, 4.0, -5.0, 5.0]
    # |D| = 1..5 each twice; 80th percentile ~ 4.x
    theta = calibrate_theta(ds, quantile=0.8)
    assert 4.0 <= theta <= 5.0


def test_theta_zero_for_empty():
    assert calibrate_theta([], quantile=0.8) == 0.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_signal_core.py -k theta -v`
Expected: FAIL — `ImportError: cannot import name 'calibrate_theta'`

- [ ] **Step 3: Write minimal implementation (append)**

```python
def calibrate_theta(d_values, *, quantile: float = 0.8) -> float:
    """Absolute |D| threshold at the given quantile of the in-sample divergence distribution.
    NOT tuned per token; one global number, calibrated in-sample only."""
    mags = [abs(float(d)) for d in d_values]
    if not mags:
        return 0.0
    return float(np.quantile(mags, quantile))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_signal_core.py -k theta -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add src/divergence/signal_core.py tests/test_signal_core.py
git commit -m "feat: calibrate_theta from in-sample |D| quantile"
```

---

### Task 7: `decide` — action + confidence given threshold

**Files:**
- Modify: `src/divergence/signal_core.py`
- Test: `tests/test_signal_core.py`

- [ ] **Step 1: Write the failing tests**

```python
from datetime import date
from divergence.types import Score
from divergence.signal_core import decide


def _score(d, *, degraded=False):
    return Score(token="BTC", day=date(2025, 1, 1), divergence=d,
                 capital_score=None if degraded else 1.0,
                 crowd_score=-d if degraded else 0.0, drivers=[], degraded=degraded)


def test_long_when_d_exceeds_theta():
    sig = decide(_score(3.0), theta_abs=2.0)
    assert sig.direction == "long" and sig.confidence > 0


def test_flat_when_below_theta():
    sig = decide(_score(1.0), theta_abs=2.0)
    assert sig.direction == "flat" and sig.confidence == 0.0


def test_negative_d_is_flat_when_long_only():
    sig = decide(_score(-3.0), theta_abs=2.0, allow_short=False)
    assert sig.direction == "flat"


def test_negative_d_is_short_when_allowed():
    sig = decide(_score(-3.0), theta_abs=2.0, allow_short=True)
    assert sig.direction == "short"


def test_degraded_caps_confidence():
    full = decide(_score(4.0), theta_abs=2.0).confidence
    deg = decide(_score(4.0, degraded=True), theta_abs=2.0).confidence
    assert deg < full
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_signal_core.py -k decide -v`
Expected: FAIL — `ImportError: cannot import name 'decide'`

- [ ] **Step 3: Write minimal implementation (append)**

```python
from .types import Signal

_DEGRADED_CONF_FACTOR = 0.6


def decide(score: Score, *, theta_abs: float, allow_short: bool = False) -> Signal:
    d = score.divergence
    if theta_abs > 0 and d >= theta_abs:
        direction = "long"
    elif theta_abs > 0 and d <= -theta_abs:
        direction = "short" if allow_short else "flat"
    else:
        direction = "flat"

    if direction == "flat":
        confidence = 0.0
    else:
        confidence = min(1.0, abs(d) / (2.0 * theta_abs)) if theta_abs > 0 else 1.0
        if score.degraded:
            confidence *= _DEGRADED_CONF_FACTOR

    return Signal(token=score.token, day=score.day, divergence=d, direction=direction,
                  confidence=confidence, capital_score=score.capital_score,
                  crowd_score=score.crowd_score, drivers=score.drivers, degraded=score.degraded)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_signal_core.py -v`
Expected: PASS (all signal_core tests green)

- [ ] **Step 5: Commit**

```bash
git add src/divergence/signal_core.py tests/test_signal_core.py
git commit -m "feat: decide() action + confidence with degraded cap"
```

---

### Task 8: `explain` — Layer-1 plain-language verdict

**Files:**
- Create: `src/divergence/explain.py`
- Test: `tests/test_explain.py`

- [ ] **Step 1: Write the failing test**

```python
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
    assert "distributing" in text.lower()  # whale z=-1.8 < 0 => distributing, not accumulating
    assert "reduce" in text.lower() or "short" in text.lower()


def test_degraded_is_flagged_in_text():
    text = explain(_sig("short", [Driver("fear_greed", 1.6, "crowd", "elevated")], degraded=True))
    assert "mean-reversion" in text.lower() or "crowd-only" in text.lower()


def test_flat_reads_as_no_edge():
    text = explain(_sig("flat", []))
    assert "no" in text.lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_explain.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write minimal implementation**

```python
from .types import Signal

_PHRASES = {
    "whale_retail_flow": {"capital": ("whales distributing", "whales accumulating")},
    "fear_greed": ("crowd fearful", "crowd greedy"),
    "social_heat": ("social quiet", "social hot"),
    "momentum": ("price weak", "price chasing"),
    "leverage": ("longs light", "longs crowded"),
}
_VERB = {"long": "accumulate / long", "short": "reduce / short", "flat": "no edge — stand aside"}


def _phrase(signal_name: str, z: float) -> str:
    spec = _PHRASES.get(signal_name)
    if spec is None:
        return signal_name
    pair = spec["capital"] if isinstance(spec, dict) else spec
    return pair[1] if z >= 0 else pair[0]


def explain(signal: Signal, *, top_k: int = 3) -> str:
    if signal.direction == "flat":
        return f"{signal.token}: signals aligned, no edge — stand aside."
    reasons = ", ".join(_phrase(d.signal, d.z) for d in signal.drivers[:top_k])
    tag = " (crowd-only mean-reversion mode)" if signal.degraded else ""
    return (f"{signal.token} — {reasons}. Divergence |{signal.divergence:.1f}|"
            f" → bias: {_VERB[signal.direction]}{tag}.")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_explain.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add src/divergence/explain.py tests/test_explain.py
git commit -m "feat: explain() Layer-1 plain-language verdict"
```

---

## Phase 2 — Data access + E1 spike

> **E1 variation points** (endpoint paths / JSON field names) are written as concrete `_PATH` / `_FIELD` constants with the documented CMC Pro defaults. If the E1 spike (Task 12) reveals different paths, change the constant — not the logic. A concrete default with a single named change-point is not a placeholder.

### Task 9: CMC Pro REST client + parquet cache (`cmc_client.py`)

**Files:**
- Create: `src/divergence/adapters/cmc_client.py`
- Test: `tests/test_cmc_client.py`

- [ ] **Step 1: Write the failing test (network mocked, cache exercised)**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_cmc_client.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write minimal implementation**

```python
from __future__ import annotations
import os
from pathlib import Path
import pandas as pd
import requests

_BASE = "https://pro-api.coinmarketcap.com"
# --- E1 variation points (confirm in Task 12) ---
PATHS = {
    "fear_greed": "/v3/fear-and-greed/historical",
    "ohlcv": "/v2/cryptocurrency/ohlcv/historical",
    # whale-vs-retail / on-chain holder distribution endpoint — CONFIRM in E1:
    "whale_retail": "/v4/dex/networks/holders/historical",
}


class CMCClient:
    def __init__(self, api_key: str | None = None, cache_dir: Path | None = Path("data")):
        self.api_key = api_key or os.environ.get("CMC_PRO_API_KEY", "")
        self.cache_dir = Path(cache_dir) if cache_dir else None
        if self.cache_dir:
            self.cache_dir.mkdir(parents=True, exist_ok=True)

    def get_json(self, path: str, params: dict) -> dict:
        resp = requests.get(_BASE + path,
                            headers={"X-CMC_PRO_API_KEY": self.api_key, "Accept": "application/json"},
                            params=params, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def cache_get(self, key: str) -> pd.DataFrame | None:
        if not self.cache_dir:
            return None
        f = self.cache_dir / f"{key}.parquet"
        return pd.read_parquet(f) if f.exists() else None

    def cache_put(self, key: str, df: pd.DataFrame) -> None:
        if self.cache_dir:
            df.to_parquet(self.cache_dir / f"{key}.parquet", index=False)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_cmc_client.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add src/divergence/adapters/cmc_client.py tests/test_cmc_client.py
git commit -m "feat: CMC Pro REST client with parquet cache"
```

---

### Task 10: Provider contract (`adapters/base.py`)

**Files:**
- Create: `src/divergence/adapters/base.py`
- Test: `tests/test_adapters_contract.py`

- [ ] **Step 1: Write the failing test**

```python
from datetime import date
import pytest
from divergence.types import Snapshot
from divergence.adapters.base import assert_schema, SnapshotProvider


def test_assert_schema_accepts_valid_snapshot():
    assert_schema(Snapshot(token="BTC", day=date(2025, 1, 1), price=1.0))


def test_assert_schema_rejects_bad_price():
    with pytest.raises(ValueError):
        assert_schema(Snapshot(token="BTC", day=date(2025, 1, 1), price=float("nan")))


def test_assert_schema_rejects_empty_token():
    with pytest.raises(ValueError):
        assert_schema(Snapshot(token="", day=date(2025, 1, 1), price=1.0))


def test_a_fake_provider_satisfies_the_protocol():
    class Fake:
        def trailing_window(self, token, end, lookback):
            return [Snapshot(token=token, day=date(2025, 1, 1), price=1.0)]
    f: SnapshotProvider = Fake()
    assert len(f.trailing_window("BTC", None, 90)) == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_adapters_contract.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write minimal implementation**

```python
from __future__ import annotations
import math
from datetime import date
from typing import Protocol, runtime_checkable
from ..types import Snapshot


@runtime_checkable
class SnapshotProvider(Protocol):
    def trailing_window(self, token: str, end: date | None, lookback: int) -> list[Snapshot]: ...


def assert_schema(s: Snapshot) -> None:
    """Boundary validation — both adapters MUST emit snapshots that pass this.
    This is what guarantees backtest == live at the data seam."""
    if not s.token:
        raise ValueError("snapshot.token must be non-empty")
    if s.price is None or math.isnan(s.price) or s.price <= 0:
        raise ValueError(f"snapshot.price must be positive, got {s.price}")
    for name in ("whale_retail_flow", "funding_rate", "open_interest", "social_heat", "fear_greed"):
        v = getattr(s, name)
        if v is not None and math.isnan(float(v)):
            raise ValueError(f"snapshot.{name} is NaN; use None for absent")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_adapters_contract.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add src/divergence/adapters/base.py tests/test_adapters_contract.py
git commit -m "feat: SnapshotProvider protocol + boundary schema assertion"
```

---

### Task 11: HistoricalAdapter (`adapters/historical.py`)

**Files:**
- Create: `src/divergence/adapters/historical.py`
- Test: `tests/test_historical.py`

Builds per-token time-ordered `Snapshot`s from cached frames, exposes `trailing_window` (for live-parity scoring) and `daterange`/`history` (for the backtest). Network fetching is delegated to `CMCClient`; tests use pre-seeded cache frames so they run offline.

- [ ] **Step 1: Write the failing test**

```python
from datetime import date
import pandas as pd
from divergence.adapters.cmc_client import CMCClient
from divergence.adapters.historical import HistoricalAdapter
from divergence.adapters.base import assert_schema


def _seed(client, token):
    days = pd.date_range("2025-01-01", periods=5, freq="D").date
    client.cache_put(f"{token}_frame", pd.DataFrame({
        "day": days, "price": [10, 11, 12, 13, 14],
        "whale_retail_flow": [1, -1, 2, -2, 3], "funding_rate": [0.01]*5,
        "open_interest": [100]*5, "social_heat": [5]*5, "fear_greed": [40, 50, 60, 70, 80],
    }))


def test_history_returns_schema_valid_ordered_snapshots(tmp_path):
    c = CMCClient(api_key="K", cache_dir=tmp_path); _seed(c, "BTC")
    a = HistoricalAdapter(c)
    hist = a.history("BTC")
    assert [s.day for s in hist] == sorted(s.day for s in hist)
    for s in hist:
        assert_schema(s)
    assert hist[0].fear_greed == 40


def test_trailing_window_is_causal_slice(tmp_path):
    c = CMCClient(api_key="K", cache_dir=tmp_path); _seed(c, "BTC")
    a = HistoricalAdapter(c)
    win = a.trailing_window("BTC", end=date(2025, 1, 3), lookback=90)
    assert win[-1].day == date(2025, 1, 3)
    assert all(s.day <= date(2025, 1, 3) for s in win)  # no future rows


def test_missing_optional_column_becomes_none(tmp_path):
    c = CMCClient(api_key="K", cache_dir=tmp_path)
    days = pd.date_range("2025-01-01", periods=3, freq="D").date
    c.cache_put("ETH_frame", pd.DataFrame({"day": days, "price": [1, 2, 3], "fear_greed": [40, 50, 60]}))
    a = HistoricalAdapter(c)
    hist = a.history("ETH")
    assert all(s.whale_retail_flow is None for s in hist)  # column absent -> None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_historical.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write minimal implementation**

```python
from __future__ import annotations
from datetime import date
import math
import pandas as pd
from ..types import Snapshot
from .cmc_client import CMCClient

_OPT = ("whale_retail_flow", "funding_rate", "open_interest", "social_heat", "fear_greed")


def _cell(row, name):
    if name not in row or pd.isna(row[name]):
        return None
    return float(row[name])


class HistoricalAdapter:
    """Reads a per-token cached 'frame' (one row/day) into Snapshots.
    Frame is populated by fetch_* (CMC Pro); tests seed the cache directly."""

    def __init__(self, client: CMCClient):
        self.client = client

    def _frame(self, token: str) -> pd.DataFrame:
        df = self.client.cache_get(f"{token}_frame")
        if df is None:
            raise FileNotFoundError(f"no cached frame for {token}; run fetch first")
        return df.sort_values("day").reset_index(drop=True)

    def history(self, token: str) -> list[Snapshot]:
        df = self._frame(token)
        out: list[Snapshot] = []
        for _, row in df.iterrows():
            d = row["day"]
            out.append(Snapshot(token=token, day=d if isinstance(d, date) else pd.to_datetime(d).date(),
                                price=float(row["price"]),
                                **{k: _cell(row, k) for k in _OPT}))
        return out

    def trailing_window(self, token: str, end: date | None, lookback: int) -> list[Snapshot]:
        hist = self.history(token)
        if end is not None:
            hist = [s for s in hist if s.day <= end]
        return hist[-lookback:]

    def daterange(self, token: str) -> list[date]:
        return [s.day for s in self.history(token)]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_historical.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add src/divergence/adapters/historical.py tests/test_historical.py
git commit -m "feat: HistoricalAdapter cached-frame -> Snapshots + causal window"
```

---

### Task 12: E1 data-availability spike + E3 differentiation note (EXPLORATORY — gate input)

> This is a **spike**, not TDD. It produces a decision (which fallback tier from spec §6) and seeds the real cache. Time-box ~0.5–1 day.

**Files:**
- Create: `scripts/spike_e1_data.py`
- Create: `docs/superpowers/notes/2026-06-12-e1-data-availability.md`
- Create: `docs/superpowers/notes/2026-06-12-e3-differentiation.md`

- [ ] **Step 1: Write the spike script (fetch + report availability for 5 tokens)**

```python
"""E1 spike: probe CMC Pro history depth for the hero + supporting signals.
Run: CMC_PRO_API_KEY=... python scripts/spike_e1_data.py
Prints, per token, how many daily rows each signal returns and the date span."""
import os, sys
from divergence.adapters.cmc_client import CMCClient, PATHS

TOKENS = ["BTC", "ETH", "SOL", "BNB", "DOGE"]


def probe(client, path, params, label):
    try:
        js = client.get_json(path, params)
        data = js.get("data", js)
        n = len(data) if hasattr(data, "__len__") else "?"
        print(f"  {label:16} rows={n}")
    except Exception as e:  # spike: we WANT to see which endpoints fail
        print(f"  {label:16} ERROR {type(e).__name__}: {e}")


def main():
    c = CMCClient()
    if not c.api_key:
        sys.exit("set CMC_PRO_API_KEY")
    for t in TOKENS:
        print(t)
        probe(c, PATHS["fear_greed"], {"start": 1, "limit": 500}, "fear_greed")
        probe(c, PATHS["ohlcv"], {"symbol": t, "count": 500, "interval": "daily"}, "ohlcv")
        probe(c, PATHS["whale_retail"], {"symbol": t, "count": 500}, "whale_retail(hero)")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run the spike**

Run: `CMC_PRO_API_KEY=<key> python scripts/spike_e1_data.py`
Observe: per-signal row counts + which endpoints error.

- [ ] **Step 3: Record the decision in the E1 note**

Capture in `docs/superpowers/notes/2026-06-12-e1-data-availability.md`:
- Row count + date span for each signal × token.
- **Chosen fallback tier** (Green / Amber / Red per spec §6).
- Confirmed Skill delivery format for Agent Hub (used in Phase 5).
- Any endpoint-path corrections to apply to `PATHS` / `_OPT`.

- [ ] **Step 4: Record the E3 differentiation scan**

In `docs/superpowers/notes/2026-06-12-e3-differentiation.md`: skim DoraHacks submissions / past CMC-hackathon winners; note how many use F&G/momentum/sentiment vs whale-vs-retail framing. Conclusion: is "smart-money divergence" a distinct hook? If crowded → flag the C7 generator escalation.

- [ ] **Step 5: Write the frame assembler (`adapters/fetch.py`) and cache real `{token}_frame`s**

This is the glue that turns raw endpoints into the per-token daily frame `HistoricalAdapter` reads. Extractors are concrete for the **documented** CMC response shapes and flagged as E1 variation points — if Step 2 showed a different JSON layout, fix the extractor body; the frame schema stays fixed. Includes the **Binance funding-history fallback** the spec §6 requires.

```python
from __future__ import annotations
import pandas as pd
from .cmc_client import CMCClient, PATHS

# --- E1 variation points: response-shape extractors. Fix bodies if Step 2's
# probe shows a different layout; downstream frame schema is fixed. ---

def _ohlcv_frame(client: CMCClient, token: str) -> pd.DataFrame:
    js = client.get_json(PATHS["ohlcv"], {"symbol": token, "count": 500, "interval": "daily"})
    quotes = js["data"]["quotes"]                       # [{time_close, quote:{USD:{close}}}]
    return pd.DataFrame([{"day": pd.to_datetime(q["time_close"]).date(),
                          "price": float(q["quote"]["USD"]["close"])} for q in quotes])

def _fear_greed_frame(client: CMCClient) -> pd.DataFrame:
    js = client.get_json(PATHS["fear_greed"], {"start": 1, "limit": 500})
    return pd.DataFrame([{"day": pd.to_datetime(int(d["timestamp"]), unit="s").date(),
                          "fear_greed": float(d["value"])} for d in js["data"]])   # market-wide

def _whale_frame(client: CMCClient, token: str) -> pd.DataFrame:
    js = client.get_json(PATHS["whale_retail"], {"symbol": token, "count": 500})
    data = js.get("data", []) or []
    return pd.DataFrame([{"day": pd.to_datetime(d["timestamp"]).date(),
                          "whale_retail_flow": float(d["net_whale_flow"])} for d in data])

def _funding_frame(client: CMCClient, token: str) -> pd.DataFrame:
    try:                                                # CMC derivatives first ...
        js = client.get_json("/v1/derivatives/funding-rate/historical",
                             {"symbol": token, "count": 500})
        return pd.DataFrame([{"day": pd.to_datetime(d["timestamp"]).date(),
                              "funding_rate": float(d["funding_rate"]),
                              "open_interest": float(d.get("open_interest", "nan"))}
                             for d in js["data"]])
    except Exception:                                   # ... Binance funding history fallback (§6)
        return _binance_funding_frame(token)

def _binance_funding_frame(token: str) -> pd.DataFrame:
    import requests
    r = requests.get("https://fapi.binance.com/fapi/v1/fundingRate",
                     params={"symbol": f"{token}USDT", "limit": 1000}, timeout=30)
    r.raise_for_status()
    df = pd.DataFrame([{"day": pd.to_datetime(int(x["fundingTime"]), unit="ms").date(),
                        "funding_rate": float(x["fundingRate"])} for x in r.json()])
    return df.groupby("day", as_index=False)["funding_rate"].mean() if not df.empty else df


def build_frame(client: CMCClient, token: str) -> pd.DataFrame:
    """Outer-join all available signals into one row/day frame and cache it as {token}_frame.
    A signal that errors or is empty is simply left out -> HistoricalAdapter renders it None,
    and signal_core takes its degradation path. social_heat is optional and omitted by default."""
    frame = _ohlcv_frame(client, token)
    for part in (_fear_greed_frame(client), _whale_frame(client, token), _funding_frame(client, token)):
        try:
            if part is not None and not part.empty:
                frame = frame.merge(part, on="day", how="left")
        except Exception:
            continue                                    # spike tolerance: skip a broken signal
    frame = frame.sort_values("day").reset_index(drop=True)
    client.cache_put(f"{token}_frame", frame)
    return frame
```

Append to `scripts/spike_e1_data.py` a `--build` path that caches frames for the confirmed-history tokens:

```python
def build(tokens):
    c = CMCClient()
    from divergence.adapters.fetch import build_frame
    for t in tokens:
        df = build_frame(c, t)
        cols = [col for col in df.columns if col not in ("day", "price")]
        print(f"{t}: {len(df)} rows, signals present = {cols}")
```

Run: `CMC_PRO_API_KEY=<key> python -c "from scripts.spike_e1_data import build; build(['BTC','ETH','SOL','BNB','DOGE'])"`
Expected: writes `data/<TOKEN>_frame.parquet` for each token and prints which signals landed (the input to the Green/Amber/Red tier call).

- [ ] **Step 6: Apply any path corrections + commit**

```bash
git add scripts/spike_e1_data.py src/divergence/adapters/fetch.py docs/superpowers/notes/ src/divergence/adapters/cmc_client.py
git commit -m "chore: E1 spike + frame assembler (CMC + Binance funding fallback), lock tier"
```

**GATE NOTE:** if E1 shows **no usable hero history**, proceed in the **Amber/Red** tier — the backtest runs in degraded crowd-contrarian mode (already supported by `score_window`); the hero is demonstrated live in Phase 5 + as a case study. No code redesign needed.

---

## Phase 3 — Backtest engine + metrics

### Task 13: `simulate` — t+1 position alignment + costs (PURE)

**Files:**
- Create: `src/divergence/backtest/simulate.py`
- Test: `tests/test_simulate.py`

This is half of the no-look-ahead proof: a position decided at day `t` earns the return from `t → t+1`, and each change in position pays cost. (The other half — that the *signal* at `t` ignores future data — is proven by the `_causal_z` / `trailing_window` tests.)

- [ ] **Step 1: Write the failing tests**

```python
import pytest
from divergence.backtest.simulate import simulate


def test_position_earns_next_day_return():
    # position[0]=1 applies to return[1]; no cost if no change from implicit prior 0... see cost test
    rets = simulate(positions=[1.0, 1.0], asset_returns=[0.0, 0.05], cost_bps=0.0)
    assert rets[1] == pytest.approx(0.05)


def test_no_lookahead_first_day_has_no_prior_return():
    rets = simulate(positions=[1.0], asset_returns=[0.99], cost_bps=0.0)
    # only one day: position can't earn a t->t+1 return -> strategy return 0 that day
    assert rets[0] == 0.0


def test_cost_charged_on_position_change():
    # enter (0->1) then exit (1->0); flat returns; cost 100bps each turn
    rets = simulate(positions=[1.0, 0.0], asset_returns=[0.0, 0.0], cost_bps=100.0)
    assert rets[0] == pytest.approx(-0.01)   # 0->1 turnover 1.0 * 100bps
    assert rets[1] == pytest.approx(-0.01)   # 1->0 turnover 1.0 * 100bps


def test_length_mismatch_raises():
    with pytest.raises(ValueError):
        simulate(positions=[1.0, 1.0], asset_returns=[0.0], cost_bps=0.0)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_simulate.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write minimal implementation**

```python
from collections.abc import Sequence


def simulate(positions: Sequence[float], asset_returns: Sequence[float], *, cost_bps: float) -> list[float]:
    """Daily net strategy returns. positions[t] is the position held entering day t+1,
    so it earns asset_returns[t+1]. Cost charged on |positions[t] - positions[t-1]| (prior = 0)."""
    if len(positions) != len(asset_returns):
        raise ValueError("positions and asset_returns must be equal length")
    cost = cost_bps / 10_000.0
    out: list[float] = []
    prev = 0.0
    for t in range(len(positions)):
        turn = abs(positions[t] - prev)
        pnl = positions[t - 1] * asset_returns[t] if t > 0 else 0.0
        out.append(pnl - turn * cost)
        prev = positions[t]
    return out
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_simulate.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add src/divergence/backtest/simulate.py tests/test_simulate.py
git commit -m "feat: pure simulate() with t+1 alignment and turnover costs"
```

---

### Task 14: Metrics (`backtest/metrics.py`)

**Files:**
- Create: `src/divergence/backtest/metrics.py`
- Test: `tests/test_metrics.py`

- [ ] **Step 1: Write the failing tests**

```python
import pytest
from divergence.backtest.metrics import sharpe, max_drawdown, hit_rate, turnover, equity_curve


def test_sharpe_zero_for_no_variance():
    assert sharpe([0.0, 0.0, 0.0]) == 0.0


def test_sharpe_positive_for_steady_gains():
    assert sharpe([0.01, 0.012, 0.009, 0.011], periods_per_year=252) > 0


def test_max_drawdown_is_worst_peak_to_trough():
    eq = [1.0, 1.2, 0.9, 1.1]   # peak 1.2 -> trough 0.9 = -0.25
    assert max_drawdown(eq) == pytest.approx(-0.25)


def test_hit_rate_fraction_positive_among_nonzero():
    assert hit_rate([0.01, -0.02, 0.0, 0.03]) == pytest.approx(2 / 3)


def test_turnover_sums_position_changes():
    assert turnover([0.0, 1.0, 1.0, 0.0]) == pytest.approx(2.0)


def test_equity_curve_compounds():
    eq = equity_curve([0.0, 0.1, -0.5])
    assert eq[-1] == pytest.approx(1.0 * 1.1 * 0.5)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_metrics.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write minimal implementation**

```python
from collections.abc import Sequence
import numpy as np


def equity_curve(returns: Sequence[float]) -> list[float]:
    eq, v = [], 1.0
    for r in returns:
        v *= (1.0 + r)
        eq.append(v)
    return eq


def sharpe(returns: Sequence[float], *, periods_per_year: int = 252) -> float:
    a = np.asarray(returns, dtype=float)
    sd = a.std(ddof=0)
    if sd == 0:
        return 0.0
    return float((a.mean() / sd) * np.sqrt(periods_per_year))


def max_drawdown(equity: Sequence[float]) -> float:
    peak, mdd = -np.inf, 0.0
    for v in equity:
        peak = max(peak, v)
        mdd = min(mdd, v / peak - 1.0)
    return float(mdd)


def hit_rate(returns: Sequence[float]) -> float:
    nz = [r for r in returns if r != 0.0]
    if not nz:
        return 0.0
    return sum(1 for r in nz if r > 0) / len(nz)


def turnover(positions: Sequence[float]) -> float:
    prev, total = 0.0, 0.0
    for p in positions:
        total += abs(p - prev)
        prev = p
    return float(total)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_metrics.py -v`
Expected: PASS (6 passed)

- [ ] **Step 5: Commit**

```bash
git add src/divergence/backtest/metrics.py tests/test_metrics.py
git commit -m "feat: backtest metrics (sharpe, drawdown, hit-rate, turnover, equity)"
```

---

### Task 15: Harness (`backtest/harness.py`) — calibrate → evaluate → simulate

**Files:**
- Create: `src/divergence/backtest/harness.py`
- Test: `tests/test_harness.py`

Drives a `{token: [Snapshot]}` history through `score_window` to calibrate θ **on the in-sample split only**, evaluates every day with `decide`, maps direction→position (long=+1, short=−1, flat=0, scaled by confidence), and runs `simulate`. Returns a `BacktestResult` with in-sample / out-of-sample metrics + per-day signals + per-signal attribution.

- [ ] **Step 1: Write the failing tests**

```python
from datetime import date, timedelta
from divergence.types import Snapshot
from divergence.backtest.harness import run_backtest, BacktestResult


def _series(token, n, *, whale_fn, price_fn, fg=50.0):
    start = date(2025, 1, 1)
    return [Snapshot(token=token, day=start + timedelta(days=i), price=price_fn(i),
                     whale_retail_flow=whale_fn(i), fear_greed=fg) for i in range(n)]


def test_runs_and_splits_in_and_out_of_sample():
    # whales lead price: when whale>0 today, price rises tomorrow -> strategy should not be empty
    hist = {"BTC": _series("BTC", 200,
                           whale_fn=lambda i: 1.0 if i % 4 == 0 else -1.0,
                           price_fn=lambda i: 100.0 * (1.01 ** i))}
    res = run_backtest(hist, lookback=30, theta_quantile=0.7, cost_bps=5.0, split=0.65)
    assert isinstance(res, BacktestResult)
    assert res.theta_abs >= 0
    assert res.oos_metrics["n_days"] > 0
    assert "whale_retail_flow" in res.attribution


def test_theta_calibrated_on_in_sample_only(monkeypatch):
    # if OOS leaked into calibration, theta would change; guard by construction:
    hist = {"BTC": _series("BTC", 120, whale_fn=lambda i: float((-1) ** i), price_fn=lambda i: 100.0 + i)}
    res = run_backtest(hist, lookback=20, split=0.5)
    assert res.in_sample_days + res.oos_days == res.total_days
    assert res.in_sample_days > 0 and res.oos_days > 0


def test_flat_strategy_when_theta_huge_has_zero_turnover():
    hist = {"BTC": _series("BTC", 100, whale_fn=lambda i: 0.0, price_fn=lambda i: 100.0)}
    res = run_backtest(hist, lookback=20, theta_quantile=0.999)
    assert res.oos_metrics["turnover"] == 0.0


def test_benchmark_is_equal_weight_buy_and_hold_same_days():
    hist = {"BTC": _series("BTC", 120, whale_fn=lambda i: float((-1) ** i), price_fn=lambda i: 100.0 + i)}
    res = run_backtest(hist, lookback=20, split=0.6)
    assert res.oos_benchmark["n_days"] == res.oos_metrics["n_days"]
    assert "total_return" in res.oos_benchmark and "sharpe" in res.oos_benchmark


def test_no_lookahead_future_prices_do_not_change_in_sample():
    # THE central no-look-ahead evidence test (spec §8): tamper the FUTURE, assert the past is untouched.
    base = _series("BTC", 120, whale_fn=lambda i: float((-1) ** i), price_fn=lambda i: 100.0 + i)
    r1 = run_backtest({"BTC": base}, lookback=20, split=0.6)
    tampered = base[:-10] + [Snapshot(token="BTC", day=s.day, price=s.price * 100,
                                      whale_retail_flow=s.whale_retail_flow, fear_greed=s.fear_greed)
                             for s in base[-10:]]
    r2 = run_backtest({"BTC": tampered}, lookback=20, split=0.6)
    assert r2.theta_abs == r1.theta_abs       # theta calibrated in-sample only -> unaffected
    assert r2.is_metrics == r1.is_metrics     # in-sample signals depend only on past data
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_harness.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write minimal implementation**

```python
from __future__ import annotations
from dataclasses import dataclass, field
import numpy as np
from ..signal_core import score_window, decide, calibrate_theta
from .simulate import simulate
from .metrics import sharpe, max_drawdown, hit_rate, turnover, equity_curve


@dataclass
class BacktestResult:
    theta_abs: float
    total_days: int
    in_sample_days: int
    oos_days: int
    is_metrics: dict
    oos_metrics: dict
    is_benchmark: dict                                  # equal-weight buy&hold, same days
    oos_benchmark: dict                                 # the §7 "vs a real benchmark" headline pair
    signals: list = field(default_factory=list)        # (token, Signal) out-of-sample
    attribution: dict = field(default_factory=dict)


def _position(sig) -> float:
    base = {"long": 1.0, "short": -1.0, "flat": 0.0}[sig.direction]
    return base * sig.confidence


def _daily_returns(snaps):
    out = [0.0]
    for i in range(1, len(snaps)):
        p0 = snaps[i - 1].price
        out.append((snaps[i].price - p0) / p0 if p0 else 0.0)
    return out


def _metrics(positions, rets, cost_bps):
    strat = simulate(positions, rets, cost_bps=cost_bps)
    eq = equity_curve(strat)
    return {"n_days": len(strat), "sharpe": sharpe(strat), "max_drawdown": max_drawdown(eq),
            "hit_rate": hit_rate(strat), "turnover": turnover(positions),
            "total_return": (eq[-1] - 1.0) if eq else 0.0}, strat


def run_backtest(history, *, lookback=90, theta_quantile=0.8, allow_short=False,
                 cost_bps=15.0, split=0.65) -> BacktestResult:
    # 1) score every day per token (causal windows)
    per_token = {}
    for token, snaps in history.items():
        snaps = sorted(snaps, key=lambda s: s.day)
        scores, rets = [], _daily_returns(snaps)
        for i in range(len(snaps)):
            scores.append(score_window(snaps[: i + 1], lookback=lookback))
        per_token[token] = (snaps, scores, rets)

    # 2) global in-sample cut (by index fraction of the longest series)
    total = max(len(v[0]) for v in per_token.values())
    cut = int(total * split)

    # 3) calibrate theta on in-sample |D| only
    in_d = [sc.divergence for (_, scores, _) in per_token.values() for sc in scores[:cut]]
    theta = calibrate_theta(in_d, quantile=theta_quantile)

    # 4) evaluate -> positions, split metrics, attribution
    is_pos, is_ret, oos_pos, oos_ret, oos_signals = [], [], [], [], []
    attr_num, attr_den = {}, {}
    for token, (snaps, scores, rets) in per_token.items():
        for i, sc in enumerate(scores):
            sig = decide(sc, theta_abs=theta, allow_short=allow_short)
            pos = _position(sig)
            if i < cut:
                is_pos.append(pos); is_ret.append(rets[i])
            else:
                oos_pos.append(pos); oos_ret.append(rets[i]); oos_signals.append((token, sig))
                fwd = rets[i + 1] if i + 1 < len(rets) else 0.0
                for d in sc.drivers:
                    attr_num[d.signal] = attr_num.get(d.signal, 0.0) + np.sign(d.z) * pos * fwd
                    attr_den[d.signal] = attr_den.get(d.signal, 0) + 1

    is_metrics, _ = _metrics(is_pos, is_ret, cost_bps)
    oos_metrics, _ = _metrics(oos_pos, oos_ret, cost_bps)
    # benchmark: equal-weight, always-long buy&hold over the SAME days, no rebalance cost.
    # (positions all 1.0; per-token series each begin with a 0.0 return, so concatenation
    #  never bleeds one token's position into another's first day — same as the strategy path.)
    is_bench, _ = _metrics([1.0] * len(is_ret), is_ret, cost_bps=0.0)
    oos_bench, _ = _metrics([1.0] * len(oos_ret), oos_ret, cost_bps=0.0)
    attribution = {k: attr_num[k] / attr_den[k] for k in attr_num if attr_den[k]}

    return BacktestResult(theta_abs=theta, total_days=total, in_sample_days=cut,
                          oos_days=total - cut, is_metrics=is_metrics, oos_metrics=oos_metrics,
                          is_benchmark=is_bench, oos_benchmark=oos_bench,
                          signals=oos_signals, attribution=attribution)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_harness.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Run the full suite**

Run: `pytest -q`
Expected: all green.

- [ ] **Step 6: Commit**

```bash
git add src/divergence/backtest/harness.py tests/test_harness.py
git commit -m "feat: backtest harness — in-sample theta calibration, OOS eval, attribution"
```

---

## Phase 4 — E2 GO/NO-GO gate

> **This is the project's hinge.** Everything after Phase 4 (live Skill, report polish, demo, packaging) is justified ONLY if E2 clears the bar. The harness from Phase 3 is the instrument — there is no throwaway code here, just the first *real-data* run of it. Time-box ~1 day.

### Task 16: E2 backtest entrypoint + decision checkpoint

**Files:**
- Create: `scripts/run_backtest.py`
- Create: `docs/superpowers/notes/2026-06-12-e2-gate.md`
- (depends on the real cache seeded in Task 12)

- [ ] **Step 1: Write the entrypoint that loads the cached universe and runs the harness**

```python
"""E2 entrypoint: build history from cached frames, run the backtest, print the gate scorecard.
Run: python scripts/run_backtest.py --tokens BTC,ETH,SOL,... [--allow-short]
Prereq: Task 12 spike has populated data/<TOKEN>_frame.parquet."""
import argparse
from divergence.adapters.cmc_client import CMCClient
from divergence.adapters.historical import HistoricalAdapter
from divergence.backtest.harness import run_backtest


def load_history(tokens):
    client = CMCClient()
    adapter = HistoricalAdapter(client)
    history, missing = {}, []
    for t in tokens:
        try:
            history[t] = adapter.history(t)
        except FileNotFoundError:
            missing.append(t)
    if missing:
        print(f"WARNING: no cached frame for {missing} (run scripts/spike_e1_data.py first)")
    return history


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tokens", default="BTC,ETH,SOL,BNB,DOGE")
    ap.add_argument("--allow-short", action="store_true")
    ap.add_argument("--lookback", type=int, default=90)
    ap.add_argument("--theta-quantile", type=float, default=0.8)
    ap.add_argument("--cost-bps", type=float, default=15.0)
    ap.add_argument("--split", type=float, default=0.65)
    args = ap.parse_args()

    history = load_history([t.strip() for t in args.tokens.split(",")])
    if not history:
        raise SystemExit("no usable history — cannot run E2")

    res = run_backtest(history, lookback=args.lookback, theta_quantile=args.theta_quantile,
                       allow_short=args.allow_short, cost_bps=args.cost_bps, split=args.split)

    print("\n=== E2 GATE SCORECARD ===")
    print(f"tokens={list(history)}  theta_abs={res.theta_abs:.3f}  "
          f"days IS/OOS={res.in_sample_days}/{res.oos_days}")
    for label, m in (("IN-SAMPLE", res.is_metrics), ("OUT-OF-SAMPLE", res.oos_metrics),
                     ("OOS BUY&HOLD", res.oos_benchmark)):
        print(f"  {label:13} sharpe={m['sharpe']:+.2f}  total_return={m['total_return']:+.1%}  "
              f"max_dd={m['max_drawdown']:+.1%}  hit={m['hit_rate']:.0%}  turnover={m['turnover']:.1f}")
    print("  attribution (OOS mean signed contribution):")
    for sig, v in sorted(res.attribution.items(), key=lambda kv: -abs(kv[1])):
        print(f"    {sig:18} {v:+.4f}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run E2 on the real cached data**

Run: `python scripts/run_backtest.py --tokens <the universe Task 12 confirmed has history>`
Observe: the out-of-sample scorecard + attribution table.

- [ ] **Step 3: Apply the gate criteria and record the verdict**

Write `docs/superpowers/notes/2026-06-12-e2-gate.md` with the scorecard and a GO / NO-GO call against the spec §10 bar:

- **GO** if, out-of-sample, the divergence rule beats buy-&-hold *risk-adjusted* (higher Sharpe **or** materially smaller drawdown for comparable return) **and** the hero/edge signal carries a non-trivial share of the attribution — i.e., the result is explainable, not noise.
- **Conditional GO (Amber)** if the edge is weak but the *framework* is sound and explainable (acceptable per spec §C1 — value is the honest framework, not magic PnL). Proceed, but the narrative leads with method + honesty, and the report foregrounds the negative/limit findings.
- **NO-GO** if the rule is indistinguishable from noise AND offers no explanatory value. Then pivot per spec §10: either (a) reframe as an *analytical/explainability* tool (drop PnL claims entirely), or (b) escalate to the C7 strategy-generator framing. Do **not** proceed to Phase 5 as a PnL strategy.

- [ ] **Step 4: Commit the gate decision**

```bash
git add scripts/run_backtest.py docs/superpowers/notes/2026-06-12-e2-gate.md
git commit -m "feat: E2 backtest entrypoint + gate verdict"
```

**STOP HERE if NO-GO.** Re-enter the brainstorming/spec loop for the chosen pivot before writing any Phase 5+ code.

---

## Phase 5 — Live Skill (gated: only if E2 ≥ Conditional GO)

> The whole architecture exists so this phase reuses the **exact** `score_window` / `decide` / `explain` code the backtest validated. The LiveAdapter is the only new logic, and it must emit snapshots that pass the same `assert_schema`.

### Task 17: LiveAdapter (`adapters/live.py`)

**Files:**
- Create: `src/divergence/adapters/live.py`
- Test: `tests/test_live.py`

Pulls the most recent `lookback` days for one token from the live source (CMC Pro REST today; swappable to Agent Hub MCP) and returns schema-valid `Snapshot`s. Tests inject a fake fetch callable so they run offline and assert the contract, not the network.

- [ ] **Step 1: Write the failing test**

```python
from datetime import date
import pytest
from divergence.types import Snapshot
from divergence.adapters.base import assert_schema, SnapshotProvider
from divergence.adapters.live import LiveAdapter


def _fake_rows():
    # source returns newest-first; adapter must sort ascending and coerce to Snapshot
    return [
        {"day": date(2025, 1, 2), "price": 11.0, "whale_retail_flow": 2.0, "fear_greed": 55.0},
        {"day": date(2025, 1, 1), "price": 10.0, "whale_retail_flow": 1.0, "fear_greed": 50.0},
    ]


def test_live_adapter_returns_sorted_schema_valid_snapshots():
    a = LiveAdapter(fetch=lambda token, lookback: _fake_rows())
    win = a.trailing_window("BTC", end=None, lookback=90)
    assert [s.day for s in win] == [date(2025, 1, 1), date(2025, 1, 2)]
    for s in win:
        assert_schema(s)
    assert win[-1].whale_retail_flow == 2.0


def test_live_adapter_satisfies_provider_protocol():
    a = LiveAdapter(fetch=lambda token, lookback: _fake_rows())
    p: SnapshotProvider = a
    assert isinstance(a, SnapshotProvider)


def test_missing_optional_keys_become_none():
    a = LiveAdapter(fetch=lambda token, lookback: [{"day": date(2025, 1, 1), "price": 10.0}])
    win = a.trailing_window("BTC", end=None, lookback=90)
    assert win[0].social_heat is None and win[0].whale_retail_flow is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_live.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write minimal implementation**

```python
from __future__ import annotations
from collections.abc import Callable
from datetime import date
from ..types import Snapshot
from .base import assert_schema

_OPT = ("whale_retail_flow", "funding_rate", "open_interest", "social_heat", "fear_greed")
Row = dict
FetchFn = Callable[[str, int], list[Row]]


def _to_snapshot(token: str, row: Row) -> Snapshot:
    return Snapshot(token=token, day=row["day"], price=float(row["price"]),
                    **{k: (None if row.get(k) is None else float(row[k])) for k in _OPT})


class LiveAdapter:
    """Live provider for the Skill runtime. `fetch(token, lookback) -> list[dict rows]`
    is injected so the transport (CMC Pro REST today, Agent Hub MCP later) is swappable
    without touching the signal path. Emits the SAME schema the backtest consumed."""

    def __init__(self, fetch: FetchFn):
        self._fetch = fetch

    def trailing_window(self, token: str, end: date | None, lookback: int) -> list[Snapshot]:
        rows = self._fetch(token, lookback)
        snaps = sorted((_to_snapshot(token, r) for r in rows), key=lambda s: s.day)
        if end is not None:
            snaps = [s for s in snaps if s.day <= end]
        for s in snaps:
            assert_schema(s)
        return snaps[-lookback:]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_live.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add src/divergence/adapters/live.py tests/test_live.py
git commit -m "feat: LiveAdapter with injectable fetch, schema-validated snapshots"
```

---

### Task 18: Skill runtime (`skill/runtime.py`) — layered output

**Files:**
- Create: `src/divergence/skill/runtime.py`
- Test: `tests/test_runtime.py`

`run_skill` ties a provider → `score_window` → `decide` → `explain` and returns the C6 layered output: a retail-facing **verdict** (Layer 1) plus a structured **detail** block (Layer 2: divergence, direction, confidence, scores, ranked drivers, degraded flag). This dict is what the CMC Skill returns to the Agent Hub.

- [ ] **Step 1: Write the failing tests**

```python
from datetime import date, timedelta
from divergence.types import Snapshot
from divergence.skill.runtime import run_skill


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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_runtime.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write minimal implementation**

```python
from __future__ import annotations
from ..signal_core import score_window, decide
from ..explain import explain


def _driver_dict(d) -> dict:
    return {"signal": d.signal, "z": round(d.z, 3), "side": d.side, "label": d.label}


def run_skill(token, provider, *, theta_abs: float, lookback: int = 90,
              allow_short: bool = False) -> dict:
    """Live Skill entrypoint. Reuses the exact backtested signal path.
    Returns C6 layered output: Layer-1 verdict string + Layer-2 structured detail."""
    window = provider.trailing_window(token, None, lookback)
    score = score_window(window, lookback=lookback)
    signal = decide(score, theta_abs=theta_abs, allow_short=allow_short)
    return {
        "verdict": explain(signal),
        "detail": {
            "token": signal.token,
            "day": signal.day.isoformat(),
            "direction": signal.direction,
            "divergence": round(signal.divergence, 3),
            "confidence": round(signal.confidence, 3),
            "capital_score": (None if signal.capital_score is None else round(signal.capital_score, 3)),
            "crowd_score": (None if signal.crowd_score is None else round(signal.crowd_score, 3)),
            "drivers": [_driver_dict(d) for d in signal.drivers],
            "degraded": signal.degraded,
        },
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_runtime.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add src/divergence/skill/runtime.py tests/test_runtime.py
git commit -m "feat: run_skill layered output reusing backtested signal path"
```

---

## Phase 6 — Report, robustness, demo cases (gated)

> Judges score "technical execution" and "demo." This phase turns the validated harness into evidence: an honest report, a robustness check that pre-empts the "you overfit" critique, and 2-3 concrete demo cases.

### Task 19: Robustness — sensitivity grid + subsample stability (`backtest/robustness.py`)

**Files:**
- Create: `src/divergence/backtest/robustness.py`
- Test: `tests/test_robustness.py`

Re-runs `run_backtest` across a small grid of the ~3 knobs (θ-quantile, lookback, cost) and across leave-one-token-out subsamples, returning OOS Sharpe for each so the report can show the edge is not a single lucky setting. **This is the anti-overfit evidence.**

- [ ] **Step 1: Write the failing tests**

```python
from datetime import date, timedelta
from divergence.types import Snapshot
from divergence.backtest.robustness import sensitivity_grid, leave_one_out


def _hist(tokens=("BTC", "ETH"), n=160):
    start = date(2025, 1, 1)
    h = {}
    for j, t in enumerate(tokens):
        h[t] = [Snapshot(token=t, day=start + timedelta(days=i), price=100.0 * (1.005 ** i),
                         whale_retail_flow=1.0 if (i + j) % 3 == 0 else -1.0, fear_greed=50.0)
                for i in range(n)]
    return h


def test_sensitivity_grid_covers_all_combos():
    grid = sensitivity_grid(_hist(), thetas=[0.7, 0.8], lookbacks=[20, 30], costs=[5.0])
    assert len(grid) == 4                       # 2 * 2 * 1
    for row in grid:
        assert "oos_sharpe" in row and "theta_quantile" in row


def test_leave_one_out_drops_each_token_once():
    loo = leave_one_out(_hist(("BTC", "ETH", "SOL")), lookback=20)
    assert len(loo) == 3
    assert {r["held_out"] for r in loo} == {"BTC", "ETH", "SOL"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_robustness.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write minimal implementation**

```python
from __future__ import annotations
from itertools import product
from .harness import run_backtest


def sensitivity_grid(history, *, thetas, lookbacks, costs, allow_short=False, split=0.65):
    """OOS Sharpe across the knob grid. A robust edge stays positive across most cells;
    a fragile one is positive in only a lucky corner."""
    rows = []
    for q, lb, c in product(thetas, lookbacks, costs):
        res = run_backtest(history, lookback=lb, theta_quantile=q,
                           allow_short=allow_short, cost_bps=c, split=split)
        rows.append({"theta_quantile": q, "lookback": lb, "cost_bps": c,
                     "oos_sharpe": res.oos_metrics["sharpe"],
                     "oos_return": res.oos_metrics["total_return"]})
    return rows


def leave_one_out(history, *, lookback=90, theta_quantile=0.8, cost_bps=15.0,
                  allow_short=False, split=0.65):
    """Drop each token once; the edge should survive removing any single name."""
    out = []
    for held in history:
        sub = {k: v for k, v in history.items() if k != held}
        if not sub:
            continue
        res = run_backtest(sub, lookback=lookback, theta_quantile=theta_quantile,
                           allow_short=allow_short, cost_bps=cost_bps, split=split)
        out.append({"held_out": held, "oos_sharpe": res.oos_metrics["sharpe"],
                    "oos_return": res.oos_metrics["total_return"]})
    return out
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_robustness.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add src/divergence/backtest/robustness.py tests/test_robustness.py
git commit -m "feat: robustness — sensitivity grid + leave-one-out stability"
```

---

### Task 20: Report writer (`backtest/report.py`) + E4 demo cases

**Files:**
- Create: `src/divergence/backtest/report.py`
- Create: `scripts/mine_demo_cases.py`
- Test: `tests/test_report.py`

`write_report` serializes a `BacktestResult` + robustness rows into a Markdown scorecard (committed to `reports/`, NOT gitignored — it is evidence). `mine_demo_cases.py` (E4, exploratory) scans OOS signals for the cleanest 2-3 illustrative divergence calls for the demo narrative.

- [ ] **Step 1: Write the failing test (report is pure string-building)**

```python
from divergence.backtest.harness import BacktestResult
from divergence.backtest.report import render_report


def _result():
    return BacktestResult(theta_abs=1.5, total_days=200, in_sample_days=130, oos_days=70,
                          is_metrics={"sharpe": 1.2, "total_return": 0.3, "max_drawdown": -0.1,
                                      "hit_rate": 0.55, "turnover": 12.0, "n_days": 130},
                          oos_metrics={"sharpe": 0.8, "total_return": 0.15, "max_drawdown": -0.12,
                                       "hit_rate": 0.52, "turnover": 7.0, "n_days": 70},
                          is_benchmark={"sharpe": 0.6, "total_return": 0.2, "max_drawdown": -0.2,
                                        "hit_rate": 0.5, "turnover": 1.0, "n_days": 130},
                          oos_benchmark={"sharpe": 0.4, "total_return": 0.1, "max_drawdown": -0.25,
                                         "hit_rate": 0.5, "turnover": 1.0, "n_days": 70},
                          signals=[], attribution={"whale_retail_flow": 0.012, "fear_greed": 0.004})


def test_render_report_includes_oos_and_attribution():
    md = render_report(_result(), sensitivity=[{"theta_quantile": 0.8, "lookback": 90,
                       "cost_bps": 15.0, "oos_sharpe": 0.8, "oos_return": 0.15}])
    assert "Out-of-sample" in md or "OUT-OF-SAMPLE" in md
    assert "buy&hold" in md          # benchmark row present (§7 vs-a-real-benchmark)
    assert "whale_retail_flow" in md
    assert "0.8" in md  # the oos sharpe shows up
    assert "Sensitivity" in md or "sensitivity" in md


def test_render_report_flags_degraded_or_honest_limits():
    md = render_report(_result(), sensitivity=[], notes="Edge weak OOS; framework-first per C1.")
    assert "framework-first" in md
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_report.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write minimal implementation**

```python
from __future__ import annotations
from pathlib import Path


def _metrics_row(label, m):
    return (f"| {label} | {m['sharpe']:+.2f} | {m['total_return']:+.1%} | "
            f"{m['max_drawdown']:+.1%} | {m['hit_rate']:.0%} | {m['turnover']:.1f} | {m['n_days']} |")


def render_report(result, *, sensitivity=None, notes: str = "") -> str:
    lines = ["# Divergence Strategy — Backtest Report", "",
             f"**θ (abs divergence threshold):** {result.theta_abs:.3f}  ",
             f"**Days (in-sample / out-of-sample):** {result.in_sample_days} / {result.oos_days}",
             "", "## Performance", "",
             "| Split | Sharpe | Return | Max DD | Hit | Turnover | Days |",
             "|---|---|---|---|---|---|---|",
             _metrics_row("In-sample", result.is_metrics),
             _metrics_row("Out-of-sample", result.oos_metrics),
             _metrics_row("OOS buy&hold", result.oos_benchmark), "",
             "_Headline = OOS strategy vs OOS buy&hold (risk-adjusted)._", "",
             "## Signal attribution (OOS mean signed contribution)", ""]
    for sig, v in sorted(result.attribution.items(), key=lambda kv: -abs(kv[1])):
        lines.append(f"- `{sig}`: {v:+.4f}")
    if sensitivity:
        lines += ["", "## Sensitivity (robustness across knobs)", "",
                  "| θ-quantile | lookback | cost(bps) | OOS Sharpe | OOS Return |",
                  "|---|---|---|---|---|"]
        for r in sensitivity:
            lines.append(f"| {r['theta_quantile']} | {r['lookback']} | {r['cost_bps']} | "
                         f"{r['oos_sharpe']:+.2f} | {r['oos_return']:+.1%} |")
    if notes:
        lines += ["", "## Honest limitations", "", notes]
    return "\n".join(lines) + "\n"


def write_report(result, path="reports/backtest_report.md", *, sensitivity=None, notes="") -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(render_report(result, sensitivity=sensitivity, notes=notes), encoding="utf-8")
    return p
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_report.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Write the E4 demo-mining script (exploratory, no test)**

```python
"""E4: surface the cleanest 2-3 demo cases from an OOS backtest run.
Run: python scripts/mine_demo_cases.py --tokens BTC,ETH,SOL,...
Prints the highest-conviction non-degraded calls + their plain-language verdict, for the demo script."""
import argparse
from divergence.adapters.cmc_client import CMCClient
from divergence.adapters.historical import HistoricalAdapter
from divergence.backtest.harness import run_backtest
from divergence.explain import explain


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tokens", default="BTC,ETH,SOL,BNB,DOGE")
    ap.add_argument("--top", type=int, default=5)
    args = ap.parse_args()
    adapter = HistoricalAdapter(CMCClient())
    history = {t.strip(): adapter.history(t.strip()) for t in args.tokens.split(",")}
    res = run_backtest(history)
    ranked = sorted(res.signals, key=lambda ts: abs(ts[1].divergence), reverse=True)
    print("=== candidate demo cases (highest |divergence| OOS) ===")
    for token, sig in ranked[: args.top]:
        flag = " [degraded]" if sig.degraded else ""
        print(f"\n{token} {sig.day} dir={sig.direction} |D|={abs(sig.divergence):.2f}{flag}")
        print(f"  {explain(sig)}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 6: Generate the report + mine cases, then commit**

```bash
python -c "from divergence.adapters.cmc_client import CMCClient; from divergence.adapters.historical import HistoricalAdapter; from divergence.backtest.harness import run_backtest; from divergence.backtest.robustness import sensitivity_grid; from divergence.backtest.report import write_report; a=HistoricalAdapter(CMCClient()); h={t:a.history(t) for t in ['BTC','ETH','SOL','BNB','DOGE']}; r=run_backtest(h); s=sensitivity_grid(h, thetas=[0.7,0.8,0.9], lookbacks=[60,90], costs=[15.0]); print(write_report(r, sensitivity=s))"
python scripts/mine_demo_cases.py --tokens BTC,ETH,SOL,BNB,DOGE
git add src/divergence/backtest/report.py tests/test_report.py scripts/mine_demo_cases.py reports/backtest_report.md
git commit -m "feat: backtest report writer + E4 demo-case mining"
```

---

## Phase 7 — Package + submit (gated)

> Final mile: make the repo legible to a judge in 90 seconds, wire the Skill manifest for the Agent Hub, and submit to DoraHacks by **2026-06-21**.

### Task 21: README, Skill manifest, demo script, submission

**Files:**
- Create: `README.md`
- Create: `skill/manifest.json` (or the CMC Agent-Hub Skill descriptor confirmed in Task 12)
- Create: `scripts/demo.py`
- Create: `docs/superpowers/notes/2026-06-12-submission-checklist.md`

- [ ] **Step 1: Write `scripts/demo.py` — the one-command demo**

```python
"""90-second demo: run the live Skill path on a token and print the layered verdict.
Run: CMC_PRO_API_KEY=... python scripts/demo.py BTC
Falls back to the cached HistoricalAdapter window if no live key is set."""
import sys
from datetime import date
from divergence.adapters.cmc_client import CMCClient
from divergence.adapters.historical import HistoricalAdapter
from divergence.skill.runtime import run_skill


def main():
    token = sys.argv[1] if len(sys.argv) > 1 else "BTC"
    # Demo uses the cached historical window as the provider (offline-safe);
    # the live Skill swaps in LiveAdapter with the same interface.
    provider = HistoricalAdapter(CMCClient())
    # theta_abs comes from the committed E2 calibration; hardcode the value the report recorded:
    theta_abs = float(__import__("os").environ.get("DIVERGENCE_THETA", "1.5"))
    out = run_skill(token, provider, theta_abs=theta_abs)
    print(f"\n  VERDICT: {out['verdict']}\n")
    d = out["detail"]
    print(f"  direction={d['direction']}  |D|={abs(d['divergence']):.2f}  "
          f"confidence={d['confidence']:.2f}  degraded={d['degraded']}")
    print("  drivers:")
    for dr in d["drivers"]:
        print(f"    {dr['signal']:18} z={dr['z']:+.2f} ({dr['side']}, {dr['label']})")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Verify the demo runs end-to-end**

Run: `python scripts/demo.py BTC` (with a cached `BTC_frame` from Task 12)
Expected: prints a verdict line, direction/|D|/confidence, and ranked drivers — no traceback.

- [ ] **Step 3: Write the Skill manifest**

Use the descriptor format confirmed in the Task 12 E1 note. Minimal shape (adjust keys to the Agent-Hub spec):

```json
{
  "name": "smart-money-divergence",
  "description": "Flags divergence between crowd sentiment and real whale-vs-retail capital flow for a token; returns a long/short/flat bias with a plain-language rationale.",
  "entrypoint": "divergence.skill.runtime:run_skill",
  "inputs": {"token": "string (symbol, e.g. BTC)"},
  "outputs": {"verdict": "string", "detail": "object (direction, divergence, confidence, drivers, degraded)"},
  "version": "0.1.0"
}
```

- [ ] **Step 4: Write `README.md`**

Must contain, in this order (judge reads top-down):
1. **One-line hook** — "Trade with the smart money, against the crowd."
2. **The thesis** (2-3 sentences): short-term price = crowd; medium-term = capital positioning; trade the divergence `D = capital − crowd`.
3. **What's the edge & how it's validated** — link `reports/backtest_report.md`; state the OOS result honestly (including limitations per C1).
4. **Architecture diagram** (reuse the spec §4 ASCII): one signal core, two adapters, backtest == live.
5. **Quickstart**: `pip install -e ".[dev]" && pytest -q` then `python scripts/demo.py BTC`.
6. **Anti-overfit note**: ~3 knobs, one global θ, in-sample-only calibration, sensitivity grid + leave-one-out (link the report section).
7. **Scope/honesty**: no live trading, no wallets, no funds (Track 2 by design); signal-only.
8. **Track 2 + special-prize framing**: CMC Strategy Skill, Agent-Hub manifest, links.

- [ ] **Step 5: Write the submission checklist note**

`docs/superpowers/notes/2026-06-12-submission-checklist.md`: DoraHacks fields, demo video link (if required), repo URL, special-prize boxes (Best Use of Agent Hub), the **2026-06-21 deadline**, and a final "all tests green / report committed / demo runs clean" gate.

- [ ] **Step 6: Final full-suite run + commit + tag**

```bash
pytest -q
git add README.md skill/manifest.json scripts/demo.py docs/superpowers/notes/2026-06-12-submission-checklist.md
git commit -m "docs: README, Skill manifest, demo script, submission checklist"
git tag v0.1.0-submission
```

- [ ] **Step 7: Publish + submit**

Push to a public repo and submit the repo + report + demo on DoraHacks before **2026-06-21**. (Publishing/pushing is a shared-state action — confirm with the user before the push.)

---

## Appendix — Spec → Plan traceability

| Spec correction | Where it lives in this plan |
|---|---|
| **C1** value = honest framework, not magic PnL | Task 16 gate criteria (Conditional GO), Task 20 "Honest limitations" report section, README §3/§7 |
| **C2** whale-vs-retail = hero, F&G = background | Task 5 `capital_score = whale_z` (hero only); F&G folded into crowd composite |
| **C3** Day-1 data spike + fallback ladder | Task 12 E1 spike + tier decision; degradation already in Task 5 |
| **C4** cut scope (daily, ~20-30 tokens, one split) | Task 3 `n=25`; Task 15 single `split`; daily snapshots throughout |
| **C5** downgrade BNB SDK special | Phase 7 only, optional; not on the critical path |
| **C6** layered output | Task 18 `run_skill` verdict + detail; Task 8 `explain` Layer-1 |
| **C7** single strategy default, generator stretch | Default = one strategy; Task 16 NO-GO branch (b) escalates to generator |
| **E1** data availability | Task 12 |
| **E2** edge backtest GO/NO-GO | Task 16 (the gate) |
| **E3** differentiation scan | Task 12 Step 4 |
| **E4** demo case mining | Task 20 Step 5 |
