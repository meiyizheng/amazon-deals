from __future__ import annotations
import re
from pathlib import Path

import requests

from .base import ApplyOutcome, ApplyResult

# Lever posting URLs look like:
#   https://jobs.lever.co/{company}/{posting_id}
#   https://jobs.lever.co/{company}/{posting_id}/apply
_LEVER_RE = re.compile(
    r"jobs\.lever\.co/(?P<company>[^/]+)/(?P<posting_id>[0-9a-f-]{36})",
    re.I,
)

APPLY_ENDPOINT = "https://api.lever.co/v0/postings/{company}/{posting_id}/apply"


def is_lever_url(url: str) -> bool:
    return bool(_LEVER_RE.search(url))


def apply(url: str, profile: dict, cover_letter_text: str) -> ApplyOutcome:
    m = _LEVER_RE.search(url)
    if not m:
        return ApplyOutcome(ApplyResult.FAILED, "Not a valid Lever URL", "lever_api")

    company = m.group("company")
    posting_id = m.group("posting_id")
    endpoint = APPLY_ENDPOINT.format(company=company, posting_id=posting_id)

    personal = profile.get("personal", {})
    resume_path = Path(profile.get("resume", {}).get("path", "resume.pdf"))

    if not resume_path.exists():
        return ApplyOutcome(
            ApplyResult.FAILED,
            f"Resume file not found: {resume_path}. Update profile.yml → resume.path",
            "lever_api",
        )

    name = f"{personal.get('first_name', '')} {personal.get('last_name', '')}".strip()
    data = {
        "name": name,
        "email": personal.get("email", ""),
        "phone": personal.get("phone", ""),
        "comments": cover_letter_text,
        "silent": "false",
    }

    # Append LinkedIn / GitHub / portfolio URLs
    for label, key in [("LinkedIn", "linkedin_url"), ("GitHub", "github_url"), ("Portfolio", "portfolio_url")]:
        val = personal.get(key, "")
        if val:
            data[f"urls[{label}]"] = val

    try:
        with open(resume_path, "rb") as resume_file:
            files = {"resume": (resume_path.name, resume_file, "application/pdf")}
            resp = requests.post(endpoint, data=data, files=files, timeout=30)

        if resp.status_code in (200, 201):
            return ApplyOutcome(ApplyResult.SUCCESS, f"Applied via Lever API ({company})", "lever_api")

        return ApplyOutcome(
            ApplyResult.FAILED,
            f"Lever API returned {resp.status_code}: {resp.text[:200]}",
            "lever_api",
        )
    except Exception as exc:
        return ApplyOutcome(ApplyResult.FAILED, str(exc), "lever_api")
