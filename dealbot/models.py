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
    score: int = 0
    reason: str = ""
