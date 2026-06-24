from __future__ import annotations

import time
import unittest

from dealbot.filtering import (
    discount_bonus,
    extract_price_drop,
    extract_prices,
    is_fresh,
    score_deal,
)
from dealbot.models import Deal


def make_deal(
    title: str,
    summary: str = "",
    link: str = "https://example.com/deal",
    published_ts: float = 0.0,
) -> Deal:
    return Deal(
        id="deal-1",
        title=title,
        link=link,
        source="example.com",
        summary=summary,
        published_ts=published_ts,
    )


# ── extract_prices ────────────────────────────────────────────────────────────

class ExtractPricesTests(unittest.TestCase):
    def test_extracts_dollar_prices(self) -> None:
        self.assertEqual(extract_prices("Now $2.50, was $19.99"), [2.50, 19.99])

    def test_ignores_currency_like_letters(self) -> None:
        self.assertEqual(extract_prices("Model ABC$5 is not a price, but $4 is"), [4.0])


# ── extract_price_drop ────────────────────────────────────────────────────────

class ExtractPriceDropTests(unittest.TestCase):
    def test_was_now_pattern(self) -> None:
        result = extract_price_drop("was $49.99, now $9.99")
        self.assertIsNotNone(result)
        assert result is not None
        self.assertAlmostEqual(result[0], 49.99)
        self.assertAlmostEqual(result[1], 9.99)

    def test_arrow_pattern(self) -> None:
        result = extract_price_drop("price drop $79.99 → $19.99")
        self.assertIsNotNone(result)
        assert result is not None
        self.assertAlmostEqual(result[0], 79.99)
        self.assertAlmostEqual(result[1], 19.99)

    def test_originally_pattern(self) -> None:
        result = extract_price_drop("Originally $100, grab it for $25 today")
        self.assertIsNotNone(result)
        assert result is not None
        self.assertAlmostEqual(result[0], 100.0)
        self.assertAlmostEqual(result[1], 25.0)

    def test_no_drop_when_prices_equal(self) -> None:
        self.assertIsNone(extract_price_drop("was $10, now $10"))

    def test_no_drop_when_reversed(self) -> None:
        self.assertIsNone(extract_price_drop("was $5, now $20"))

    def test_returns_none_when_no_pattern(self) -> None:
        self.assertIsNone(extract_price_drop("great deal on headphones"))


# ── discount_bonus ────────────────────────────────────────────────────────────

class DiscountBonusTests(unittest.TestCase):
    def test_90pct_drop_gives_max_bonus(self) -> None:
        bonus, label = discount_bonus(100.0, 9.0)
        self.assertEqual(bonus, 5)
        self.assertIn("91%", label)

    def test_80pct_drop(self) -> None:
        bonus, _ = discount_bonus(100.0, 18.0)
        self.assertEqual(bonus, 4)

    def test_70pct_drop(self) -> None:
        bonus, _ = discount_bonus(100.0, 28.0)
        self.assertEqual(bonus, 3)

    def test_50pct_drop(self) -> None:
        bonus, _ = discount_bonus(100.0, 49.0)
        self.assertEqual(bonus, 2)

    def test_small_drop_gives_no_bonus(self) -> None:
        bonus, _ = discount_bonus(100.0, 80.0)
        self.assertEqual(bonus, 0)


# ── is_fresh ──────────────────────────────────────────────────────────────────

class IsFreshTests(unittest.TestCase):
    def test_unknown_ts_passes(self) -> None:
        deal = make_deal("any title", published_ts=0.0)
        self.assertTrue(is_fresh(deal))

    def test_recent_deal_passes(self) -> None:
        ts = time.time() - 3600  # 1 hour ago
        deal = make_deal("any title", published_ts=ts)
        self.assertTrue(is_fresh(deal))

    def test_old_deal_filtered(self) -> None:
        ts = time.time() - (7 * 3600)  # 7 hours ago (default limit is 6h)
        deal = make_deal("any title", published_ts=ts)
        self.assertFalse(is_fresh(deal))


# ── score_deal ────────────────────────────────────────────────────────────────

class ScoreDealTests(unittest.TestCase):
    def test_scores_low_price_amazon_deal(self) -> None:
        deal = make_deal(
            "Amazon coupon: headphones for $2",
            "Limited promo code stacks with subscribe & save",
        )
        scored = score_deal(deal, keywords=[])
        self.assertIsNotNone(scored)
        assert scored is not None
        self.assertGreaterEqual(scored.score, 5)
        self.assertIn("Amazon", scored.reason)

    def test_filters_expired_or_dead_deals(self) -> None:
        deal = make_deal("Amazon $1 charger expired", "dead deal")
        self.assertIsNone(score_deal(deal, keywords=[]))

    def test_filters_weak_non_amazon_low_price_deal(self) -> None:
        deal = make_deal("Generic socks for $4", "Small discount")
        self.assertIsNone(score_deal(deal, keywords=[]))

    def test_allows_very_strong_non_amazon_discount(self) -> None:
        deal = make_deal("Coupon stack gives 90% off clearance", "No marketplace mention")
        scored = score_deal(deal, keywords=[])
        self.assertIsNotNone(scored)
        assert scored is not None
        self.assertGreaterEqual(scored.score, 8)

    def test_user_keywords_raise_score(self) -> None:
        deal = make_deal("Amazon Anker USB cable deal", "Works with promo code")
        scored = score_deal(deal, keywords=["anker", "usb"])
        self.assertIsNotNone(scored)
        assert scored is not None
        self.assertIn("anker", scored.reason)
        self.assertGreaterEqual(scored.score, 7)

    def test_amazon_lightning_deal_boosts_score(self) -> None:
        deal = make_deal("Amazon Lightning Deal: Sony headphones $49")
        scored = score_deal(deal, keywords=[])
        self.assertIsNotNone(scored)
        assert scored is not None
        self.assertGreater(scored.score, 5)
        self.assertIn("lightning deal", scored.reason)

    def test_was_now_price_drop_detected(self) -> None:
        deal = make_deal(
            "Amazon HDMI cable was $29.99, now $4.99",
            "Great value",
        )
        scored = score_deal(deal, keywords=[])
        self.assertIsNotNone(scored)
        assert scored is not None
        self.assertGreater(scored.original_price, 0)
        self.assertGreater(scored.discount_pct, 50)
        self.assertIn("↓", scored.reason)

    def test_old_deal_filtered_by_freshness(self) -> None:
        stale_ts = time.time() - (10 * 3600)  # 10 hours ago
        deal = make_deal("Amazon $1 promo code coupon", published_ts=stale_ts)
        self.assertIsNone(score_deal(deal, keywords=[]))

    def test_non_usd_deal_filtered(self) -> None:
        deal = make_deal("Headphones £29.99 from UK retailer", "No USD pricing here")
        self.assertIsNone(score_deal(deal, keywords=[]))

    def test_non_usd_with_usd_not_filtered(self) -> None:
        # A US Amazon deal that mentions a UK price in comparison should still pass
        deal = make_deal(
            "Amazon deal: was £80 in UK, now $29.99 in US",
            "Great Amazon exclusive",
        )
        scored = score_deal(deal, keywords=[])
        self.assertIsNotNone(scored)

    def test_discussion_post_filtered(self) -> None:
        deal = make_deal("[Discussion] best amazon deals this week")
        self.assertIsNone(score_deal(deal, keywords=[]))


if __name__ == "__main__":
    unittest.main()
