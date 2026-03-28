"""
filters.py — Keyword and location filtering for job postings.
"""

from config import KEYWORDS_INCLUDE, KEYWORDS_EXCLUDE, LOCATIONS


def _normalise(text: str) -> str:
    return text.lower().replace("-", " ").replace("_", " ")


def passes_include(title: str, description: str = "") -> bool:
    """At least one include keyword must appear in title or description."""
    haystack = _normalise(f"{title} {description}")
    return any(kw.lower() in haystack for kw in KEYWORDS_INCLUDE)


def passes_exclude(title: str, description: str = "") -> bool:
    """Returns True if NO exclude keyword is found (i.e. job is safe to keep)."""
    haystack = _normalise(f"{title} {description}")
    return not any(kw.lower() in haystack for kw in KEYWORDS_EXCLUDE)


def passes_location(location: str) -> bool:
    """Location string must contain at least one of the allowed locations."""
    if not location:
        return True   # if location is missing, don't filter it out
    loc = location.lower()
    return any(allowed.lower() in loc for allowed in LOCATIONS)


def passes_all(title: str, location: str = "", description: str = "") -> bool:
    return (
        passes_include(title, description)
        and passes_exclude(title, description)
        and passes_location(location)
    )
