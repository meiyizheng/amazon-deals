#!/usr/bin/env python3
"""
Job Application Helper
======================
Usage:
  python apply_main.py apply  --url "https://jobs.lever.co/company/123..."
  python apply_main.py apply  --url "https://boards.greenhouse.io/company/jobs/123"
  python apply_main.py apply  --url "https://any-other-job-url.com"  --title "Backend Engineer" --company "Acme"
  python apply_main.py list
  python apply_main.py cover  --url URL --title "Java Developer" --company "Acme"

The tool:
  1. Detects the job platform (Lever / Greenhouse / other)
  2. Generates a tailored cover letter from your profile
  3. Submits the application via Lever or Greenhouse API, or opens your browser
  4. Records every application in data/applications.json
"""
from __future__ import annotations
import argparse
import sys

from job_applier import config as cfg
from job_applier import cover_letter as cl
from job_applier import tracker
from job_applier.platforms import lever, greenhouse, browser
from job_applier.platforms.base import ApplyResult


def cmd_apply(args: argparse.Namespace) -> None:
    url = args.url
    profile = cfg.load_profile()
    tracker_file = cfg.tracker_path()

    # Duplicate application guard
    if tracker.already_applied(tracker_file, url):
        print(f"⚠️  Already applied to this job: {url}")
        print("   Use --force to apply again.")
        if not getattr(args, "force", False):
            return

    # Resolve job title and company (from args or profile defaults)
    job_title = args.title or "this position"
    company = args.company or "your company"

    # Generate cover letter
    letter = cl.generate(profile, job_title, company, args.description or "")
    print("\n── Cover Letter Preview ─────────────────────────────────────────────")
    print(letter)
    print("────────────────────────────────────────────────────────────────────\n")

    if args.preview_only:
        print("(--preview-only: not submitting)")
        return

    # Choose platform
    if lever.is_lever_url(url):
        print(f"🔍 Detected: Lever  ({url})")
        outcome = lever.apply(url, profile, letter)
    elif greenhouse.is_greenhouse_url(url):
        print(f"🔍 Detected: Greenhouse  ({url})")
        outcome = greenhouse.apply(url, profile, letter)
    else:
        print(f"🔍 Platform unknown — opening browser ({url})")
        outcome = browser.open_in_browser(url)

    # Print result
    icon = {
        ApplyResult.SUCCESS: "✅",
        ApplyResult.BROWSER_OPENED: "🌐",
        ApplyResult.FAILED: "❌",
        ApplyResult.SKIPPED: "⏭",
    }.get(outcome.result, "❓")
    print(f"{icon} {outcome.message}")

    # Record in tracker
    status = "applied" if outcome.result in (ApplyResult.SUCCESS, ApplyResult.BROWSER_OPENED) else "failed"
    tracker.record_application(
        tracker_file,
        job_url=url,
        job_title=job_title,
        company=company,
        method=outcome.method,
        status=status,
    )
    print(f"📋 Recorded in {tracker_file}")


def cmd_list(args: argparse.Namespace) -> None:
    tracker.print_summary(cfg.tracker_path())


def cmd_cover(args: argparse.Namespace) -> None:
    profile = cfg.load_profile()
    letter = cl.generate(
        profile,
        args.title or "this position",
        args.company or "your company",
        args.description or "",
    )
    print(letter)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Remote SDE Job Application Helper",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command")

    # ── apply ──────────────────────────────────────────────────────────────────
    p_apply = sub.add_parser("apply", help="Apply to a job posting")
    p_apply.add_argument("--url",          required=True, help="Job posting URL")
    p_apply.add_argument("--title",        default="",    help="Job title (optional, improves cover letter)")
    p_apply.add_argument("--company",      default="",    help="Company name (optional)")
    p_apply.add_argument("--description",  default="",    help="Job description text (optional)")
    p_apply.add_argument("--preview-only", action="store_true", help="Show cover letter but don't submit")
    p_apply.add_argument("--force",        action="store_true", help="Apply even if already tracked")

    # ── list ───────────────────────────────────────────────────────────────────
    sub.add_parser("list", help="Show all tracked applications")

    # ── cover ──────────────────────────────────────────────────────────────────
    p_cover = sub.add_parser("cover", help="Generate a cover letter (no submission)")
    p_cover.add_argument("--url",         default="",  help="Job URL (used for platform detection)")
    p_cover.add_argument("--title",       default="",  help="Job title")
    p_cover.add_argument("--company",     default="",  help="Company name")
    p_cover.add_argument("--description", default="",  help="Job description")

    args = parser.parse_args()

    if args.command == "apply":
        cmd_apply(args)
    elif args.command == "list":
        cmd_list(args)
    elif args.command == "cover":
        cmd_cover(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
