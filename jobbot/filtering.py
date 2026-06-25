from __future__ import annotations
import re
import time
from .config import MAX_JOB_AGE_HOURS
from .models import Job

# ── Job-role term lists ───────────────────────────────────────────────────────

# Strong: specifically an SDE-in-Test / SDET title
SDET_TITLE_TERMS: list[str] = [
    "sdet",
    "sde-t",
    "sde in test",
    "sde, test",
    "software development engineer in test",
    "software engineer in test",
    "software engineer, test",
    "software engineer (test)",
]

# Medium: automation-focused engineering roles
AUTOMATION_TERMS: list[str] = [
    "test automation engineer",
    "automation engineer",
    "qa automation engineer",
    "automation in test",
    "quality automation",
    "engineer in test",
    "software test engineer",
    "platform engineer in test",
]

# Weaker: general QA engineering (may include manual roles)
QA_ENGINEERING_TERMS: list[str] = [
    "quality engineer",
    "qa engineer",
    "software quality",
    "quality assurance engineer",
    "test engineer",
    "testing engineer",
]

# SDE / developer roles (the titles the user explicitly wants to track)
SDE_TITLE_TERMS: list[str] = [
    # User-requested titles
    "java developer",
    "java application developer",
    "java software developer",
    "java software engineer",
    "backend engineer",
    "backend software engineer",
    "backend developer",
    "application developer",
    "enterprise application developer",
    "software developer",
    "integration engineer",
    "api developer",
    "business systems developer",
    # Common adjacent titles worth catching
    "full stack developer",
    "full-stack developer",
    "full stack engineer",
    "full-stack engineer",
    "software engineer",          # broad, only fires when relevance gate passes
    "senior software engineer",
    "staff software engineer",
    "principal software engineer",
]

# Remote signals for boards that mix remote/on-site listings
REMOTE_TERMS: list[str] = [
    "remote",
    "work from home",
    "wfh",
    "fully remote",
    "100% remote",
    "anywhere",
    "distributed team",
]

# Noise: roles that are clearly manual-only, non-engineering, or on-site only
NOISE_TERMS: list[str] = [
    "manual qa only",
    "no coding required",
    "non-technical",
    "onsite required",
    "on-site only",
    "in-person required",
    "in-office required",
    "on site only",
]

# Coding / engineering signal in description
CODING_SIGNALS: list[str] = [
    "python", "java", "javascript", "typescript", "go ", "golang", "c#", "c++",
    "selenium", "playwright", "cypress", "appium",
    "pytest", "junit", "testng", "jest",
    "spring", "spring boot", "hibernate", "jpa",
    "microservices", "rest api", "graphql", "grpc",
    "kafka", "rabbitmq", "sqs",
    "mysql", "postgresql", "mongodb", "redis",
    "ci/cd", "jenkins", "github actions", "gitlab ci",
    "api testing", "performance testing", "load testing", "k6", "jmeter",
    "docker", "kubernetes", "aws", "azure", "gcp",
    "test framework", "automation framework",
    "code review", "pull request", "version control", "git",
]


# ── Helpers ───────────────────────────────────────────────────────────────────

def is_fresh(job: Job) -> bool:
    if MAX_JOB_AGE_HOURS == 0 or job.published_ts == 0:
        return True
    age_hours = (time.time() - job.published_ts) / 3600
    return age_hours <= MAX_JOB_AGE_HOURS


# ── Main scoring function ─────────────────────────────────────────────────────

def score_job(job: Job, keywords: list[str]) -> Job | None:
    """
    Score a job listing. Returns None when the job should be dropped:
    - Too old
    - Clearly a manual/non-engineering role
    - Not an SDE, SDET, or QA engineering role

    Two role families are tracked:
      Testing: SDET / automation engineer / QA engineer
      Development: backend engineer / Java developer / software developer / etc.
    """
    if not is_fresh(job):
        return None

    title_lower = job.title.lower()
    full_text = f"{job.title} {job.description}".lower()
    score = 0
    reasons: list[str] = []

    # ── Hard drops ────────────────────────────────────────────────────────────
    if any(term in full_text for term in NOISE_TERMS):
        return None

    # ══ Testing track ═════════════════════════════════════════════════════════

    # SDET / SDE-in-Test title (highest value testing signal)
    sdet_matches = [t for t in SDET_TITLE_TERMS if t in title_lower]
    if sdet_matches:
        score += 8
        reasons.append(f"SDET职位: {sdet_matches[0]}")

    # Automation engineering title
    auto_matches = [t for t in AUTOMATION_TERMS if t in full_text]
    if auto_matches:
        bonus = 5 if not sdet_matches else 2
        score += bonus
        reasons.append(f"自动化测试: {auto_matches[0]}")

    # General QA engineering (only when no stronger testing match)
    qa_matches = [t for t in QA_ENGINEERING_TERMS if t in title_lower]
    if qa_matches and not sdet_matches and not auto_matches:
        score += 3
        reasons.append(f"QA工程: {qa_matches[0]}")

    # ══ Development track ═════════════════════════════════════════════════════

    sde_matches = [t for t in SDE_TITLE_TERMS if t in title_lower]
    if sde_matches:
        # Only score SDE title when no testing role already matched; avoids
        # double-counting titles like "Software Engineer in Test"
        if not sdet_matches and not auto_matches and not qa_matches:
            score += 6
            reasons.append(f"开发职位: {sde_matches[0]}")

    # ══ Shared signals ════════════════════════════════════════════════════════

    # Coding signals in description
    coding_hits = [s for s in CODING_SIGNALS if s in full_text]
    if coding_hits:
        score += min(4, len(coding_hits))
        reasons.append("技术信号: " + ", ".join(coding_hits[:4]))

    # Remote signal
    if job.is_remote_board:
        score += 2
        reasons.append("Remote职位")
    elif any(term in full_text for term in REMOTE_TERMS):
        score += 3
        reasons.append("支持远程")

    # User-defined tech-stack keywords
    kw_matches = [k for k in keywords if k and k in full_text]
    if kw_matches:
        score += min(4, len(kw_matches) * 2)
        reasons.append("关键词: " + ", ".join(kw_matches[:4]))

    # Salary listed (transparent employer signal)
    if job.salary:
        score += 1
        reasons.append(f"薪资: {job.salary}")

    # ── Relevance gate ────────────────────────────────────────────────────────
    # Must be a testing role OR a development role to pass
    is_test_role = bool(sdet_matches or auto_matches or qa_matches)
    is_sde_role = bool(sde_matches)
    if not is_test_role and not is_sde_role:
        return None

    return Job(
        id=job.id,
        title=job.title,
        company=job.company,
        link=job.link,
        source=job.source,
        location=job.location,
        description=job.description,
        published=job.published,
        published_ts=job.published_ts,
        score=score,
        reason="；".join(reasons) if reasons else "可能匹配",
        salary=job.salary,
        is_remote_board=job.is_remote_board,
    )
