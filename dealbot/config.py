from __future__ import annotations
import os


def _env_value(name: str, aliases: tuple[str, ...] = ()) -> str | None:
    for env_name in (name, *aliases):
        value = os.getenv(env_name)
        if value:
            return value
    return None


def _env_float(name: str, default: float, aliases: tuple[str, ...] = ()) -> float:
    value = _env_value(name, aliases)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError as exc:
        raise ValueError(f"{name} must be a number, got {value!r}") from exc


def _env_int(name: str, default: int, aliases: tuple[str, ...] = ()) -> int:
    value = _env_value(name, aliases)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer, got {value!r}") from exc


def _env_str(name: str, default: str, aliases: tuple[str, ...] = ()) -> str:
    value = _env_value(name, aliases)
    return default if value is None else value

FEEDS = [
    # ── Slickdeals ────────────────────────────────────────────────────────────
    # Frontpage hot deals
    "https://slickdeals.net/newsearch.php?mode=frontpage&searcharea=deals&searchin=first&rss=1",
    # Amazon-tagged deals
    "https://slickdeals.net/newsearch.php?searcharea=deals&searchin=first&q=amazon&rss=1",
    # Amazon Lightning / Deal-of-the-Day
    "https://slickdeals.net/newsearch.php?searcharea=deals&searchin=first&q=amazon+lightning+deal&rss=1",
    # Amazon price errors and coupons
    "https://slickdeals.net/newsearch.php?searcharea=deals&searchin=first&q=amazon+price+error&rss=1",
    "https://slickdeals.net/newsearch.php?searcharea=deals&searchin=first&q=amazon+coupon&rss=1",

    # ── Reddit – Amazon-specific ──────────────────────────────────────────────
    # Dedicated Amazon deal community
    "https://www.reddit.com/r/amazondeals/.rss",
    # Extreme / price-error deals
    "https://www.reddit.com/r/extremedeals/.rss",
    # Frugal community – highly curated, low noise
    "https://www.reddit.com/r/Frugal/.rss",

    # ── Reddit – general deal communities ────────────────────────────────────
    "https://www.reddit.com/r/deals/.rss",
    "https://www.reddit.com/r/HotDeals/.rss",
    "https://www.reddit.com/r/buildapcsales/.rss",
    "https://www.reddit.com/r/GameDeals/.rss",
    "https://www.reddit.com/r/FreeGameFindings/.rss",
    "https://www.reddit.com/r/frugalmalefashion/.rss",
]

MAX_PRICE_DOLLARS = _env_float("MAX_PRICE_DOLLARS", 5.00, aliases=("MAX_PRICE",))
MIN_SCORE_TO_NOTIFY = _env_int("MIN_SCORE_TO_NOTIFY", 5)
MAX_ALERTS_PER_RUN = _env_int("MAX_ALERTS_PER_RUN", 10)
# Deals older than this many hours are skipped (0 = no age filter)
MAX_DEAL_AGE_HOURS = _env_int("MAX_DEAL_AGE_HOURS", 6)
# Seconds to sleep between consecutive feed fetches; prevents Reddit/Slickdeals 429s
FEED_FETCH_DELAY = _env_float("FEED_FETCH_DELAY", 1.5)
SEEN_FILE = _env_str("SEEN_FILE", "data/seen_deals.json")
KEYWORDS_FILE = _env_str("KEYWORDS_FILE", "keywords.txt")

# Reddit requires a descriptive User-Agent: "<platform>:<appID>:<version> (by /u/<username>)"
# This format is needed to avoid 429 rate-limit blocks on Reddit RSS feeds.
USER_AGENT = _env_str(
    "USER_AGENT",
    "python:amazon-deal-bot:v2.0 (by /u/amazon-deals-bot; github.com/meiyizheng/amazon-deals)",
)
