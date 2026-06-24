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
    # Slickdeals frontpage / hot deals
    "https://slickdeals.net/newsearch.php?mode=frontpage&searcharea=deals&searchin=first&rss=1",
    "https://slickdeals.net/newsearch.php?searcharea=deals&searchin=first&q=amazon&rss=1",

    # Reddit RSS feeds
    "https://www.reddit.com/r/deals/.rss",
    "https://www.reddit.com/r/frugalmalefashion/.rss",
    "https://www.reddit.com/r/buildapcsales/.rss",
    "https://www.reddit.com/r/GameDeals/.rss",
    "https://www.reddit.com/r/FreeGameFindings/.rss",
]

MAX_PRICE_DOLLARS = _env_float("MAX_PRICE_DOLLARS", 5.00, aliases=("MAX_PRICE",))
MIN_SCORE_TO_NOTIFY = _env_int("MIN_SCORE_TO_NOTIFY", 5)
MAX_ALERTS_PER_RUN = _env_int("MAX_ALERTS_PER_RUN", 10)
SEEN_FILE = _env_str("SEEN_FILE", "data/seen_deals.json")
KEYWORDS_FILE = _env_str("KEYWORDS_FILE", "keywords.txt")

USER_AGENT = _env_str("USER_AGENT", "amazon-deal-ai-bot/1.0 (+https://github.com/)")
