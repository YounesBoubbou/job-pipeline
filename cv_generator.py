"""
cv_generator.py — Generate a job-description-tailored CV (.tex) from data/base_cv.tex.

Splits the base CV at \\begin{document}: the LaTeX preamble (packages, custom
commands, layout) is frozen and never sent to the model. Only the body
(Education/Experience/Projects/Skills) is rewritten, keyed to the job's full
description, which is re-fetched from the job URL since the pipeline only
stores a 300-character snippet.
"""

import os
import re

import requests
from bs4 import BeautifulSoup

from config import BASE_CV_PATH, GENERATED_CV_DIR

_ROOT = os.path.dirname(os.path.abspath(__file__))
BASE_CV_ABS_PATH = os.path.join(_ROOT, BASE_CV_PATH)
GENERATED_DIR_ABS = os.path.join(_ROOT, GENERATED_CV_DIR)

DOC_BEGIN = r"\begin{document}"
DOC_END = r"\end{document}"


def load_base_cv() -> str:
    if not os.path.exists(BASE_CV_ABS_PATH):
        raise FileNotFoundError(f"Base CV not found at {BASE_CV_ABS_PATH}")
    with open(BASE_CV_ABS_PATH, "r", encoding="utf-8") as f:
        return f.read()


def split_preamble_and_body(tex: str) -> tuple[str, str]:
    idx = tex.index(DOC_BEGIN)
    return tex[:idx], tex[idx:]


def fetch_full_description(url: str, fallback: str = "") -> str:
    """Re-fetch the job page for its full description (stored snippet is truncated to 300 chars)."""
    try:
        resp = requests.get(
            url,
            timeout=10,
            headers={"User-Agent": "Mozilla/5.0 (compatible; job-pipeline-cv-bot)"},
        )
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style", "nav", "header", "footer"]):
            tag.decompose()
        text = re.sub(r"\s+", " ", soup.get_text(separator=" ", strip=True)).strip()
        return text[:6000] if text else fallback
    except Exception:
        return fallback


def _strip_code_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines)
    return text.strip()


def generate_tailored_cv(job: dict) -> str:
    """Return the full tailored .tex source (frozen preamble + rewritten body)."""
    from anthropic import Anthropic

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is not set")

    tex = load_base_cv()
    preamble, body = split_preamble_and_body(tex)
    jd_text = fetch_full_description(job.get("url", ""), job.get("description_snippet", ""))

    prompt = f"""You are tailoring a candidate's LaTeX CV body for a specific job application.

JOB TITLE: {job.get('title', '')}
COMPANY: {job.get('company', '')}
JOB DESCRIPTION:
{jd_text}

CURRENT CV BODY (LaTeX, from \\begin{{document}} to \\end{{document}}):
{body}

Instructions:
- Rewrite ONLY this body so it emphasizes the experience, skills, and projects most relevant to this job description.
- You MAY reorder bullet points within a section, reorder Skills categories/items, and reword bullets for emphasis.
- You MAY trim less-relevant "Research & Projects" entries if there are more than fit well, but do not remove Education or Experience entries.
- You MUST NOT invent technologies, employers, dates, degrees, or experience not present in the original. Everything must remain factually true to the original CV.
- You MUST NOT change LaTeX commands, environment names, or document structure (no new packages, no new commands) — only edit text content inside existing environments.
- Preserve exact section order: Education, Experience, Research & Projects, Skills.
- Output ONLY the raw LaTeX body, starting with "\\begin{{document}}" and ending with "\\end{{document}}". No markdown code fences, no explanation."""

    client = Anthropic(api_key=api_key)
    response = client.messages.create(
        model="claude-opus-4-8",
        max_tokens=8000,
        thinking={"type": "adaptive"},
        messages=[{"role": "user", "content": prompt}],
    )

    tailored_body = _strip_code_fences(
        "".join(block.text for block in response.content if block.type == "text")
    )

    if DOC_BEGIN not in tailored_body or DOC_END not in tailored_body:
        raise RuntimeError("Model output did not contain a valid LaTeX document body")

    return preamble + tailored_body


def _slugify(value: str) -> str:
    value = re.sub(r"[^\w\-]+", "_", value.strip())
    return re.sub(r"_+", "_", value).strip("_")[:80]


def save_generated_cv(job: dict, tex: str) -> str:
    os.makedirs(GENERATED_DIR_ABS, exist_ok=True)
    filename = f"{_slugify(job.get('company', 'company'))}-{_slugify(job.get('title', 'role'))}.tex"
    with open(os.path.join(GENERATED_DIR_ABS, filename), "w", encoding="utf-8") as f:
        f.write(tex)
    return filename
