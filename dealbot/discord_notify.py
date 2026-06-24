from __future__ import annotations
import time
import os
import requests
from .models import Deal

# ── Tier definitions ──────────────────────────────────────────────────────────
# Each entry: (min_score, label, Discord embed color as decimal int)
_TIERS: list[tuple[int, str, int]] = [
    (12, "🚨 FIRE DEAL", 0xE74C3C),   # ≥12 → red
    (8,  "🔥 Hot Deal",  0xE67E22),   # 8–11 → orange
    (0,  "💰 Good Deal", 0x2ECC71),   # 5–7  → green
]

_SUMMARY_COLOR = 0x3498DB       # blue for the run-summary embed
_FOOTER_TEXT = "Amazon Deal Bot"
_INTER_POST_DELAY = 0.8         # seconds between individual Discord posts
_MAX_RETRIES = 3
_SUMMARY_THRESHOLD = 3          # send a summary embed when this many alerts or more


# ── Internal helpers ──────────────────────────────────────────────────────────

def _tier(score: int) -> tuple[str, int]:
    for threshold, label, color in _TIERS:
        if score >= threshold:
            return label, color
    return "💰 Good Deal", 0x2ECC71


def _build_embed(deal: Deal) -> dict:
    tier_label, color = _tier(deal.score)
    # Discord embed title max = 256 chars
    title = f"{tier_label}  {deal.title}"[:256]

    fields: list[dict] = []

    if deal.original_price > 0 and deal.discount_pct > 0:
        sale_price = deal.original_price * (1 - deal.discount_pct / 100)
        price_str = (
            f"~~${deal.original_price:.2f}~~ → **${sale_price:.2f}**\n"
            f"(↓{deal.discount_pct:.0f}% off)"
        )
        fields.append({"name": "💰 价格", "value": price_str, "inline": True})

    fields.append({"name": "⭐ 评分", "value": str(deal.score), "inline": True})
    fields.append({"name": "📌 来源", "value": deal.source[:100], "inline": True})

    return {
        "title": title,
        "url": deal.link,
        "color": color,
        # reason string (e.g. "Amazon相关；lightning deal；↓83% off") as description
        "description": (deal.reason or "可能相关")[:1024],
        "fields": fields,
        "footer": {"text": _FOOTER_TEXT},
    }


def _build_summary_embed(deals: list[Deal]) -> dict:
    lines: list[str] = []
    for d in deals:
        tier_label, _ = _tier(d.score)
        short_title = d.title[:80].rstrip()
        lines.append(f"{tier_label} **[{short_title}]({d.link})** (评分 {d.score})")
    return {
        "title": f"🔔 本次发现 {len(deals)} 条好价线索",
        "description": "\n".join(lines)[:4096],
        "color": _SUMMARY_COLOR,
        "footer": {"text": _FOOTER_TEXT},
    }


def _post_with_retry(webhook: str, payload: dict) -> None:
    """POST to Discord with automatic retry on 429 rate-limit and transient errors."""
    for attempt in range(_MAX_RETRIES):
        try:
            resp = requests.post(webhook, json=payload, timeout=20)
        except requests.RequestException as exc:
            print(f"WARN: Discord request failed (attempt {attempt + 1}): {exc}")
            if attempt < _MAX_RETRIES - 1:
                time.sleep(2 ** attempt)
            continue

        if resp.status_code == 429:
            try:
                retry_after = float(resp.json().get("retry_after", 1.0))
            except Exception:
                retry_after = 1.0
            print(f"WARN: Discord rate-limited, retrying after {retry_after:.1f}s")
            time.sleep(retry_after)
            continue

        if resp.status_code >= 300:
            print(f"WARN: Discord returned {resp.status_code}: {resp.text[:300]}")
        return  # success or non-retryable error


# ── Public interface ──────────────────────────────────────────────────────────

def format_deal(deal: Deal) -> str:
    """Plain-text representation used when no webhook is configured."""
    tier_label, _ = _tier(deal.score)
    lines = [
        tier_label,
        f"  {deal.title[:230]}",
        f"  Score: {deal.score}  |  {deal.reason[:200]}",
        f"  Source: {deal.source}",
        f"  {deal.link}",
    ]
    return "\n".join(lines)


def send_discord(deals: list[Deal]) -> None:
    webhook = os.getenv("DISCORD_WEBHOOK")
    if not webhook:
        print("DISCORD_WEBHOOK is not set. Printing alerts instead.")
        for deal in deals:
            print(format_deal(deal))
            print()
        return

    # Summary embed when there are multiple deals
    if len(deals) >= _SUMMARY_THRESHOLD:
        _post_with_retry(webhook, {"embeds": [_build_summary_embed(deals)]})
        time.sleep(_INTER_POST_DELAY)

    # Individual embeds, highest-scored first
    for deal in deals:
        _post_with_retry(webhook, {"embeds": [_build_embed(deal)]})
        time.sleep(_INTER_POST_DELAY)
