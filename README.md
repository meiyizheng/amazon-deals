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

---

# Remote SDE Testing Job Bot

A second GitHub Actions bot that monitors remote **Software Development Engineer in Test (SDET)** job listings across multiple job boards and sends Discord alerts.

## What it does

- Runs every **2 hours** on GitHub Actions
- Watches **8 RSS feeds**: RemoteOK (QA/test/SDET/dev+test categories), WeWorkRemotely (programming + all jobs), Himalayas, Arbeitnow
- Scores listings using:
  - SDET / SDE-in-Test title match (+8)
  - Automation engineering terms (+5)
  - General QA engineering (+3)
  - Coding signals in description: Python, Selenium, Playwright, pytest, CI/CD, etc. (+1 each, up to +4)
  - Remote board bonus (+2) or explicit remote mention in text (+3)
  - User-defined tech-stack keywords from `job_keywords.txt`
  - Salary listed (+1)
- Skips listings older than 48 hours (configurable)
- Filters noise: manual-only roles, onsite-only, no-coding-required
- Sends tiered Discord Embeds via `JOB_DISCORD_WEBHOOK`:
  - 🔥 完美匹配 (score ≥ 12) → green
  - 💼 强力匹配 (score 9–11) → blue
  - 🎯 可能匹配 (score 7–8) → grey-blue
  - Summary embed when ≥ 3 matches per run

## Setup

1. In GitHub, go to `Settings` → `Secrets and variables` → `Actions`.
2. Add a repository secret:
   - Name: `JOB_DISCORD_WEBHOOK`
   - Value: your Discord webhook URL (can be a different channel than the deal bot)
3. Go to `Actions` → `Remote SDE Job Bot` → `Run workflow`.

## Customize

Edit `job_keywords.txt` to add the tech stack you care about (Python, Playwright, AWS, etc.) — each match raises a listing's score.

Optional GitHub Actions repository variables:

| Variable | Default | Description |
| --- | --- | --- |
| `JOB_MIN_SCORE` | `7` | Minimum score before sending a Discord alert |
| `JOB_MAX_ALERTS` | `15` | Maximum alerts per run |
| `JOB_MAX_AGE_HOURS` | `48` | Skip listings older than this many hours |
| `JOB_SEEN_FILE` | `data/seen_jobs.json` | Dedup cache path |
| `JOB_KEYWORDS_FILE` | `job_keywords.txt` | Keyword list path |
