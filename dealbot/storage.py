from __future__ import annotations
import json
import os
from typing import Set


def load_seen(path: str) -> Set[str]:
    if not os.path.exists(path):
        return set()
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return set(str(x) for x in data)
        return set()
    except Exception:
        return set()


def save_seen(path: str, seen: Set[str], keep_last: int = 5000) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    items = list(seen)[-keep_last:]
    with open(path, "w", encoding="utf-8") as f:
        json.dump(items, f, indent=2, ensure_ascii=False)
