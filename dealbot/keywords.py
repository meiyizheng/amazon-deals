from __future__ import annotations
from pathlib import Path


def load_keywords(path: str) -> list[str]:
    p = Path(path)
    if not p.exists():
        return []
    return [line.strip().lower() for line in p.read_text(encoding="utf-8").splitlines() if line.strip() and not line.strip().startswith("#")]
