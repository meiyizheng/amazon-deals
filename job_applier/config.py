from __future__ import annotations
import os
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore[assignment]

_PROFILE_PATH = Path(os.getenv("APPLY_PROFILE", "profile.yml"))
_DEFAULT_TRACKER = "data/applications.json"


def load_profile() -> dict:
    """Load profile.yml. Exits with instructions if file is missing."""
    if yaml is None:
        print("ERROR: PyYAML is required. Run:  pip install pyyaml")
        sys.exit(1)

    if not _PROFILE_PATH.exists():
        print(f"ERROR: Profile file not found: {_PROFILE_PATH}")
        print("Copy profile.yml.example to profile.yml and fill in your details.")
        sys.exit(1)

    with open(_PROFILE_PATH, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    required = ["personal", "resume"]
    for key in required:
        if key not in data:
            print(f"ERROR: profile.yml is missing required section: '{key}'")
            sys.exit(1)

    return data


def tracker_path() -> str:
    return os.getenv("APPLY_TRACKER", _DEFAULT_TRACKER)
