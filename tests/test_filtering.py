from __future__ import annotations

import unittest

from dealbot.filtering import extract_prices, score_deal
from dealbot.models import Deal


def make_deal(title: str, summary: str = "", link: str = "https://example.com/deal") -> Deal:
    return Deal(
        id="deal-1",
        title=title,
        link=link,
        source="example.com",
        summary=summary,
    )


class ExtractPricesTests(unittest.TestCase):
    def test_extracts_dollar_prices(self) -> None:
        self.assertEqual(extract_prices("Now $2.50, was $19.99"), [2.50, 19.99])

    def test_ignores_currency_like_letters(self) -> None:
        self.assertEqual(extract_prices("Model ABC$5 is not a price, but $4 is"), [4.0])


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


if __name__ == "__main__":
    unittest.main()
