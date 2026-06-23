from __future__ import annotations
import re
from .config import MAX_PRICE_DOLLARS
from .models import Deal

PRICE_RE = re.compile(r"(?<![A-Za-z])\$\s*(\d+(?:\.\d{1,2})?)")
PERCENT_RE = re.compile(r"(\d{2,3})\s*%\s*(?:off|discount)", re.I)

STRONG_TERMS = [
    "free", "freebie", "nearly free", "price error", "glitch", "coupon", "promo code", "coupon code",
    "subscribe & save", "ymmv", "stack", "stacking", "99% off", "95% off", "90% off", "$0", "$1", "$2", "$3", "$4", "$5",
]
AMAZON_TERMS = ["amazon", "amazon.com", "amzn"]
NOISE_TERMS = ["expired", "dead deal", "sold out"]


def extract_prices(text: str) -> list[float]:
    prices = []
    for m in PRICE_RE.finditer(text):
        try:
            prices.append(float(m.group(1)))
        except ValueError:
            pass
    return prices


def score_deal(deal: Deal, keywords: list[str]) -> Deal | None:
    text = f"{deal.title} {deal.summary}".lower()
    score = 0
    reasons: list[str] = []

    if any(term in text for term in NOISE_TERMS):
        return None

    if any(term in text for term in AMAZON_TERMS):
        score += 3
        reasons.append("Amazon相关")

    matched_keywords = [k for k in keywords if k and k in text]
    if matched_keywords:
        score += min(4, len(matched_keywords))
        reasons.append("关键词: " + ", ".join(matched_keywords[:5]))

    strong_matches = [t for t in STRONG_TERMS if t in text]
    if strong_matches:
        score += min(6, len(strong_matches) * 2)
        reasons.append("强信号: " + ", ".join(strong_matches[:5]))

    prices = extract_prices(text)
    low_prices = [p for p in prices if 0 <= p <= MAX_PRICE_DOLLARS]
    if low_prices:
        score += 4
        reasons.append(f"低价≤${MAX_PRICE_DOLLARS:.0f}: ${min(low_prices):.2f}")

    percents = []
    for m in PERCENT_RE.finditer(text):
        try:
            percents.append(int(m.group(1)))
        except ValueError:
            pass
    if percents and max(percents) >= 80:
        score += 4
        reasons.append(f"大幅折扣: {max(percents)}% off")

    # Require either Amazon OR very strong deal language. This keeps notifications relevant.
    is_relevant = any(term in text for term in AMAZON_TERMS) or score >= 8
    if not is_relevant:
        return None

    return Deal(
        id=deal.id,
        title=deal.title,
        link=deal.link,
        source=deal.source,
        summary=deal.summary,
        published=deal.published,
        score=score,
        reason="；".join(reasons) if reasons else "可能相关",
    )
