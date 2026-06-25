from __future__ import annotations
import os
import time
import requests
from .models import Job

# ── Tier definitions ──────────────────────────────────────────────────────────
# (min_score, label, Discord embed color)
_TIERS: list[tuple[int, str, int]] = [
    (12, "🔥 完美匹配", 0x00C853),   # ≥12 → bright green
    (9,  "💼 强力匹配", 0x2196F3),   # 9–11 → blue
    (7,  "🎯 可能匹配", 0x78909C),   # 7–8  → grey-blue
]

_SUMMARY_COLOR = 0x7E57C2       # purple for run-summary embed
_FOOTER_TEXT = "Remote SDE Job Bot"
_INTER_POST_DELAY = 0.8
_MAX_RETRIES = 3
_SUMMARY_THRESHOLD = 3


# ── Internal helpers ──────────────────────────────────────────────────────────

def _tier(score: int) -> tuple[str, int]:
    for threshold, label, color in _TIERS:
        if score >= threshold:
            return label, color
    return "🎯 可能匹配", 0x78909C


def _apply_command(job: Job) -> str:
    """Build a ready-to-run apply_main.py command for this job."""
    title   = job.title.replace('"', '\\"')[:80]
    company = job.company.replace('"', '\\"')[:50]
    return (
        f'python apply_main.py apply \\\n'
        f'  --url     "{job.link}" \\\n'
        f'  --title   "{title}" \\\n'
        f'  --company "{company}"'
    )


def _build_embed(job: Job) -> dict:
    tier_label, color = _tier(job.score)
    title = f"{tier_label}  {job.title}"[:256]

    fields: list[dict] = [
        {"name": "🏢 公司", "value": job.company[:100] or "Unknown", "inline": True},
    ]

    location_display = job.location or ("🌐 Remote" if job.is_remote_board else "")
    if location_display:
        fields.append({"name": "📍 地点", "value": location_display[:100], "inline": True})

    if job.employment_type:
        fields.append({"name": "📋 类型", "value": job.employment_type[:80], "inline": True})

    if job.min_years_exp > 0:
        fields.append({"name": "🗓 经验", "value": f"≤{job.min_years_exp} 年", "inline": True})

    if job.salary:
        fields.append({"name": "💰 薪资", "value": job.salary[:100], "inline": True})

    fields.append({"name": "⭐ 评分", "value": str(job.score), "inline": True})
    fields.append({"name": "📌 来源", "value": job.source[:100], "inline": True})

    # Full-width apply command — click the code block in Discord to copy it
    cmd = _apply_command(job)
    fields.append({
        "name": "📤 投递命令（点击代码块一键复制，粘贴到终端运行）",
        "value": f"```sh\n{cmd}\n```",
        "inline": False,
    })

    return {
        "title": title,
        "url": job.link,
        "color": color,
        "description": (job.reason or "可能匹配")[:1024],
        "fields": fields,
        "footer": {"text": _FOOTER_TEXT},
    }


def _build_summary_embed(jobs: list[Job]) -> dict:
    lines: list[str] = []
    for j in jobs:
        tier_label, _ = _tier(j.score)
        short = j.title[:60].rstrip()
        company = j.company[:30] or "Unknown"
        lines.append(f"{tier_label} **[{short}]({j.link})** @ {company} (评分 {j.score})")
    return {
        "title": f"💼 本次发现 {len(jobs)} 个 Remote SDE Testing 职位",
        "description": "\n".join(lines)[:4096],
        "color": _SUMMARY_COLOR,
        "footer": {"text": _FOOTER_TEXT},
    }


def _post_with_retry(webhook: str, payload: dict) -> None:
    for attempt in range(_MAX_RETRIES):
        try:
            resp = requests.post(webhook, json=payload, timeout=20)
        except requests.RequestException as exc:
            print(f"WARN: Discord request failed (attempt {attempt + 1}): {exc}")
            if attempt < _MAX_RETRIES - 1:
                time.sleep(2 ** attempt)
            continue

        if resp.status_code == 429:
            try:
                retry_after = float(resp.json().get("retry_after", 1.0))
            except Exception:
                retry_after = 1.0
            print(f"WARN: Discord rate-limited, retrying after {retry_after:.1f}s")
            time.sleep(retry_after)
            continue

        if resp.status_code >= 300:
            print(f"WARN: Discord returned {resp.status_code}: {resp.text[:300]}")
        return


# ── Public interface ──────────────────────────────────────────────────────────

def format_job(job: Job) -> str:
    """Plain-text fallback when no webhook is configured."""
    tier_label, _ = _tier(job.score)
    parts = [
        tier_label,
        f"  {job.title[:120]}",
        f"  {job.company}" + (f" | {job.location}" if job.location else ""),
        f"  Score: {job.score}  |  {job.reason[:200]}",
    ]
    if job.employment_type:
        parts.append(f"  Type: {job.employment_type}")
    if job.salary:
        parts.append(f"  Salary: {job.salary}")
    parts.append(f"  {job.link}")
    parts.append(f"  $ {_apply_command(job).replace(chr(10), ' ').replace('  ', ' ')}")
    return "\n".join(parts)


def send_discord(jobs: list[Job]) -> None:
    webhook = os.getenv("JOB_DISCORD_WEBHOOK")
    if not webhook:
        print("JOB_DISCORD_WEBHOOK is not set. Printing job alerts instead.")
        for job in jobs:
            print(format_job(job))
            print()
        return

    if len(jobs) >= _SUMMARY_THRESHOLD:
        _post_with_retry(webhook, {"embeds": [_build_summary_embed(jobs)]})
        time.sleep(_INTER_POST_DELAY)

    for job in jobs:
        _post_with_retry(webhook, {"embeds": [_build_embed(job)]})
        time.sleep(_INTER_POST_DELAY)
