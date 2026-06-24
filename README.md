# Amazon Deal AI Bot

A lightweight GitHub Actions bot that checks Slickdeals and Reddit RSS feeds, filters for Amazon/free/coupon/near-free deals, deduplicates alerts, and sends Discord notifications.

## What it does

- Runs every 5 minutes on GitHub Actions
- Watches Slickdeals + Reddit deal feeds
- Filters for Amazon, coupon, promo, free, price error, and <$5 deals
- Deduplicates using a JSON cache preserved by GitHub Actions cache
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

Edit `dealbot/config.py` to change feeds or defaults.

You can also set optional GitHub Actions repository variables without changing code:

| Variable | Default | Description |
| --- | --- | --- |
| `MAX_PRICE_DOLLARS` | `5.00` | Highest dollar price that counts as a low-price deal |
| `MIN_SCORE_TO_NOTIFY` | `5` | Minimum score required before sending a Discord alert |
| `MAX_ALERTS_PER_RUN` | `10` | Maximum number of Discord alerts sent per run |
| `USER_AGENT` | `amazon-deal-ai-bot/1.0 (+https://github.com/)` | User-Agent used for RSS requests |
| `SEEN_FILE` | `data/seen_deals.json` | Deduplication cache path |
| `KEYWORDS_FILE` | `keywords.txt` | Keyword list path |

`MAX_PRICE` is also accepted as a compatibility alias for `MAX_PRICE_DOLLARS`.

## Local validation

```bash
python3 -m unittest discover -s tests
```

## Notes

This bot uses public RSS feeds. It does not scrape Amazon product pages and does not bypass anti-bot systems.
