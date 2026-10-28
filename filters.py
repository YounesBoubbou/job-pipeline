"""
filters.py — Keyword and location filtering for job postings.
"""

import re

from config import KEYWORDS_INCLUDE, KEYWORDS_EXCLUDE, LOCATIONS

# Normalise the text first
def _normalise(text: str) -> str:
    return text.lower().replace("-", " ").replace("_", " ")

# Whole-word match, so "lead" doesn't hit "leading" and "nl" doesn't hit "Finland"
def _contains_word(haystack: str, word: str) -> bool:
    return re.search(rf"\b{re.escape(word.strip())}\b", haystack) is not None

# "5+ years", "5-7 years", "at least 6 years" of experience — 5 or more, not "3-5 years".
# Needs "experience" after it, so "building software for 20 years" doesn't count.
_YEARS_REQUIRED = re.compile(
    r"(?<![\d\-–])\b([5-9]|[1-9]\d)\s*(\+|[\-–]\s*\d+)?\s*years?'?\s+(of\s+)?(\w+\s+)?experience"
)

# Detect if keyword(s) appear in title or description
def passes_include(title: str, description: str = "") -> bool:
    """At least one include keyword must appear in title or description."""
    haystack = _normalise(f"{title} {description}")
    return any(kw.lower() in haystack for kw in KEYWORDS_INCLUDE)

# Filter out the jobs that contain exclude keywords
def passes_exclude(title: str, description: str = "") -> bool:
    """Returns True if NO exclude keyword is found (i.e. job is safe to keep)."""
    text = f"{title} {description}".lower()
    if _YEARS_REQUIRED.search(text):
        return False
    haystack = _normalise(text)
    return not any(_contains_word(haystack, kw.lower()) for kw in KEYWORDS_EXCLUDE)

# Work modes in LOCATIONS — they say how, not where
_WORK_MODES = {"remote", "hybrid"}

# Filter out the jobs based on location
def passes_location(location: str) -> bool:
    """
    Passes if the location names an NL place (whole word), or is only a work mode
    like "Remote" — but not "Remote - Indonesia", which can't get you a Dutch visa.
    """
    if not location:
        return False   # no location means we can't tell it's in the NL
    loc = location.lower()
    places = [p.lower() for p in LOCATIONS if p.lower() not in _WORK_MODES]
    if any(_contains_word(loc, p) for p in places):
        return True
    words = set(re.findall(r"[a-z]+", loc))
    return bool(words) and words <= _WORK_MODES | {"job"}

# Return the jobs that pass all of the filtering steps
def passes_all(title: str, location: str = "", description: str = "") -> bool:
    return (
        passes_include(title, description)
        and passes_exclude(title, description)
        and passes_location(location)
    )
