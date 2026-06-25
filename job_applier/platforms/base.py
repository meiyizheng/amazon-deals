from __future__ import annotations
from dataclasses import dataclass
from enum import Enum


class ApplyResult(Enum):
    SUCCESS = "success"
    BROWSER_OPENED = "browser_opened"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class ApplyOutcome:
    result: ApplyResult
    message: str
    method: str  # e.g. "lever_api", "greenhouse_api", "browser"
