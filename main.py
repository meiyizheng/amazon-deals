from __future__ import annotations
from dealbot.config import FEEDS, KEYWORDS_FILE, MAX_ALERTS_PER_RUN, MIN_SCORE_TO_NOTIFY, SEEN_FILE
from dealbot.fetcher import fetch_all
from dealbot.filtering import score_deal
from dealbot.keywords import load_keywords
from dealbot.storage import load_seen, save_seen
from dealbot.discord_notify import send_discord


def main() -> None:
    keywords = load_keywords(KEYWORDS_FILE)
    seen = load_seen(SEEN_FILE)

    raw_deals = fetch_all(FEEDS)
    print(f"Fetched {len(raw_deals)} raw deals")

    scored = []
    for deal in raw_deals:
        if deal.id in seen:
            continue
        result = score_deal(deal, keywords)
        if result and result.score >= MIN_SCORE_TO_NOTIFY:
            scored.append(result)

    scored.sort(key=lambda d: d.score, reverse=True)
    alerts = scored[:MAX_ALERTS_PER_RUN]

    if alerts:
        print(f"Sending {len(alerts)} alerts")
        send_discord(alerts)
        for deal in alerts:
            seen.add(deal.id)
        save_seen(SEEN_FILE, seen)
    else:
        print("No new matching deals")
        # Still mark high-noise irrelevant fetched items? No. Only mark notified deals so improved filters can catch later.


if __name__ == "__main__":
    main()
