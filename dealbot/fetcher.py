from __future__ import annotations
import calendar
import hashlib
import html
import re
from urllib.parse import urlparse
import feedparser
import requests
from .config import USER_AGENT
from .models import Deal

TAG_RE = re.compile(r"<[^>]+>")


def clean_html(value: str | None) -> str:
    if not value:
        return ""
    value = TAG_RE.sub(" ", value)
    value = html.unescape(value)
    return re.sub(r"\s+", " ", value).strip()


def source_name(feed_url: str) -> str:
    host = urlparse(feed_url).netloc.replace("www.", "")
    return host or feed_url


def deal_id(title: str, link: str) -> str:
    raw = f"{title}|{link}".encode("utf-8", errors="ignore")
    return hashlib.sha256(raw).hexdigest()[:24]


def fetch_feed(feed_url: str) -> list[Deal]:
    headers = {"User-Agent": USER_AGENT}
    resp = requests.get(feed_url, headers=headers, timeout=25)
    resp.raise_for_status()
    parsed = feedparser.parse(resp.content)
    deals: list[Deal] = []
    src = source_name(feed_url)

    for entry in parsed.entries[:30]:
        title = clean_html(getattr(entry, "title", ""))
        link = getattr(entry, "link", "") or ""
        summary = clean_html(getattr(entry, "summary", ""))
        published = getattr(entry, "published", "") or getattr(entry, "updated", "") or ""
        # feedparser populates *_parsed as UTC time.struct_time; convert to Unix timestamp
        parsed_struct = getattr(entry, "published_parsed", None) or getattr(entry, "updated_parsed", None)
        published_ts = float(calendar.timegm(parsed_struct)) if parsed_struct else 0.0
        if not title or not link:
            continue
        deals.append(Deal(
            id=deal_id(title, link),
            title=title,
            link=link,
            source=src,
            summary=summary,
            published=published,
            published_ts=published_ts,
        ))
    return deals


def fetch_all(feeds: list[str]) -> list[Deal]:
    all_deals: list[Deal] = []
    for feed in feeds:
        try:
            all_deals.extend(fetch_feed(feed))
        except Exception as exc:
            print(f"WARN: failed to fetch {feed}: {exc}")
    return all_deals
