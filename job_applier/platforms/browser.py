from __future__ import annotations
import webbrowser
from .base import ApplyOutcome, ApplyResult


def open_in_browser(url: str) -> ApplyOutcome:
    """Open the job application URL in the system default browser."""
    try:
        webbrowser.open(url)
        return ApplyOutcome(
            ApplyResult.BROWSER_OPENED,
            f"Opened in browser: {url}",
            "browser",
        )
    except Exception as exc:
        return ApplyOutcome(ApplyResult.FAILED, str(exc), "browser")
