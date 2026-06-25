from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class Job:
    id: str
    title: str
    company: str
    link: str
    source: str
    location: str = ""
    description: str = ""
    published: str = ""
    published_ts: float = 0.0
    score: int = 0
    reason: str = ""
    salary: str = ""
    # True when the source is a remote-specific job board (all listings are remote)
    is_remote_board: bool = False
    # Minimum years of experience required (0 = unknown / not specified)
    min_years_exp: int = 0
    # Employment type string e.g. "Full-time", "Contract", "Part-time"
    employment_type: str = ""
