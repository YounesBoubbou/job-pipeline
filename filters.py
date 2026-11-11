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

# Asking for 3 or more years of experience: "3+ years", "3-5 years of experience",
# "at least three years", "minimum of 4 yrs", "5 years' relevant experience".
# A range counts by its lower end, so "2-3 years", "2 - 3 years" and "2 to 3 years" are kept.
# A bare number needs "experience" close after it, or "at least"/"minimum" before it,
# so "building software for 20 years" and "a 3-year contract" don't count.
_NUM = (r"(?:[3-9]|[1-9]\d|three|four|five|six|seven|eight|nine|ten|eleven|twelve"
        r"|fifteen|twenty)")
# Any number, for the top end of a range: "3-5", "three to five"
_ANY_NUM = (r"(?:\d+|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve"
            r"|fifteen|twenty)")
# "three (3) years": the number repeated in brackets
_PAREN = r"(?:\s*\(\d+\))?"
# "years", "yrs", "years'", "years’" (straight or curly apostrophe)
_YRS = r"(?:years?|yrs?)\b['’]?"
# The number is not the top end of a range ("2-3", "2 - 3", "2 to 3", "2 or 3",
# "between 1 and 3"), not the decimal part of "1.5", and not a ceiling ("less than 3",
# "under 3", "up to 3", "max 3", "maximum of 3", "no more than 3", "at most 3")
_NOT_RANGE_END = (r"(?<![\d\-–.])(?<![\-–]\s)(?<![\-–]\s\s)(?<!to\s)(?<!or\s)"
                  r"(?<!between\s\d\sand\s)(?<!between\s\d\.\d\sand\s)"
                  r"(?<!between\sone\sand\s)(?<!between\stwo\sand\s)"
                  r"(?<!less than\s)(?<!under\s)(?<!max\s)(?<!max\.\s)(?<!maximum\s)"
                  r"(?<!maximum of\s)(?<!no more than\s)(?<!not more than\s)(?<!at most\s)\b")
# "3-5", "3 to 5" ("and" only counts after "between", so "MBO 4 and 2 years" is no range)
_RANGE = rf"\s*(?:[\-–]|to)\s*{_ANY_NUM}"
# Not the length of a contract: "a 3-5 year contract", "3-5 year (fixed-term) contract",
# at most one word in between and not "of"/"experience", so "3-5 years of contract
# experience" and "3-5 years experience, contract: permanent" still count
_NOT_CONTRACT = (r"(?!['’]?[\s\-]+(?:(?!of\b|experience\b)\(?[a-z\-]+\)?\s+)?"
                 r"contract\b(?!\s+experience))")
_YEARS_REQUIRED = re.compile(
    # "3+ years", "5 plus years", "3 or more years": always a minimum
    rf"{_NOT_RANGE_END}{_NUM}{_PAREN}\s*(?:\+|plus|or\s+more)\s*{_YRS}"
    # "3-5 years", "5–7 yrs", "three to five years": a range of years is a requirement,
    # unless it is the length of a contract
    rf"|{_NOT_RANGE_END}{_NUM}{_RANGE}[\s\-]*{_YRS}{_NOT_CONTRACT}"
    # "between 3 and 5 years", "between three and five years"
    rf"|\bbetween\s+{_NUM}{_PAREN}\s+and\s+{_ANY_NUM}[\s\-]*{_YRS}{_NOT_CONTRACT}"
    # "3 years of experience", "three (3) years experience", "4 yrs' hands-on experience"
    rf"|{_NOT_RANGE_END}{_NUM}{_PAREN}[\s\-]*{_YRS}\s+(?:of\s+)?(?:\S+\s+){{0,2}}?experience"
    # "at least 3 years", "minimum of three (3) years", "min. 4 yrs"
    rf"|\b(?:at\s+least|minimum(?:\s+of)?|min\.?)\s+{_NUM}{_PAREN}(?:{_RANGE})?\s*(?:\+\s*)?{_YRS}"
)

# Detect if keyword(s) appear in the title
def passes_include(title: str) -> bool:
    """At least one include keyword must appear in the title."""
    haystack = _normalise(title)
    return any(_contains_word(haystack, kw.lower()) for kw in KEYWORDS_INCLUDE)

# Filter out the jobs that contain exclude keywords
def passes_exclude(title: str, description: str = "") -> bool:
    """Returns True if the title has no seniority word and no 3+ years are asked for."""
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
    Passes if the location names an NL place (whole word), or only says "Remote" —
    but not "Remote - Indonesia", which can't get you a Dutch visa. A bare "Hybrid"
    fails: it means an office somewhere, and we don't know where.
    """
    if not location:
        return False   # no location means we can't tell it's in the NL
    if names_nl_place(location):
        return True
    words = set(re.findall(r"[a-z]+", location.lower()))
    return bool(words) and words <= {"remote", "job"}

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
        passes_include(title)
        and passes_exclude(title, description)
        and passes_location(location)
        and passes_language(title, description)
    )
