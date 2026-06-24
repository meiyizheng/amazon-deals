from __future__ import annotations

import unittest
from unittest.mock import MagicMock, call, patch

from dealbot.discord_notify import (
    _build_embed,
    _build_summary_embed,
    _tier,
    format_deal,
    send_discord,
)
from dealbot.models import Deal


def make_deal(
    title: str = "Amazon deal",
    score: int = 7,
    reason: str = "Amazon相关；coupon",
    link: str = "https://amazon.com/dp/test",
    source: str = "slickdeals.net",
    original_price: float = 0.0,
    discount_pct: float = 0.0,
) -> Deal:
    return Deal(
        id="test-deal",
        title=title,
        link=link,
        source=source,
        summary="",
        score=score,
        reason=reason,
        original_price=original_price,
        discount_pct=discount_pct,
    )


# ── _tier ─────────────────────────────────────────────────────────────────────

class TierTests(unittest.TestCase):
    def test_fire_deal_at_12(self) -> None:
        label, color = _tier(12)
        self.assertIn("FIRE", label)
        self.assertEqual(color, 0xE74C3C)

    def test_fire_deal_above_12(self) -> None:
        label, _ = _tier(15)
        self.assertIn("FIRE", label)

    def test_hot_deal_at_8(self) -> None:
        label, color = _tier(8)
        self.assertIn("Hot", label)
        self.assertEqual(color, 0xE67E22)

    def test_hot_deal_at_11(self) -> None:
        label, _ = _tier(11)
        self.assertIn("Hot", label)

    def test_good_deal_at_5(self) -> None:
        label, color = _tier(5)
        self.assertIn("Good", label)
        self.assertEqual(color, 0x2ECC71)

    def test_good_deal_at_7(self) -> None:
        label, _ = _tier(7)
        self.assertIn("Good", label)


# ── _build_embed ──────────────────────────────────────────────────────────────

class BuildEmbedTests(unittest.TestCase):
    def test_embed_has_required_keys(self) -> None:
        deal = make_deal()
        embed = _build_embed(deal)
        for key in ("title", "url", "color", "description", "fields", "footer"):
            self.assertIn(key, embed)

    def test_embed_title_within_limit(self) -> None:
        long_title = "A" * 300
        deal = make_deal(title=long_title)
        embed = _build_embed(deal)
        self.assertLessEqual(len(embed["title"]), 256)

    def test_embed_color_matches_tier(self) -> None:
        fire_deal = make_deal(score=14)
        _, expected_color = _tier(14)
        self.assertEqual(_build_embed(fire_deal)["color"], expected_color)

    def test_price_field_shown_when_drop_detected(self) -> None:
        deal = make_deal(original_price=49.99, discount_pct=80.0)
        embed = _build_embed(deal)
        field_names = [f["name"] for f in embed["fields"]]
        self.assertIn("💰 价格", field_names)

    def test_price_field_absent_without_drop(self) -> None:
        deal = make_deal(original_price=0.0, discount_pct=0.0)
        embed = _build_embed(deal)
        field_names = [f["name"] for f in embed["fields"]]
        self.assertNotIn("💰 价格", field_names)

    def test_score_and_source_fields_always_present(self) -> None:
        deal = make_deal()
        embed = _build_embed(deal)
        field_names = [f["name"] for f in embed["fields"]]
        self.assertIn("⭐ 评分", field_names)
        self.assertIn("📌 来源", field_names)

    def test_embed_url_matches_deal_link(self) -> None:
        deal = make_deal(link="https://example.com/deal/123")
        embed = _build_embed(deal)
        self.assertEqual(embed["url"], "https://example.com/deal/123")


# ── _build_summary_embed ──────────────────────────────────────────────────────

class BuildSummaryEmbedTests(unittest.TestCase):
    def test_summary_contains_all_deal_titles(self) -> None:
        deals = [make_deal(title=f"Deal {i}", score=10 - i) for i in range(3)]
        embed = _build_summary_embed(deals)
        for i in range(3):
            self.assertIn(f"Deal {i}", embed["description"])

    def test_summary_title_shows_count(self) -> None:
        deals = [make_deal() for _ in range(5)]
        embed = _build_summary_embed(deals)
        self.assertIn("5", embed["title"])

    def test_summary_description_within_limit(self) -> None:
        deals = [make_deal(title="X" * 100, score=10) for _ in range(20)]
        embed = _build_summary_embed(deals)
        self.assertLessEqual(len(embed["description"]), 4096)


# ── format_deal (plain text fallback) ────────────────────────────────────────

class FormatDealTests(unittest.TestCase):
    def test_contains_title_and_score(self) -> None:
        deal = make_deal(title="Amazing deal", score=9)
        text = format_deal(deal)
        self.assertIn("Amazing deal", text)
        self.assertIn("9", text)

    def test_contains_link(self) -> None:
        deal = make_deal(link="https://amazon.com/dp/B001")
        text = format_deal(deal)
        self.assertIn("https://amazon.com/dp/B001", text)


# ── send_discord ──────────────────────────────────────────────────────────────

class SendDiscordTests(unittest.TestCase):
    def test_prints_when_no_webhook(self) -> None:
        deals = [make_deal()]
        with patch.dict("os.environ", {"DISCORD_WEBHOOK": ""}, clear=False):
            with patch("builtins.print") as mock_print:
                send_discord(deals)
        # At minimum one print call should contain the deal title
        all_printed = " ".join(str(c) for c in mock_print.call_args_list)
        self.assertIn("Amazon deal", all_printed)

    def test_posts_embeds_to_webhook(self) -> None:
        deals = [make_deal(score=9)]
        mock_resp = MagicMock()
        mock_resp.status_code = 204

        with patch.dict("os.environ", {"DISCORD_WEBHOOK": "https://discord.test/hook"}, clear=False):
            with patch("dealbot.discord_notify.requests.post", return_value=mock_resp) as mock_post:
                with patch("dealbot.discord_notify.time.sleep"):
                    send_discord(deals)

        self.assertTrue(mock_post.called)
        # Payload should use embeds key
        call_kwargs = mock_post.call_args_list[0].kwargs
        self.assertIn("embeds", call_kwargs.get("json", {}))

    def test_summary_sent_for_three_or_more_deals(self) -> None:
        deals = [make_deal(score=9, title=f"Deal {i}") for i in range(3)]
        mock_resp = MagicMock()
        mock_resp.status_code = 204

        with patch.dict("os.environ", {"DISCORD_WEBHOOK": "https://discord.test/hook"}, clear=False):
            with patch("dealbot.discord_notify.requests.post", return_value=mock_resp) as mock_post:
                with patch("dealbot.discord_notify.time.sleep"):
                    send_discord(deals)

        # Should have: 1 summary + 3 individual = 4 total posts
        self.assertEqual(mock_post.call_count, 4)

    def test_no_summary_for_two_deals(self) -> None:
        deals = [make_deal(score=9, title=f"Deal {i}") for i in range(2)]
        mock_resp = MagicMock()
        mock_resp.status_code = 204

        with patch.dict("os.environ", {"DISCORD_WEBHOOK": "https://discord.test/hook"}, clear=False):
            with patch("dealbot.discord_notify.requests.post", return_value=mock_resp) as mock_post:
                with patch("dealbot.discord_notify.time.sleep"):
                    send_discord(deals)

        # No summary, just 2 individual posts
        self.assertEqual(mock_post.call_count, 2)

    def test_retries_on_429_rate_limit(self) -> None:
        deals = [make_deal()]
        rate_limit_resp = MagicMock()
        rate_limit_resp.status_code = 429
        rate_limit_resp.json.return_value = {"retry_after": 0.1}
        ok_resp = MagicMock()
        ok_resp.status_code = 204

        with patch.dict("os.environ", {"DISCORD_WEBHOOK": "https://discord.test/hook"}, clear=False):
            with patch(
                "dealbot.discord_notify.requests.post",
                side_effect=[rate_limit_resp, ok_resp],
            ) as mock_post:
                with patch("dealbot.discord_notify.time.sleep"):
                    send_discord(deals)

        # First call hit 429, second call succeeded
        self.assertEqual(mock_post.call_count, 2)

    def test_inter_post_delay_called(self) -> None:
        deals = [make_deal(score=9)]
        mock_resp = MagicMock()
        mock_resp.status_code = 204

        with patch.dict("os.environ", {"DISCORD_WEBHOOK": "https://discord.test/hook"}, clear=False):
            with patch("dealbot.discord_notify.requests.post", return_value=mock_resp):
                with patch("dealbot.discord_notify.time.sleep") as mock_sleep:
                    send_discord(deals)

        self.assertTrue(mock_sleep.called)


if __name__ == "__main__":
    unittest.main()
