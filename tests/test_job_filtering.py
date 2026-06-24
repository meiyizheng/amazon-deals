from __future__ import annotations

import time
import unittest

from jobbot.filtering import is_fresh, score_job
from jobbot.models import Job


def make_job(
    title: str = "Software Engineer",
    company: str = "Acme Corp",
    description: str = "",
    source: str = "remoteok.com",
    is_remote_board: bool = True,
    published_ts: float = 0.0,
    salary: str = "",
    location: str = "Remote",
) -> Job:
    return Job(
        id="test-job-1",
        title=title,
        company=company,
        link="https://example.com/job/1",
        source=source,
        location=location,
        description=description,
        published_ts=published_ts,
        salary=salary,
        is_remote_board=is_remote_board,
    )


# ── is_fresh ──────────────────────────────────────────────────────────────────

class IsFreshTests(unittest.TestCase):
    def test_unknown_ts_always_passes(self) -> None:
        job = make_job(published_ts=0.0)
        self.assertTrue(is_fresh(job))

    def test_recent_job_passes(self) -> None:
        job = make_job(published_ts=time.time() - 3600)  # 1h ago
        self.assertTrue(is_fresh(job))

    def test_very_old_job_filtered(self) -> None:
        job = make_job(published_ts=time.time() - (72 * 3600))  # 72h ago (default limit 48h)
        self.assertFalse(is_fresh(job))


# ── score_job ─────────────────────────────────────────────────────────────────

class ScoreJobTests(unittest.TestCase):

    # ── SDET / SDE-in-Test ───────────────────────────────────────────────────

    def test_sdet_title_scores_high(self) -> None:
        job = make_job(title="Senior SDET", description="Selenium, Python, CI/CD")
        result = score_job(job, keywords=[])
        self.assertIsNotNone(result)
        assert result is not None
        self.assertGreaterEqual(result.score, 8)
        self.assertIn("SDET", result.reason)

    def test_software_engineer_in_test_scores_high(self) -> None:
        job = make_job(title="Software Engineer in Test", description="AWS, pytest, automation")
        result = score_job(job, keywords=[])
        self.assertIsNotNone(result)
        assert result is not None
        self.assertGreaterEqual(result.score, 8)

    def test_full_sdet_phrase_detected(self) -> None:
        job = make_job(
            title="Software Development Engineer in Test",
            description="Build automation frameworks in Python"
        )
        result = score_job(job, keywords=[])
        self.assertIsNotNone(result)
        assert result is not None
        self.assertIn("SDET", result.reason)

    # ── Automation engineering ────────────────────────────────────────────────

    def test_automation_engineer_detected(self) -> None:
        job = make_job(title="Test Automation Engineer", description="Playwright, TypeScript")
        result = score_job(job, keywords=[])
        self.assertIsNotNone(result)
        assert result is not None
        self.assertIn("自动化", result.reason)
        self.assertGreaterEqual(result.score, 5)

    def test_qa_automation_in_description_scores(self) -> None:
        job = make_job(
            title="Quality Engineer",
            description="qa automation engineer with selenium experience",
        )
        result = score_job(job, keywords=[])
        self.assertIsNotNone(result)

    # ── General QA engineering ────────────────────────────────────────────────

    def test_quality_engineer_title_detected(self) -> None:
        job = make_job(title="Quality Engineer", description="Build test plans")
        result = score_job(job, keywords=[])
        self.assertIsNotNone(result)
        assert result is not None
        self.assertIn("QA", result.reason)

    def test_non_testing_role_filtered(self) -> None:
        job = make_job(title="Backend Software Engineer", description="Build REST APIs in Python")
        self.assertIsNone(score_job(job, keywords=[]))

    # ── Remote signals ────────────────────────────────────────────────────────

    def test_remote_board_adds_score(self) -> None:
        job_remote = make_job(title="SDET", is_remote_board=True)
        job_onsite = make_job(title="SDET", is_remote_board=False)
        r_remote = score_job(job_remote, keywords=[])
        r_onsite = score_job(job_onsite, keywords=[])
        assert r_remote is not None and r_onsite is not None
        self.assertGreater(r_remote.score, r_onsite.score)

    def test_remote_in_description_adds_score(self) -> None:
        job = make_job(
            title="QA Engineer",
            description="Fully remote position, work from home",
            is_remote_board=False,
        )
        result = score_job(job, keywords=[])
        self.assertIsNotNone(result)
        assert result is not None
        self.assertIn("远程", result.reason)

    # ── Noise filtering ───────────────────────────────────────────────────────

    def test_manual_only_role_filtered(self) -> None:
        job = make_job(
            title="QA Tester",
            description="Manual qa only. No coding required. Onsite required.",
        )
        self.assertIsNone(score_job(job, keywords=[]))

    def test_onsite_required_filtered(self) -> None:
        job = make_job(
            title="SDET",
            description="Must be in NYC. In-person required. Onsite only.",
        )
        self.assertIsNone(score_job(job, keywords=[]))

    # ── Freshness ─────────────────────────────────────────────────────────────

    def test_old_sdet_job_filtered(self) -> None:
        old_ts = time.time() - (72 * 3600)  # 72h ago
        job = make_job(title="SDET", description="python, selenium", published_ts=old_ts)
        self.assertIsNone(score_job(job, keywords=[]))

    # ── Coding signals ────────────────────────────────────────────────────────

    def test_coding_signals_in_description_raise_score(self) -> None:
        job_plain = make_job(title="QA Engineer", description="Write test cases")
        job_tech = make_job(
            title="QA Engineer",
            description="Python, Selenium, pytest, CI/CD pipelines, API testing",
        )
        r_plain = score_job(job_plain, keywords=[])
        r_tech = score_job(job_tech, keywords=[])
        assert r_plain is not None and r_tech is not None
        self.assertGreater(r_tech.score, r_plain.score)

    # ── User keywords ─────────────────────────────────────────────────────────

    def test_user_keywords_raise_score(self) -> None:
        job = make_job(title="SDET", description="Looking for Playwright and AWS expert")
        result_no_kw = score_job(job, keywords=[])
        result_kw = score_job(job, keywords=["playwright", "aws"])
        assert result_no_kw is not None and result_kw is not None
        self.assertGreater(result_kw.score, result_no_kw.score)
        self.assertIn("playwright", result_kw.reason)

    # ── Salary signal ─────────────────────────────────────────────────────────

    def test_salary_listed_raises_score(self) -> None:
        job_with_salary = make_job(title="SDET", salary="$130k–$160k")
        job_without = make_job(title="SDET", salary="")
        r_with = score_job(job_with_salary, keywords=[])
        r_without = score_job(job_without, keywords=[])
        assert r_with is not None and r_without is not None
        self.assertGreater(r_with.score, r_without.score)
        self.assertIn("薪资", r_with.reason)


if __name__ == "__main__":
    unittest.main()
