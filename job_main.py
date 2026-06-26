from __future__ import annotations
import os
import sys
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
from jobbot.linkedin_fetcher import fetch_linkedin_jobs, DEFAULT_QUERIES
from dealbot.keywords import load_keywords   # generic keyword loader, safe to reuse
from dealbot.storage import load_seen, save_seen  # generic dedup cache, safe to reuse


def main() -> None:
    if not os.getenv("JOB_DISCORD_WEBHOOK"):
        print("ERROR: JOB_DISCORD_WEBHOOK secret is not set.")
        print("Go to GitHub → Settings → Secrets and variables → Actions → New repository secret")
        print("  Name:  JOB_DISCORD_WEBHOOK")
        print("  Value: your Discord webhook URL (https://discord.com/api/webhooks/...)")
        sys.exit(1)

    keywords = load_keywords(KEYWORDS_FILE)
    seen = load_seen(SEEN_FILE)

    # Fetch from RSS feeds
    rss_jobs = fetch_all(FEEDS)
    print(f"Fetched {len(rss_jobs)} listings from RSS feeds")

    # Fetch from LinkedIn public guest API (no login required)
    print("Fetching LinkedIn jobs...")
    linkedin_jobs = fetch_linkedin_jobs(queries=DEFAULT_QUERIES)
    print(f"Fetched {len(linkedin_jobs)} listings from LinkedIn")

    raw_jobs = rss_jobs + linkedin_jobs
    print(f"Total: {len(raw_jobs)} raw listings")

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
