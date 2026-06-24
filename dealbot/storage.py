from __future__ import annotations
import json
import os
import tempfile
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
    abs_path = os.path.abspath(path)
    target_dir = os.path.dirname(abs_path)
    os.makedirs(target_dir, exist_ok=True)
    items = list(seen)[-keep_last:]
    # Write to a temp file in the same directory, then atomically rename.
    # Ensures the cache is never left in a partial state if the process is
    # interrupted mid-write (e.g. GitHub Actions job timeout or eviction).
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=target_dir,
        delete=False,
        suffix=".tmp",
    ) as tmp_f:
        json.dump(items, tmp_f, indent=2, ensure_ascii=False)
        tmp_path = tmp_f.name
    os.replace(tmp_path, abs_path)
