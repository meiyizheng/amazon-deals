# Deal AI Assistant

A lightweight GitHub Actions bot that monitors Slickdeals + Reddit RSS feeds and sends Amazon/free/coupon/price-error style deals to Discord.

## Files

- `main.py` - main bot
- `requirements.txt` - Python dependencies
- `.github/workflows/deal-bot.yml` - GitHub Actions schedule
- `data/deals.db` - created automatically for deduplication

## Setup

1. Upload all files to your GitHub repo.
2. Go to `Settings` → `Secrets and variables` → `Actions`.
3. Add a repository secret:
   - Name: `DISCORD_WEBHOOK`
   - Value: your Discord webhook URL
4. Go to `Actions` → `Deal Bot` → `Run workflow`.

## Change max price

In `.github/workflows/deal-bot.yml`, change:

```yaml
MAX_PRICE: "5"
```

For example, use `10` for $10 and under.
