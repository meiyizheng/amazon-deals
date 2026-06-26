from __future__ import annotations
"""
LinkedIn job fetcher using the public guest search API.

LinkedIn does not provide RSS feeds or a public API, but its job search
pages load listings via a guest endpoint that requires no authentication.
This module uses that same endpoint to fetch job listings.

Note: Only publicly visible data (title, company, location, apply link)
is accessible without login. Full job descriptions require an extra
request per listing and are fetched on demand with a polite delay.
"""
import hashlib
import re
import time
from urllib.parse import urlencode

import requests

try:
    from bs4 import BeautifulSoup
    _BS4_AVAILABLE = True
except ImportError:
    _BS4_AVAILABLE = False

from .models import Job

# LinkedIn guest jobs API — returns HTML fragments (list items), no auth needed
_GUEST_API = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"

# LinkedIn job detail page — used to fetch description
_DETAIL_API = "https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{job_id}"

# Remote filter value for LinkedIn's f_WT parameter
_REMOTE_FILTER = "2"

# Worldwide geo ID
_GEO_WORLDWIDE = "92000000"

# How many listings to fetch per search query
_PAGE_SIZE = 25

# Delay between description fetches (seconds) — be polite to LinkedIn
_DESC_FETCH_DELAY = 1.0

# Browser-like User-Agent — generic UA gets blocked
_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/125.0.0.0 Safari/537.36"
)

# Default search queries targeting SDE / SDET / Java / backend roles
DEFAULT_QUERIES = [
    "java developer",
    "backend engineer",
    "software developer",
    "sdet",
    "test automation engineer",
    "software engineer in test",
    "integration engineer",
    "api developer",
]


def _job_id_from_url(url: str) -> str:
    """Extract numeric LinkedIn job ID from a job URL."""
    m = re.search(r"/view/[^/]+-(\d+)", url)
    if m:
        return m.group(1)
    m = re.search(r"currentJobId=(\d+)", url)
    if m:
        return m.group(1)
    return ""


def _canonical_url(raw_url: str, job_id: str) -> str:
    """Return a clean linkedin.com/jobs/view/{id} URL."""
    if job_id:
        return f"https://www.linkedin.com/jobs/view/{job_id}/"
    return raw_url


def _make_id(title: str, company: str, job_id: str) -> str:
    raw = f"linkedin|{job_id or title}|{company}".encode("utf-8", errors="ignore")
    return hashlib.sha256(raw).hexdigest()[:24]


def _fetch_description(job_id: str, session: requests.Session) -> str:
    """Fetch the full job description for a single listing."""
    if not job_id:
        return ""
    try:
        url = _DETAIL_API.format(job_id=job_id)
        resp = session.get(url, timeout=15)
        if resp.status_code != 200:
            return ""
        soup = BeautifulSoup(resp.text, "html.parser")
        desc_tag = soup.find("div", class_=re.compile("description|details", re.I))
        if desc_tag:
            return re.sub(r"\s+", " ", desc_tag.get_text(separator=" ")).strip()[:2000]
    except Exception:
        pass
    return ""


def _parse_cards(html: str, fetch_descriptions: bool, session: requests.Session) -> list[Job]:
    """Parse LinkedIn job card HTML fragments into Job objects."""
    soup = BeautifulSoup(html, "html.parser")
    jobs: list[Job] = []

    for card in soup.find_all("li"):
        title_tag   = card.find("h3")
        company_tag = card.find("h4")
        link_tag    = card.find("a", href=True)

        if not title_tag or not link_tag:
            continue

        title   = title_tag.get_text(strip=True)
        company = company_tag.get_text(strip=True) if company_tag else "Unknown"
        raw_url = link_tag["href"].split("?")[0]
        job_id  = _job_id_from_url(raw_url)
        link    = _canonical_url(raw_url, job_id)

        # Location — look for the metadata list item
        location = ""
        for span in card.find_all("span"):
            text = span.get_text(strip=True)
            if text and len(text) < 80 and any(kw in text.lower() for kw in ("remote", "anywhere", "worldwide")):
                location = text
                break

        description = ""
        if fetch_descriptions and job_id:
            description = _fetch_description(job_id, session)
            time.sleep(_DESC_FETCH_DELAY)

        jobs.append(Job(
            id=_make_id(title, company, job_id),
            title=title,
            company=company,
            link=link,
            source="linkedin.com",
            location=location or "Remote",
            description=description,
            is_remote_board=False,   # LinkedIn mixes remote and on-site
        ))

    return jobs


def fetch_linkedin_jobs(
    queries: list[str] | None = None,
    fetch_descriptions: bool = True,
    max_retries: int = 3,
) -> list[Job]:
    """
    Fetch remote job listings from LinkedIn for each query in `queries`.

    Args:
        queries: Search terms. Defaults to DEFAULT_QUERIES.
        fetch_descriptions: Whether to fetch full descriptions (slower but
            enables experience/type extraction and better scoring). Default True.
        max_retries: Number of retries on 429 / transient errors.

    Returns:
        Deduplicated list of Job objects.
    """
    if not _BS4_AVAILABLE:
        print("WARN: beautifulsoup4 is not installed — LinkedIn fetcher skipped. "
              "Run: pip install beautifulsoup4")
        return []

    if queries is None:
        queries = DEFAULT_QUERIES

    session = requests.Session()
    session.headers.update({"User-Agent": _USER_AGENT})

    all_jobs: list[Job] = []
    seen_ids: set[str] = set()

    for query in queries:
        params = {
            "keywords": query,
            "location": "Remote",
            "f_WT": _REMOTE_FILTER,
            "geoId": _GEO_WORLDWIDE,
            "start": "0",
            "count": str(_PAGE_SIZE),
        }
        url = f"{_GUEST_API}?{urlencode(params)}"

        for attempt in range(max_retries):
            try:
                resp = session.get(url, timeout=20)
            except requests.RequestException as exc:
                print(f"WARN: LinkedIn request failed ({query}): {exc}")
                break

            if resp.status_code == 429:
                wait = float(resp.headers.get("Retry-After", 5 * (attempt + 1)))
                print(f"WARN: LinkedIn rate-limited, waiting {wait:.0f}s")
                time.sleep(wait)
                continue

            if resp.status_code != 200:
                print(f"WARN: LinkedIn returned {resp.status_code} for query '{query}'")
                break

            jobs = _parse_cards(resp.text, fetch_descriptions, session)
            new_jobs = [j for j in jobs if j.id not in seen_ids]
            seen_ids.update(j.id for j in new_jobs)
            all_jobs.extend(new_jobs)
            print(f"  LinkedIn '{query}': {len(new_jobs)} new listings")
            break

        # Polite delay between queries
        time.sleep(2.0)

    return all_jobs
