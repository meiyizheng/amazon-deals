from __future__ import annotations
import os
import requests
from .models import Deal


def format_deal(deal: Deal) -> str:
    title = deal.title[:230]
    reason = deal.reason[:300]
    return (
        f"🔥 **Amazon / 神价线索**\n"
        f"**{title}**\n"
        f"Score: `{deal.score}`\n"
        f"Reason: {reason}\n"
        f"Source: `{deal.source}`\n"
        f"{deal.link}"
    )


def send_discord(deals: list[Deal]) -> None:
    webhook = os.getenv("DISCORD_WEBHOOK")
    if not webhook:
        print("DISCORD_WEBHOOK is not set. Printing alerts instead.")
        for deal in deals:
            print(format_deal(deal))
        return

    for deal in deals:
        payload = {"content": format_deal(deal)}
        resp = requests.post(webhook, json=payload, timeout=20)
        if resp.status_code >= 300:
            print(f"WARN: Discord returned {resp.status_code}: {resp.text[:300]}")
