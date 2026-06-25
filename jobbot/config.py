from __future__ import annotations
import os


# ── Env helpers (mirrors dealbot/config.py helpers, kept independent) ─────────

def _env_value(name: str, aliases: tuple[str, ...] = ()) -> str | None:
    for env_name in (name, *aliases):
        v = os.getenv(env_name)
        if v:
            return v
    return None


def _env_int(name: str, default: int) -> int:
    v = _env_value(name)
    if v is None:
        return default
    try:
        return int(v)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer, got {v!r}") from exc


def _env_float(name: str, default: float) -> float:
    v = _env_value(name)
    if v is None:
        return default
    try:
        return float(v)
    except ValueError as exc:
        raise ValueError(f"{name} must be a number, got {v!r}") from exc


def _env_str(name: str, default: str) -> str:
    v = _env_value(name)
    return default if v is None else v


# ── RSS feeds ─────────────────────────────────────────────────────────────────

# Remote-board flag: source hostname → True means ALL listings on this board are remote.
# Used to award a base remote-score bonus without requiring "remote" in the text.
REMOTE_BOARDS: frozenset[str] = frozenset([
    "remoteok.com",
    "weworkremotely.com",
    "himalayas.app",
    "remotive.com",
    "arbeitnow.com",
    "jobspresso.co",
    "remote.co",
])

FEEDS: list[dict] = [
    # ── RemoteOK ──────────────────────────────────────────────────────────────
    # Category feeds let us target QA/test roles specifically
    {"url": "https://remoteok.com/remote-qa-jobs.rss",       "remote_board": True},
    {"url": "https://remoteok.com/remote-test-jobs.rss",     "remote_board": True},
    {"url": "https://remoteok.com/remote-sdet-jobs.rss",     "remote_board": True},
    {"url": "https://remoteok.com/remote-dev+test-jobs.rss", "remote_board": True},

    # ── WeWorkRemotely ────────────────────────────────────────────────────────
    # Programming category covers SDET / automation roles
    {"url": "https://weworkremotely.com/categories/remote-programming-jobs.rss", "remote_board": True},
    {"url": "https://weworkremotely.com/remote-jobs.rss",    "remote_board": True},

    # ── Himalayas ─────────────────────────────────────────────────────────────
    {"url": "https://himalayas.app/jobs/rss",                "remote_board": True},

    # ── Arbeitnow ─────────────────────────────────────────────────────────────
    # Tech-focused, has a good mix of remote engineering roles
    {"url": "https://www.arbeitnow.com/feed",                "remote_board": True},
]

# ── Configurable thresholds ───────────────────────────────────────────────────

MIN_SCORE_TO_NOTIFY  = _env_int("JOB_MIN_SCORE", 7)
MAX_ALERTS_PER_RUN   = _env_int("JOB_MAX_ALERTS", 15)
# Listings older than this many hours are skipped (0 = no age limit)
MAX_JOB_AGE_HOURS    = _env_int("JOB_MAX_AGE_HOURS", 48)
# Skip listings that require more than this many years of experience (0 = no limit)
MAX_EXPERIENCE_YEARS = _env_int("JOB_MAX_EXP_YEARS", 5)
# Seconds to sleep between consecutive feed fetches
FEED_FETCH_DELAY     = _env_float("JOB_FEED_FETCH_DELAY", 1.5)

SEEN_FILE      = _env_str("JOB_SEEN_FILE",      "data/seen_jobs.json")
KEYWORDS_FILE  = _env_str("JOB_KEYWORDS_FILE",  "job_keywords.txt")
USER_AGENT     = _env_str(
    "JOB_USER_AGENT",
    "python:remote-sde-job-bot:v1.0 (by /u/amazon-deals-bot; github.com/meiyizheng/amazon-deals)",
)
