"""
cover_letter_generator.py — Generate a job-description-tailored cover letter (plain text).

Reuses cv_generator's base-CV loading and full-JD fetching (the pipeline only
stores a 300-character description snippet, so the full JD is re-fetched from
the job URL). Output is plain text, not LaTeX — there's no cover-letter
template to preserve, so a formatted, ready-to-paste letter is simplest.
"""

import os
import re

from config import GENERATED_CV_DIR
from cv_generator import fetch_full_description, load_base_cv, split_preamble_and_body

_ROOT = os.path.dirname(os.path.abspath(__file__))
COVER_LETTER_DIR_ABS = os.path.join(_ROOT, GENERATED_CV_DIR, "cover_letters")


def generate_cover_letter(job: dict) -> str:
    """Return a tailored plain-text cover letter for the given job."""
    from anthropic import Anthropic

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is not set")

    # Reuse the CV body as the candidate's factual background — the model
    # must not invent experience beyond what's already on the CV.
    _, cv_body = split_preamble_and_body(load_base_cv())
    jd_text = fetch_full_description(job.get("url", ""), job.get("description_snippet", ""))

    prompt = f"""You are writing a cover letter for a candidate applying to a specific job.

JOB TITLE: {job.get('title', '')}
COMPANY: {job.get('company', '')}
JOB DESCRIPTION:
{jd_text}

CANDIDATE'S CV (LaTeX source — use only the factual content: education, experience, projects, skills):
{cv_body}

Instructions:
- Write a concise, professional cover letter (roughly 250-400 words) tailored to this specific job and company.
- Open with why the candidate is a strong fit for this specific role, not a generic opener.
- Reference 2-3 concrete pieces of experience/projects from the CV that map directly to the job description's requirements.
- You MUST NOT invent employers, technologies, dates, or experience not present in the CV.
- Close with a brief, confident call to action.
- Output ONLY the plain-text letter body (no LaTeX, no markdown, no subject line, no placeholder brackets like [Company Address]). Do not include a salutation address block or date header — start directly with "Dear Hiring Manager," (or the company name if natural) and end with a sign-off and the candidate's name."""

    client = Anthropic(api_key=api_key)
    response = client.messages.create(
        model="claude-opus-4-8",
        max_tokens=2000,
        thinking={"type": "adaptive"},
        messages=[{"role": "user", "content": prompt}],
    )

    letter = "".join(block.text for block in response.content if block.type == "text").strip()
    if not letter:
        raise RuntimeError("Model returned an empty cover letter")
    return letter


def _slugify(value: str) -> str:
    value = re.sub(r"[^\w\-]+", "_", value.strip())
    return re.sub(r"_+", "_", value).strip("_")[:80]


def save_cover_letter(job: dict, letter: str) -> str:
    os.makedirs(COVER_LETTER_DIR_ABS, exist_ok=True)
    filename = f"{_slugify(job.get('company', 'company'))}-{_slugify(job.get('title', 'role'))}.txt"
    with open(os.path.join(COVER_LETTER_DIR_ABS, filename), "w", encoding="utf-8") as f:
        f.write(letter)
    return filename
