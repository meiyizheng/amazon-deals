from __future__ import annotations
import calendar
import hashlib
import html
import re
import time
from urllib.parse import urlparse

import feedparser
import requests

from .config import FEED_FETCH_DELAY, USER_AGENT
from .models import Job

TAG_RE = re.compile(r"<[^>]+>")

# "Title at Company" — e.g. "Senior SDET at Acme Corp"
AT_COMPANY_RE = re.compile(r"\bat\s+([A-Z][^,\n\|–\-]{2,60}?)(?:\s*[-,\|]|\s*$)")
# "Company: Title" — WeWorkRemotely format
COMPANY_PREFIX_RE = re.compile(r"^([^:]{2,60}):\s+")

# Detect salary ranges inside description text
SALARY_RE = re.compile(
    r"\$\s*(\d{2,3})[kK](?:\s*[-–]\s*\$?\s*(\d{2,3})[kK])?"   # $120k–$150k
    r"|\$\s*([\d,]{3,})(?:\s*[-–]\s*\$?\s*([\d,]{3,}))?(?:\s*(?:USD|per\s+year|\/yr|annually))?",
    re.I,
)


def _clean(value: str | None) -> str:
    if not value:
        return ""
    value = TAG_RE.sub(" ", value)
    value = html.unescape(value)
    return re.sub(r"\s+", " ", value).strip()


def _source_name(feed_url: str) -> str:
    host = urlparse(feed_url).netloc.replace("www.", "")
    return host or feed_url


def _extract_company(entry, title: str) -> str:
    """Best-effort company name extraction from feed entry and title."""
    # 1. Explicit author field (RemoteOK, Himalayas)
    author = getattr(entry, "author", "") or ""
    if author and "@" not in author and len(author) < 80:
        return author.strip()

    # 2. "Title at Company Name" (RemoteOK title format)
    m = AT_COMPANY_RE.search(title)
    if m:
        return m.group(1).strip()

    # 3. "Company: Title" (WeWorkRemotely title format)
    m = COMPANY_PREFIX_RE.match(title)
    if m:
        candidate = m.group(1).strip()
        # Skip if candidate looks like a seniority level, not a company
        if not re.match(r"(?:senior|junior|lead|staff|principal|mid)\b", candidate, re.I):
            return candidate

    return "Unknown Company"


def _extract_salary(text: str) -> str:
    m = SALARY_RE.search(text)
    return m.group(0).strip() if m else ""


def _job_id(title: str, company: str, link: str) -> str:
    raw = f"{title}|{company}|{link}".encode("utf-8", errors="ignore")
    return hashlib.sha256(raw).hexdigest()[:24]


def _clean_title(title: str) -> str:
    """Strip 'Company: ' prefix from WeWorkRemotely-style titles."""
    m = COMPANY_PREFIX_RE.match(title)
    if m:
        rest = title[m.end():]
        # Only strip prefix if the rest looks like an actual job title
        if re.search(r"\bengine|develop|quality|test|automation|sdet|sde\b", rest, re.I):
            return rest.strip()
    return title


def fetch_feed(feed_url: str, is_remote_board: bool = True, max_retries: int = 3) -> list[Job]:
    headers = {"User-Agent": USER_AGENT}
    for attempt in range(max_retries):
        resp = requests.get(feed_url, headers=headers, timeout=25)
        if resp.status_code == 429:
            retry_after = float(resp.headers.get("Retry-After", 2 ** (attempt + 1)))
            print(f"WARN: {feed_url} rate-limited (429), retrying after {retry_after:.0f}s")
            time.sleep(retry_after)
            continue
        resp.raise_for_status()
        break
    else:
        raise requests.HTTPError(f"Failed after {max_retries} retries: {feed_url}")
    parsed = feedparser.parse(resp.content)
    jobs: list[Job] = []
    src = _source_name(feed_url)

    for entry in parsed.entries[:50]:
        raw_title = _clean(getattr(entry, "title", ""))
        link = getattr(entry, "link", "") or ""
        description = _clean(getattr(entry, "summary", ""))
        published = getattr(entry, "published", "") or getattr(entry, "updated", "") or ""
        parsed_struct = (
            getattr(entry, "published_parsed", None)
            or getattr(entry, "updated_parsed", None)
        )
        published_ts = float(calendar.timegm(parsed_struct)) if parsed_struct else 0.0

        if not raw_title or not link:
            continue

        company = _extract_company(entry, raw_title)
        title = _clean_title(raw_title)
        salary = _extract_salary(f"{title} {description}")

        # Some feeds embed location in a tags/categories field
        location_parts: list[str] = []
        for tag in getattr(entry, "tags", []):
            term = (tag.get("term") or "").strip()
            if re.search(r"remote|anywhere|worldwide|global", term, re.I):
                location_parts.append(term)
        location = ", ".join(location_parts) if location_parts else ("Remote" if is_remote_board else "")

        jobs.append(Job(
            id=_job_id(title, company, link),
            title=title,
            company=company,
            link=link,
            source=src,
            location=location,
            description=description,
            published=published,
            published_ts=published_ts,
            salary=salary,
            is_remote_board=is_remote_board,
        ))

    return jobs


def fetch_all(feeds: list[dict]) -> list[Job]:
    all_jobs: list[Job] = []
    for i, feed in enumerate(feeds):
        if i > 0 and FEED_FETCH_DELAY > 0:
            time.sleep(FEED_FETCH_DELAY)
        url = feed["url"]
        is_remote = feed.get("remote_board", False)
        try:
            all_jobs.extend(fetch_feed(url, is_remote_board=is_remote))
        except Exception as exc:
            print(f"WARN: failed to fetch {url}: {exc}")
    return all_jobs
