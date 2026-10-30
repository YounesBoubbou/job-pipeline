"""
filters.py — Keyword and location filtering for job postings.
"""

import html
import re

from config import KEYWORDS_INCLUDE, KEYWORDS_EXCLUDE, EXPERIENCE_EXCLUDE, LOCATIONS

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
    """Returns True if the title has no seniority word and no 5+ years are asked for."""
    text = f"{title} {description}".lower()
    if _YEARS_REQUIRED.search(text) or any(kw in text for kw in EXPERIENCE_EXCLUDE):
        return False
    haystack = _normalise(title.lower())
    return not any(_contains_word(haystack, kw.lower()) for kw in KEYWORDS_EXCLUDE)

# Work modes in LOCATIONS — they say how, not where
_WORK_MODES = {"remote", "hybrid"}

# True if the location names an NL place (whole word); work modes don't count
def names_nl_place(location: str) -> bool:
    loc = location.lower()
    places = [p.lower() for p in LOCATIONS if p.lower() not in _WORK_MODES]
    return any(_contains_word(loc, p) for p in places)

# Filter out the jobs based on location
def passes_location(location: str) -> bool:
    """
    Passes if the location names an NL place (whole word), or is only a work mode
    like "Remote" — but not "Remote - Indonesia", which can't get you a Dutch visa.
    """
    if not location:
        return False   # no location means we can't tell it's in the NL
    if names_nl_place(location):
        return True
    words = set(re.findall(r"[a-z]+", location.lower()))
    return bool(words) and words <= _WORK_MODES | {"job"}

# Common words that are unambiguous between the two languages, so not "in", "is", "we" or "of".
# The Dutch list also has job-title words, because some listings only give us a title.
_DUTCH_WORDS = {
    "de", "het", "een", "en", "van", "voor", "met", "je", "jij", "jouw", "wij", "ons", "onze",
    "naar", "bij", "zijn", "wordt", "worden", "ook", "die", "dat", "aan", "als", "om", "niet",
    "ontwikkelaar", "medewerker", "beheerder", "adviseur", "monteur", "stagiair",
    "afstudeerstage", "werkstudent", "vacature",
}
_ENGLISH_WORDS = {
    "the", "and", "to", "with", "for", "you", "your", "our", "are", "will", "this", "that",
    "from", "have",
}

# Boards send descriptions as HTML, some of it escaped; a cut-off final tag is removed too
def strip_html(text: str) -> str:
    text = re.sub(r"<[^>]*(>|$)", " ", html.unescape(text))
    return " ".join(html.unescape(text).split())

# Filter out the jobs written in Dutch; a tie (e.g. the title "Data Engineer") is kept
def passes_language(title: str, description: str = "") -> bool:
    """Returns True unless the posting has more Dutch words than English ones."""
    words = re.findall(r"[a-zà-ÿ]+", strip_html(f"{title} {description}").lower())
    dutch = sum(w in _DUTCH_WORDS for w in words)
    english = sum(w in _ENGLISH_WORDS for w in words)
    return dutch <= english

# Return the jobs that pass all of the filtering steps
def passes_all(title: str, location: str = "", description: str = "") -> bool:
    return (
        passes_include(title, description)
        and passes_exclude(title, description)
        and passes_location(location)
        and passes_language(title, description)
    )
