from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class Deal:
    id: str
    title: str
    link: str
    source: str
    summary: str = ""
    published: str = ""
    # UTC Unix timestamp parsed from the feed entry; 0 means unknown
    published_ts: float = 0.0
    score: int = 0
    reason: str = ""
    # Populated when a was/now price-drop pattern is detected
    original_price: float = 0.0
    discount_pct: float = 0.0
