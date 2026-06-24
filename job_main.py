from __future__ import annotations
from jobbot.config import (
    FEEDS,
    KEYWORDS_FILE,
    MAX_ALERTS_PER_RUN,
    MIN_SCORE_TO_NOTIFY,
    SEEN_FILE,
)
from jobbot.fetcher import fetch_all
from jobbot.filtering import score_job
from jobbot.discord_notify import send_discord
from dealbot.keywords import load_keywords   # generic keyword loader, safe to reuse
from dealbot.storage import load_seen, save_seen  # generic dedup cache, safe to reuse


def main() -> None:
    keywords = load_keywords(KEYWORDS_FILE)
    seen = load_seen(SEEN_FILE)

    raw_jobs = fetch_all(FEEDS)
    print(f"Fetched {len(raw_jobs)} raw job listings")

    evaluated: list = []
    alerts: list = []

    for job in raw_jobs:
        if job.id in seen:
            continue
        result = score_job(job, keywords)
        if result is None:
            continue
        evaluated.append(result)
        if result.score >= MIN_SCORE_TO_NOTIFY:
            alerts.append(result)

    alerts.sort(key=lambda j: j.score, reverse=True)
    alerts = alerts[:MAX_ALERTS_PER_RUN]

    if alerts:
        print(f"Sending {len(alerts)} job alerts")
        send_discord(alerts)
    else:
        print("No new matching job listings")

    # Mark all evaluated jobs as seen to prevent re-alerting after cache eviction
    if evaluated:
        for job in evaluated:
            seen.add(job.id)
        save_seen(SEEN_FILE, seen)


if __name__ == "__main__":
    main()
