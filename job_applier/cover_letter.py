from __future__ import annotations
import re


# Tech signals used to pick the right paragraph template
_JAVA_SIGNALS = ["java", "spring", "hibernate", "jvm", "kotlin", "gradle", "maven"]
_TESTING_SIGNALS = ["sdet", "test automation", "selenium", "playwright", "pytest", "quality"]
_BACKEND_SIGNALS = ["backend", "api", "microservices", "rest", "graphql", "kafka"]

_DEFAULT_TEMPLATE = """\
Dear Hiring Manager,

I am excited to apply for the {job_title} position at {company}. \
With my background in software engineering and a strong track record of delivering \
high-quality solutions, I believe I would be a strong fit for this role.

{body_paragraph}

I am particularly drawn to {company} because of your commitment to building \
robust, scalable systems. I would welcome the opportunity to discuss how my \
experience and skills align with your needs.

Best regards,
{first_name} {last_name}
"""

_BODY_PARAGRAPHS = {
    "java": (
        "My expertise in Java development — including Spring Boot, microservices architecture, "
        "and cloud-native deployments on AWS/GCP — allows me to design and ship production-ready "
        "services efficiently. I enjoy working across the full lifecycle from API design to CI/CD "
        "pipeline optimisation."
    ),
    "testing": (
        "My experience building end-to-end test automation frameworks, integrating quality gates "
        "into CI/CD pipelines, and collaborating with product and engineering teams to shift testing "
        "left has consistently reduced defect escape rates and accelerated release confidence."
    ),
    "backend": (
        "My background in backend engineering covers API design, distributed systems, event-driven "
        "architectures, and database optimisation. I am comfortable owning features from design "
        "through deployment and have a strong habit of writing well-tested, maintainable code."
    ),
    "default": (
        "I bring a combination of strong engineering fundamentals, a collaborative mindset, and "
        "a commitment to writing clean, well-tested code. I am quick to ramp up on new stacks and "
        "thrive in remote, async-first environments."
    ),
}


def _detect_body_key(job_title: str, description: str) -> str:
    text = f"{job_title} {description}".lower()
    if any(s in text for s in _TESTING_SIGNALS):
        return "testing"
    if any(s in text for s in _JAVA_SIGNALS):
        return "java"
    if any(s in text for s in _BACKEND_SIGNALS):
        return "backend"
    return "default"


def generate(
    profile: dict,
    job_title: str,
    company: str,
    description: str = "",
) -> str:
    """
    Generate a tailored cover letter for the given job.

    Uses the custom template from profile.yml['cover_letter']['template'] when
    present; falls back to the built-in template otherwise.
    """
    personal = profile.get("personal", {})
    first = personal.get("first_name", "")
    last = personal.get("last_name", "")

    # Body paragraph: custom or auto-detected
    cl_section = profile.get("cover_letter", {})
    custom_body = cl_section.get("body_paragraph", "")
    if custom_body:
        body = custom_body
    else:
        key = _detect_body_key(job_title, description)
        body = cl_section.get("paragraphs", {}).get(key, _BODY_PARAGRAPHS[key])

    template = cl_section.get("template", _DEFAULT_TEMPLATE)

    return template.format(
        first_name=first,
        last_name=last,
        job_title=job_title,
        company=company,
        body_paragraph=body,
    )
