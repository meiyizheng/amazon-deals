from __future__ import annotations

import importlib
import os
import unittest
from unittest.mock import patch

import dealbot.config as config


class ConfigEnvTests(unittest.TestCase):
    def tearDown(self) -> None:
        importlib.reload(config)

    def test_empty_environment_values_use_defaults(self) -> None:
        with patch.dict(
            os.environ,
            {
                "MAX_PRICE_DOLLARS": "",
                "MIN_SCORE_TO_NOTIFY": "",
                "MAX_ALERTS_PER_RUN": "",
                "MAX_DEAL_AGE_HOURS": "",
                "SEEN_FILE": "",
                "KEYWORDS_FILE": "",
                "USER_AGENT": "",
            },
            clear=False,
        ):
            reloaded = importlib.reload(config)

        self.assertEqual(reloaded.MAX_PRICE_DOLLARS, 5.00)
        self.assertEqual(reloaded.MIN_SCORE_TO_NOTIFY, 5)
        self.assertEqual(reloaded.MAX_ALERTS_PER_RUN, 10)
        self.assertEqual(reloaded.MAX_DEAL_AGE_HOURS, 6)
        self.assertEqual(reloaded.SEEN_FILE, "data/seen_deals.json")
        self.assertEqual(reloaded.KEYWORDS_FILE, "keywords.txt")
        self.assertIn("amazon-deal-bot", reloaded.USER_AGENT)

    def test_environment_overrides_defaults(self) -> None:
        with patch.dict(
            os.environ,
            {
                "MAX_PRICE_DOLLARS": "2.50",
                "MIN_SCORE_TO_NOTIFY": "7",
                "MAX_ALERTS_PER_RUN": "3",
                "MAX_DEAL_AGE_HOURS": "12",
                "SEEN_FILE": "tmp/seen.json",
                "KEYWORDS_FILE": "tmp/keywords.txt",
                "USER_AGENT": "custom-agent/1.0",
            },
            clear=False,
        ):
            reloaded = importlib.reload(config)

        self.assertEqual(reloaded.MAX_PRICE_DOLLARS, 2.50)
        self.assertEqual(reloaded.MIN_SCORE_TO_NOTIFY, 7)
        self.assertEqual(reloaded.MAX_ALERTS_PER_RUN, 3)
        self.assertEqual(reloaded.MAX_DEAL_AGE_HOURS, 12)
        self.assertEqual(reloaded.SEEN_FILE, "tmp/seen.json")
        self.assertEqual(reloaded.KEYWORDS_FILE, "tmp/keywords.txt")
        self.assertEqual(reloaded.USER_AGENT, "custom-agent/1.0")

    def test_max_price_alias_is_supported(self) -> None:
        with patch.dict(os.environ, {"MAX_PRICE_DOLLARS": "", "MAX_PRICE": "3.75"}, clear=False):
            reloaded = importlib.reload(config)

        self.assertEqual(reloaded.MAX_PRICE_DOLLARS, 3.75)


if __name__ == "__main__":
    unittest.main()
