from __future__ import annotations
import json
import os
import tempfile
from datetime import datetime, timezone
from typing import Any


def _load(path: str) -> list[dict]:
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _save(path: str, records: list[dict]) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    abs_path = os.path.abspath(path)
    target_dir = os.path.dirname(abs_path)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=target_dir, delete=False, suffix=".tmp"
    ) as f:
        json.dump(records, f, indent=2, ensure_ascii=False)
        tmp = f.name
    os.replace(tmp, abs_path)


def already_applied(path: str, job_url: str) -> bool:
    records = _load(path)
    return any(r.get("url") == job_url for r in records)


def record_application(
    path: str,
    job_url: str,
    job_title: str,
    company: str,
    method: str,
    status: str = "applied",
    notes: str = "",
) -> None:
    records = _load(path)
    records.append({
        "url": job_url,
        "title": job_title,
        "company": company,
        "method": method,
        "status": status,
        "notes": notes,
        "applied_at": datetime.now(timezone.utc).isoformat(),
    })
    _save(path, records)


def list_applications(path: str) -> list[dict[str, Any]]:
    return _load(path)


def print_summary(path: str) -> None:
    records = _load(path)
    if not records:
        print("No applications tracked yet.")
        return
    print(f"\n{'─'*70}")
    print(f"{'#':<4} {'Title':<35} {'Company':<20} {'Status':<12} {'Date'}")
    print(f"{'─'*70}")
    for i, r in enumerate(records, 1):
        date = r.get("applied_at", "")[:10]
        print(f"{i:<4} {r.get('title','')[:34]:<35} {r.get('company','')[:19]:<20} {r.get('status',''):<12} {date}")
    print(f"{'─'*70}")
    print(f"Total: {len(records)} applications\n")
