from __future__ import annotations
import time
import unittest

from jobbot.filtering import (
    extract_employment_type,
    extract_min_years_experience,
    score_job,
)
from jobbot.models import Job


def make_job(title: str = "Java Developer", description: str = "", is_remote_board: bool = True) -> Job:
    return Job(
        id="test-exp",
        title=title,
        company="Acme",
        link="https://example.com/job",
        source="remoteok.com",
        description=description,
        is_remote_board=is_remote_board,
    )


# ── extract_min_years_experience ──────────────────────────────────────────────

class ExtractExpTests(unittest.TestCase):
    def test_range_lower_bound(self) -> None:
        self.assertEqual(extract_min_years_experience("3-5 years of experience required"), 3)

    def test_range_with_dash(self) -> None:
        self.assertEqual(extract_min_years_experience("Requires 2–4 years experience"), 2)

    def test_plus_years(self) -> None:
        self.assertEqual(extract_min_years_experience("5+ years experience"), 5)

    def test_minimum_keyword(self) -> None:
        self.assertEqual(extract_min_years_experience("Minimum 7 years of experience"), 7)

    def test_at_least_keyword(self) -> None:
        self.assertEqual(extract_min_years_experience("at least 3 years exp"), 3)

    def test_plain_years(self) -> None:
        self.assertEqual(extract_min_years_experience("Requires 4 years experience"), 4)

    def test_no_mention_returns_zero(self) -> None:
        self.assertEqual(extract_min_years_experience("build awesome software"), 0)

    def test_ten_plus_years(self) -> None:
        self.assertEqual(extract_min_years_experience("10+ years of Java experience"), 10)


# ── extract_employment_type ───────────────────────────────────────────────────

class ExtractEmploymentTypeTests(unittest.TestCase):
    def test_full_time_detected(self) -> None:
        result = extract_employment_type("This is a full-time permanent role")
        self.assertIn("Full-time", result)

    def test_contract_detected(self) -> None:
        result = extract_employment_type("6-month contract position, W2 contract")
        self.assertIn("Contract", result)

    def test_part_time_detected(self) -> None:
        result = extract_employment_type("Part-time role, 20 hours per week")
        self.assertIn("Part-time", result)

    def test_multiple_types(self) -> None:
        result = extract_employment_type("Full-time or contract engagement")
        self.assertIn("Full-time", result)
        self.assertIn("Contract", result)

    def test_no_type_returns_empty(self) -> None:
        self.assertEqual(extract_employment_type("great java developer role"), "")

    def test_contractor_keyword(self) -> None:
        result = extract_employment_type("Looking for a contractor or 1099 worker")
        self.assertIn("Contract", result)


# ── score_job with experience filter ─────────────────────────────────────────

class ExpFilterInScoreTests(unittest.TestCase):
    def test_job_with_acceptable_exp_passes(self) -> None:
        job = make_job(description="Requires 3-5 years of Java experience. Remote position.")
        result = score_job(job, keywords=[])
        self.assertIsNotNone(result)

    def test_job_requiring_too_much_exp_filtered(self) -> None:
        job = make_job(description="Minimum 8 years of Java experience required. Remote position.")
        result = score_job(job, keywords=[])
        self.assertIsNone(result)

    def test_job_with_no_exp_mentioned_passes(self) -> None:
        job = make_job(description="Build microservices with Spring Boot and AWS.")
        result = score_job(job, keywords=[])
        self.assertIsNotNone(result)

    def test_job_at_boundary_passes(self) -> None:
        # Exactly 5 years should pass (≤5)
        job = make_job(description="5 years of experience required. Java, Spring Boot.")
        result = score_job(job, keywords=[])
        self.assertIsNotNone(result)

    def test_job_one_over_boundary_filtered(self) -> None:
        job = make_job(description="6+ years of experience required. Remote Java developer.")
        result = score_job(job, keywords=[])
        self.assertIsNone(result)

    def test_employment_type_populated_on_result(self) -> None:
        job = make_job(description="Full-time contract position. Java, AWS.")
        result = score_job(job, keywords=[])
        self.assertIsNotNone(result)
        assert result is not None
        self.assertIn("Full-time", result.employment_type)
        self.assertIn("Contract", result.employment_type)

    def test_min_years_populated_on_result(self) -> None:
        job = make_job(description="3-5 years of experience. Spring Boot, Kubernetes.")
        result = score_job(job, keywords=[])
        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result.min_years_exp, 3)


# ── cover letter generation ───────────────────────────────────────────────────

class CoverLetterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.profile = {
            "personal": {
                "first_name": "Jane",
                "last_name": "Doe",
                "email": "jane@example.com",
            },
            "resume": {"path": "resume.pdf"},
            "cover_letter": {},
        }

    def test_cover_letter_contains_name(self) -> None:
        from job_applier.cover_letter import generate
        letter = generate(self.profile, "Java Developer", "Acme Corp")
        self.assertIn("Jane", letter)
        self.assertIn("Doe", letter)

    def test_cover_letter_contains_company(self) -> None:
        from job_applier.cover_letter import generate
        letter = generate(self.profile, "Backend Engineer", "GlobalTech")
        self.assertIn("GlobalTech", letter)

    def test_java_role_uses_java_paragraph(self) -> None:
        from job_applier.cover_letter import generate
        letter = generate(self.profile, "Java Developer", "Acme", "Spring Boot microservices")
        self.assertIn("Java", letter)

    def test_testing_role_uses_testing_paragraph(self) -> None:
        from job_applier.cover_letter import generate
        letter = generate(self.profile, "SDET", "Acme", "selenium playwright test automation")
        self.assertIn("test automation", letter.lower())


# ── tracker ───────────────────────────────────────────────────────────────────

class TrackerTests(unittest.TestCase):
    def setUp(self) -> None:
        import tempfile, os
        self.tmpdir = tempfile.mkdtemp()
        self.path = os.path.join(self.tmpdir, "apps.json")

    def tearDown(self) -> None:
        import shutil
        shutil.rmtree(self.tmpdir)

    def test_not_applied_initially(self) -> None:
        from job_applier.tracker import already_applied
        self.assertFalse(already_applied(self.path, "https://example.com/job/1"))

    def test_record_and_check(self) -> None:
        from job_applier.tracker import already_applied, record_application
        url = "https://jobs.lever.co/acme/abc123"
        record_application(self.path, url, "Java Dev", "Acme", "lever_api")
        self.assertTrue(already_applied(self.path, url))

    def test_different_url_not_applied(self) -> None:
        from job_applier.tracker import already_applied, record_application
        record_application(self.path, "https://example.com/job/1", "Dev", "Co", "browser")
        self.assertFalse(already_applied(self.path, "https://example.com/job/2"))

    def test_list_returns_all_records(self) -> None:
        from job_applier.tracker import record_application, list_applications
        for i in range(3):
            record_application(self.path, f"https://example.com/{i}", f"Job {i}", "Co", "browser")
        self.assertEqual(len(list_applications(self.path)), 3)


if __name__ == "__main__":
    unittest.main()
