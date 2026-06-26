from __future__ import annotations
import unittest
from unittest.mock import MagicMock, patch

from jobbot.linkedin_fetcher import (
    _job_id_from_url,
    _canonical_url,
    _make_id,
    _parse_cards,
)


# ── URL helpers ───────────────────────────────────────────────────────────────

class JobIdFromUrlTests(unittest.TestCase):
    def test_standard_view_url(self) -> None:
        url = "https://ng.linkedin.com/jobs/view/java-developer-at-acme-4012345678"
        self.assertEqual(_job_id_from_url(url), "4012345678")

    def test_currentjobid_param(self) -> None:
        url = "https://www.linkedin.com/jobs/search/?currentJobId=3987654321"
        self.assertEqual(_job_id_from_url(url), "3987654321")

    def test_no_id_returns_empty(self) -> None:
        self.assertEqual(_job_id_from_url("https://www.linkedin.com/jobs/"), "")


class CanonicalUrlTests(unittest.TestCase):
    def test_with_job_id(self) -> None:
        result = _canonical_url("https://ng.linkedin.com/jobs/view/...", "1234567890")
        self.assertEqual(result, "https://www.linkedin.com/jobs/view/1234567890/")

    def test_fallback_without_id(self) -> None:
        raw = "https://www.linkedin.com/jobs/view/something"
        self.assertEqual(_canonical_url(raw, ""), raw)


# ── Card parsing ──────────────────────────────────────────────────────────────

_SAMPLE_HTML = """
<ul>
  <li>
    <h3 class="base-search-card__title">Java Developer</h3>
    <h4 class="base-search-card__subtitle">Acme Corp</h4>
    <a href="https://www.linkedin.com/jobs/view/java-developer-at-acme-4012345678"></a>
    <span class="job-search-card__location">Remote</span>
  </li>
  <li>
    <h3 class="base-search-card__title">Backend Engineer</h3>
    <h4 class="base-search-card__subtitle">GlobalTech</h4>
    <a href="https://www.linkedin.com/jobs/view/backend-engineer-at-globaltech-4099887766"></a>
    <span class="job-search-card__location">Remote, Worldwide</span>
  </li>
</ul>
"""

_EMPTY_HTML = "<ul></ul>"
_NO_LINK_HTML = "<ul><li><h3>Some Job</h3><h4>Some Co</h4></li></ul>"


class ParseCardsTests(unittest.TestCase):
    def _parse(self, html: str, fetch_desc: bool = False) -> list:
        mock_session = MagicMock()
        return _parse_cards(html, fetch_desc, mock_session)

    def test_parses_two_cards(self) -> None:
        jobs = self._parse(_SAMPLE_HTML)
        self.assertEqual(len(jobs), 2)

    def test_title_extracted(self) -> None:
        jobs = self._parse(_SAMPLE_HTML)
        self.assertEqual(jobs[0].title, "Java Developer")

    def test_company_extracted(self) -> None:
        jobs = self._parse(_SAMPLE_HTML)
        self.assertEqual(jobs[0].company, "Acme Corp")

    def test_link_is_canonical(self) -> None:
        jobs = self._parse(_SAMPLE_HTML)
        self.assertIn("linkedin.com/jobs/view/4012345678", jobs[0].link)

    def test_source_is_linkedin(self) -> None:
        jobs = self._parse(_SAMPLE_HTML)
        self.assertEqual(jobs[0].source, "linkedin.com")

    def test_empty_html_returns_empty_list(self) -> None:
        self.assertEqual(self._parse(_EMPTY_HTML), [])

    def test_card_without_link_skipped(self) -> None:
        self.assertEqual(self._parse(_NO_LINK_HTML), [])

    def test_ids_are_unique(self) -> None:
        jobs = self._parse(_SAMPLE_HTML)
        ids = [j.id for j in jobs]
        self.assertEqual(len(ids), len(set(ids)))

    def test_description_not_fetched_when_disabled(self) -> None:
        mock_session = MagicMock()
        _parse_cards(_SAMPLE_HTML, fetch_descriptions=False, session=mock_session)
        mock_session.get.assert_not_called()


if __name__ == "__main__":
    unittest.main()
