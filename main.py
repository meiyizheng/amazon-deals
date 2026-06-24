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

    # evaluated: all deals that passed scoring filters (any score ≥ 0)
    # alerts:    subset of evaluated that exceed MIN_SCORE_TO_NOTIFY
    evaluated: list = []
    alerts: list = []

    for deal in raw_deals:
        if deal.id in seen:
            continue
        result = score_deal(deal, keywords)
        if result is None:
            continue
        evaluated.append(result)
        if result.score >= MIN_SCORE_TO_NOTIFY:
            alerts.append(result)

    alerts.sort(key=lambda d: d.score, reverse=True)
    alerts = alerts[:MAX_ALERTS_PER_RUN]

    if alerts:
        print(f"Sending {len(alerts)} alerts")
        send_discord(alerts)
    else:
        print("No new matching deals")

    # Mark every evaluated deal (not just notified ones) as seen.
    # This prevents a cache-eviction event on GitHub Actions from re-sending
    # hundreds of old deals that scored below the notification threshold.
    if evaluated:
        for deal in evaluated:
            seen.add(deal.id)
        save_seen(SEEN_FILE, seen)


if __name__ == "__main__":
    main()
