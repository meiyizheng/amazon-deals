from __future__ import annotations
import re
import time
from .config import MAX_PRICE_DOLLARS, MAX_DEAL_AGE_HOURS
from .models import Deal

# ── Price regexes ─────────────────────────────────────────────────────────────

PRICE_RE = re.compile(r"(?<![A-Za-z])\$\s*(\d+(?:\.\d{1,2})?)")
PERCENT_RE = re.compile(r"(\d{2,3})\s*%\s*(?:off|discount)", re.I)

# "was $X" / "originally $X" / "reg. $X" / "msrp $X"
ORIG_PRICE_RE = re.compile(
    r"(?:was|originally|reg(?:ular)?\.?|msrp|retail|listed\s+at|valued\s+at)\s+\$\s*([\d,]+(?:\.\d{1,2})?)",
    re.I,
)
# "$X → $Y" or "$X -> $Y"
ARROW_PRICE_RE = re.compile(
    r"\$\s*([\d,]+(?:\.\d{1,2})?)\s*(?:→|->)\s*\$\s*([\d,]+(?:\.\d{1,2})?)"
)
# "save $X"
SAVE_RE = re.compile(r"save\s+\$\s*([\d,]+(?:\.\d{1,2})?)", re.I)

# Non-USD price signals (£, €, AU$, C$) — used to filter region-locked deals
NON_USD_RE = re.compile(r"(?:£|€|AU\$|C\$)\s*\d+|\d+\s*(?:GBP|EUR|CAD)\b", re.I)

# ── Term lists ────────────────────────────────────────────────────────────────

STRONG_TERMS = [
    "free", "freebie", "nearly free", "price error", "glitch",
    "coupon", "promo code", "coupon code",
    "subscribe & save", "ymmv", "stack", "stacking",
    "99% off", "95% off", "90% off",
    "$0", "$1", "$2", "$3", "$4", "$5",
]

# Amazon-platform-specific deal types (each worth extra points)
AMAZON_DEAL_TERMS = [
    "lightning deal",
    "deal of the day",
    "gold box",
    "clip coupon",
    "clip the coupon",
    "prime exclusive",
    "prime day deal",
    "warehouse deal",
    "amazon warehouse",
    "limited time deal",
]

AMAZON_TERMS = ["amazon", "amazon.com", "amzn"]

NOISE_TERMS = [
    "expired",
    "dead deal",
    "sold out",
    "[discussion]",
    "[request]",
    "looking for",
    "iso ",  # "in search of"
    "wtb ",  # "want to buy"
]


# ── Helper functions ──────────────────────────────────────────────────────────

def extract_prices(text: str) -> list[float]:
    prices = []
    for m in PRICE_RE.finditer(text):
        try:
            prices.append(float(m.group(1)))
        except ValueError:
            pass
    return prices


def extract_price_drop(text: str) -> tuple[float, float] | None:
    """
    Return (original_price, sale_price) when a clear was→now pattern is found.
    Returns None when no such pattern exists.
    """
    # Arrow pattern first: "$49.99 → $9.99"
    m = ARROW_PRICE_RE.search(text)
    if m:
        orig = float(m.group(1).replace(",", ""))
        sale = float(m.group(2).replace(",", ""))
        if orig > sale > 0:
            return orig, sale

    # "was $X …(up to 120 chars)… $Y"
    m = ORIG_PRICE_RE.search(text)
    if m:
        orig = float(m.group(1).replace(",", ""))
        after = text[m.end():]
        m2 = PRICE_RE.search(after[:120])
        if m2:
            sale = float(m2.group(1))
            if orig > sale > 0:
                return orig, sale

    return None


def discount_bonus(orig: float, sale: float) -> tuple[int, str]:
    """Return (score_bonus, human_label) for a detected price drop."""
    if orig <= 0:
        return 0, ""
    pct = (orig - sale) / orig * 100
    label = f"↓{pct:.0f}% off (${orig:.2f}→${sale:.2f})"
    if pct >= 90:
        return 5, label
    if pct >= 80:
        return 4, label
    if pct >= 70:
        return 3, label
    if pct >= 50:
        return 2, label
    return 0, ""


def is_fresh(deal: Deal) -> bool:
    """Return False if the deal's publish timestamp is older than MAX_DEAL_AGE_HOURS."""
    if deal.published_ts == 0:
        return True  # unknown age — let it through
    age_hours = (time.time() - deal.published_ts) / 3600
    return age_hours <= MAX_DEAL_AGE_HOURS


# ── Main scoring function ─────────────────────────────────────────────────────

def score_deal(deal: Deal, keywords: list[str]) -> Deal | None:
    """
    Score a deal and return an enriched Deal, or None if the deal should be dropped.
    Returns None when:
      - The deal is too old (exceeds MAX_DEAL_AGE_HOURS)
      - Noise terms are present
      - The deal appears to be non-US priced
      - The deal is not Amazon-related AND score is below the relevance threshold
    """
    if not is_fresh(deal):
        return None

    text = f"{deal.title} {deal.summary}".lower()
    score = 0
    reasons: list[str] = []
    original_price = 0.0
    discount_pct = 0.0

    # ── Hard drops ────────────────────────────────────────────────────────────
    if any(term in text for term in NOISE_TERMS):
        return None
    # Non-US deal: has £/€/AU$/C$ pricing but no USD $ at all
    if NON_USD_RE.search(text) and "$" not in text:
        return None

    # ── Amazon base signal ────────────────────────────────────────────────────
    if any(term in text for term in AMAZON_TERMS):
        score += 3
        reasons.append("Amazon相关")

    # ── Amazon platform-specific deal types ───────────────────────────────────
    matched_deal_types = [t for t in AMAZON_DEAL_TERMS if t in text]
    if matched_deal_types:
        # Each extra deal-type label adds 2 pts, capped at 6
        score += min(6, len(matched_deal_types) * 2)
        reasons.append("Amazon专项: " + ", ".join(matched_deal_types[:3]))

    # ── User keywords ─────────────────────────────────────────────────────────
    matched_keywords = [k for k in keywords if k and k in text]
    if matched_keywords:
        score += min(4, len(matched_keywords))
        reasons.append("关键词: " + ", ".join(matched_keywords[:5]))

    # ── Strong deal language ──────────────────────────────────────────────────
    strong_matches = [t for t in STRONG_TERMS if t in text]
    if strong_matches:
        score += min(6, len(strong_matches) * 2)
        reasons.append("强信号: " + ", ".join(strong_matches[:5]))

    # ── Low absolute price ────────────────────────────────────────────────────
    prices = extract_prices(text)
    low_prices = [p for p in prices if 0 <= p <= MAX_PRICE_DOLLARS]
    if low_prices:
        score += 4
        reasons.append(f"低价≤${MAX_PRICE_DOLLARS:.0f}: ${min(low_prices):.2f}")

    # ── Price-drop pattern (was/now, arrow) ───────────────────────────────────
    drop = extract_price_drop(text)
    if drop:
        original_price, sale_price = drop
        discount_pct = (original_price - sale_price) / original_price * 100
        bonus, label = discount_bonus(original_price, sale_price)
        if bonus:
            score += bonus
            reasons.append(label)

    # ── Explicit "X% off" in text (only when no was/now pattern found) ────────
    if not drop:
        percents = []
        for m in PERCENT_RE.finditer(text):
            try:
                percents.append(int(m.group(1)))
            except ValueError:
                pass
        if percents and max(percents) >= 80:
            score += 4
            reasons.append(f"大幅折扣: {max(percents)}% off")

    # ── "Save $X" boost ───────────────────────────────────────────────────────
    m_save = SAVE_RE.search(text)
    if m_save:
        saved = float(m_save.group(1).replace(",", ""))
        if saved >= 50:
            score += 2
            reasons.append(f"节省: ${saved:.0f}")
        elif saved >= 20:
            score += 1
            reasons.append(f"节省: ${saved:.0f}")

    # ── Relevance gate ────────────────────────────────────────────────────────
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
        published_ts=deal.published_ts,
        score=score,
        reason="；".join(reasons) if reasons else "可能相关",
        original_price=original_price,
        discount_pct=discount_pct,
    )
