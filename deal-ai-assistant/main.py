import hashlib
import os
import re
import sqlite3
from datetime import datetime, timezone
from typing import Dict, List

import feedparser
import requests

DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK", "").strip()
DB_PATH = os.getenv("DB_PATH", "data/deals.db")
MAX_PRICE = float(os.getenv("MAX_PRICE", "5"))

FEEDS = [
    "https://slickdeals.net/newsearch.php?mode=frontpage&searcharea=deals&searchin=first&rss=1",
    "https://www.reddit.com/r/deals/.rss",
    "https://www.reddit.com/r/buildapcsales/.rss",
    "https://www.reddit.com/r/GameDeals/.rss",
]

GOOD_WORDS = [
    "amazon", "free", "nearly free", "coupon", "promo", "code", "price error",
    "glitch", "ymmv", "clearance", "after coupon", "after promo", "$0", "$1", "$2", "$3", "$4", "$5"
]
BAD_WORDS = ["expired", "dead deal", "in store only", "local only"]


def init_db() -> None:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS seen (id TEXT PRIMARY KEY, title TEXT, link TEXT, created_at TEXT)"
        )


def deal_id(title: str, link: str) -> str:
    return hashlib.sha256(f"{title}|{link}".encode("utf-8")).hexdigest()


def already_seen(item_id: str) -> bool:
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute("SELECT 1 FROM seen WHERE id=?", (item_id,)).fetchone()
        return row is not None


def mark_seen(item_id: str, title: str, link: str) -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT OR IGNORE INTO seen VALUES (?, ?, ?, ?)",
            (item_id, title, link, datetime.now(timezone.utc).isoformat()),
        )


def extract_prices(text: str) -> List[float]:
    prices = []
    for match in re.findall(r"\$\s*(\d+(?:\.\d{1,2})?)", text):
        try:
            prices.append(float(match))
        except ValueError:
            pass
    return prices


def looks_good(title: str, summary: str) -> bool:
    text = f"{title} {summary}".lower()
    if any(w in text for w in BAD_WORDS):
        return False

    prices = extract_prices(text)
    has_low_price = any(p <= MAX_PRICE for p in prices)
    has_good_word = any(w in text for w in GOOD_WORDS)
    is_amazon = "amazon" in text or "amzn" in text or "amazon.com" in text

    return is_amazon and (has_low_price or has_good_word)


def fetch_deals() -> List[Dict[str, str]]:
    results = []
    headers = {"User-Agent": "deal-ai-assistant/1.0"}

    for feed_url in FEEDS:
        parsed = feedparser.parse(requests.get(feed_url, headers=headers, timeout=20).text)
        for entry in parsed.entries[:30]:
            title = getattr(entry, "title", "").strip()
            link = getattr(entry, "link", "").strip()
            summary = getattr(entry, "summary", "").strip()
            if not title or not link:
                continue
            if looks_good(title, summary):
                results.append({"title": title, "link": link, "summary": summary, "source": feed_url})
    return results


def send_discord(title: str, link: str, summary: str) -> None:
    if not DISCORD_WEBHOOK:
        print(f"DISCORD_WEBHOOK missing. Deal: {title} {link}")
        return

    content = f"🔥 **Amazon Deal Alert**\n{title}\n{link}"
    if len(content) > 1900:
        content = content[:1900]

    resp = requests.post(DISCORD_WEBHOOK, json={"content": content}, timeout=20)
    resp.raise_for_status()


def main() -> None:
    init_db()
    deals = fetch_deals()
    sent = 0

    for deal in deals:
        item_id = deal_id(deal["title"], deal["link"])
        if already_seen(item_id):
            continue
        send_discord(deal["title"], deal["link"], deal.get("summary", ""))
        mark_seen(item_id, deal["title"], deal["link"])
        sent += 1

    print(f"Found {len(deals)} matching deals, sent {sent} new alerts.")


if __name__ == "__main__":
    main()
