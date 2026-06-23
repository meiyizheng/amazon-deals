from __future__ import annotations

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

MAX_PRICE_DOLLARS = 5.00
MIN_SCORE_TO_NOTIFY = 5
MAX_ALERTS_PER_RUN = 10
SEEN_FILE = "data/seen_deals.json"
KEYWORDS_FILE = "keywords.txt"

USER_AGENT = "amazon-deal-ai-bot/1.0 (+https://github.com/)"
