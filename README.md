# Amazon Deal AI Bot

A lightweight GitHub Actions bot that checks Slickdeals and Reddit RSS feeds, filters for Amazon/free/coupon/near-free deals, deduplicates alerts, and sends Discord notifications.

## What it does

- Runs every 5 minutes on GitHub Actions
- Watches **14 RSS feeds**: Slickdeals (frontpage + 4 Amazon keyword searches) and Reddit (r/amazondeals, r/extremedeals, r/Frugal, r/HotDeals, r/deals, r/buildapcsales, r/GameDeals, r/FreeGameFindings, r/frugalmalefashion)
- Filters and scores deals using:
  - Amazon base signal, Lightning Deal / Deal of the Day / Gold Box / Clip Coupon / Prime Exclusive / Warehouse Deal types
  - Was→Now price-drop pattern (`was $X, now $Y` and `$X → $Y`) with calculated discount %
  - Explicit `X% off` and `save $X` phrases
  - User-defined brand/term keywords
  - Low absolute price (≤ configurable threshold)
- Skips deals older than 6 hours (configurable)
- Filters non-US currency deals (£/€/AU$/C$ only) and noise posts ([Discussion], [Request], sold out, expired)
- Deduplicates using a JSON cache (atomic write) preserved by GitHub Actions cache
- Marks all evaluated deals as seen (not just notified ones) to prevent re-flood after cache eviction
- Sends tiered Discord alerts via webhook:
  - 🚨 **FIRE DEAL** (score ≥ 12): red embed
  - 🔥 **Hot Deal** (score 8–11): orange embed
  - 💰 **Good Deal** (score 5–7): green embed
  - Consolidated summary embed when ≥ 3 deals found in one run
  - 0.8 s inter-post delay + automatic retry on Discord 429 rate-limit

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
| `MAX_DEAL_AGE_HOURS` | `6` | Skip deals older than this many hours (0 = no age filter) |
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
