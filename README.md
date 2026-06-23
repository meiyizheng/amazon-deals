# Amazon Deal AI Bot

A lightweight GitHub Actions bot that checks Slickdeals and Reddit RSS feeds, filters for Amazon/free/coupon/near-free deals, deduplicates alerts, and sends Discord notifications.

## What it does

- Runs every 5 minutes on GitHub Actions
- Watches Slickdeals + Reddit deal feeds
- Filters for Amazon, coupon, promo, free, price error, and <$5 deals
- Deduplicates using a local JSON cache committed back to the repo
- Sends alerts to Discord via webhook

## Setup

1. Upload the **contents** of this folder to the root of your GitHub repo. Do not upload the folder itself.
2. In GitHub, go to `Settings` → `Secrets and variables` → `Actions`.
3. Add a repository secret:
   - Name: `DISCORD_WEBHOOK`
   - Value: your Discord webhook URL
4. Go to `Actions` → `Amazon Deal Bot` → `Run workflow`.

## Customize

Edit `keywords.txt` to add brands or terms you care about.

Edit `dealbot/config.py` to change feeds, score threshold, or price limits.

## Notes

This bot uses public RSS feeds. It does not scrape Amazon product pages and does not bypass anti-bot systems.
