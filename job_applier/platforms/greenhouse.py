from __future__ import annotations
import base64
import json
import re
from pathlib import Path

import requests

from .base import ApplyOutcome, ApplyResult

# Greenhouse job URLs look like:
#   https://boards.greenhouse.io/{company}/jobs/{job_id}
#   https://job-boards.greenhouse.io/{company}/jobs/{job_id}
_GH_RE = re.compile(
    r"(?:boards|job-boards)\.greenhouse\.io/(?P<company>[^/]+)/jobs/(?P<job_id>\d+)",
    re.I,
)

APPLY_ENDPOINT = "https://boards-api.greenhouse.io/v1/boards/{company}/jobs/{job_id}"


def is_greenhouse_url(url: str) -> bool:
    return bool(_GH_RE.search(url))


def apply(url: str, profile: dict, cover_letter_text: str) -> ApplyOutcome:
    m = _GH_RE.search(url)
    if not m:
        return ApplyOutcome(ApplyResult.FAILED, "Not a valid Greenhouse URL", "greenhouse_api")

    company = m.group("company")
    job_id = m.group("job_id")
    endpoint = APPLY_ENDPOINT.format(company=company, job_id=job_id)

    personal = profile.get("personal", {})
    resume_path = Path(profile.get("resume", {}).get("path", "resume.pdf"))

    if not resume_path.exists():
        return ApplyOutcome(
            ApplyResult.FAILED,
            f"Resume file not found: {resume_path}. Update profile.yml → resume.path",
            "greenhouse_api",
        )

    resume_b64 = base64.b64encode(resume_path.read_bytes()).decode()
    cl_b64 = base64.b64encode(cover_letter_text.encode()).decode()

    payload = {
        "first_name": personal.get("first_name", ""),
        "last_name": personal.get("last_name", ""),
        "email": personal.get("email", ""),
        "phone": personal.get("phone", ""),
        "resume_content": resume_b64,
        "resume_content_filename": resume_path.name,
        "cover_letter_content": cl_b64,
        "cover_letter_content_filename": "cover_letter.txt",
        "linkedin_profile_url": personal.get("linkedin_url", ""),
        "website": personal.get("portfolio_url", "") or personal.get("github_url", ""),
    }

    try:
        resp = requests.post(
            endpoint,
            data=json.dumps(payload),
            headers={"Content-Type": "application/json"},
            timeout=30,
        )
        if resp.status_code in (200, 201):
            return ApplyOutcome(ApplyResult.SUCCESS, f"Applied via Greenhouse API ({company})", "greenhouse_api")

        return ApplyOutcome(
            ApplyResult.FAILED,
            f"Greenhouse API returned {resp.status_code}: {resp.text[:200]}",
            "greenhouse_api",
        )
    except Exception as exc:
        return ApplyOutcome(ApplyResult.FAILED, str(exc), "greenhouse_api")
