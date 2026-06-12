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
