from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class ScrapedAction:
    action_text: str
    material_text: str
    count: float
    amount: float
    weight_grams: float
    raw_text: str
    source: str
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class AggregatedRow:
    action: str
    subdivision: str
    count: float = 0.0
    amount: float = 0.0
    weight_grams: float = 0.0
