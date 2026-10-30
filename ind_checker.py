"""
ind_checker.py — Cross-reference companies against the IND public sponsor register.

The register is scraped from the IND public web page on first run and cached
locally in data/ind_sponsors.csv, which is redownloaded once it is older than
REGISTER_MAX_AGE_DAYS. Delete that file to force a refresh.

Source: https://ind.nl/en/public-register-recognised-sponsors/public-register-work
"""

import os
import time
import requests
import pandas as pd
from bs4 import BeautifulSoup
from config import IND_REGISTER_PATH

IND_REGISTER_WEB_URL = (
    "https://ind.nl/en/public-register-recognised-sponsors/public-register-work"
)

# The register changes by a few hundred names a month; redownload once the cache is older.
REGISTER_MAX_AGE_DAYS = 30


def _download_register():
    """Scrape the IND sponsor table from their public web page and cache as CSV."""
    print("  Downloading IND sponsor register (web page)...")
    headers = {"User-Agent": "Mozilla/5.0 (compatible; job-pipeline/1.0)"}
    try:
        r = requests.get(IND_REGISTER_WEB_URL, headers=headers, timeout=30)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")

        # Company names are in <th scope="row"> elements (KvK numbers are in <td>).
        names = [
            th.get_text(strip=True).lower()
            for th in soup.select("table tr th[scope='row']")
            if th.get_text(strip=True)
        ]

        if not names:
            print("  Warning: IND register table was empty — sponsor check will be skipped.")
            return []

        os.makedirs(os.path.dirname(IND_REGISTER_PATH), exist_ok=True)
        pd.Series(names).drop_duplicates().to_csv(
            IND_REGISTER_PATH, index=False, header=["name"]
        )
        print(f"  IND register cached ({len(names)} sponsors).")
        return names

    except Exception as e:
        print(f"  Warning: could not download IND register — {e}")
        return []


# Trailing tokens stripped by normalise_name(). End-of-name only, whole tokens only.
_STRIP_SUFFIXES = {
    "b.v.", "b.v", "bv", "n.v.", "nv", "i.o.", "v.o.f.", "vof", "u.a.", "c.v.",
    "limited", "ltd", "ltd.", "gmbh", "inc.", "llp", "s.a.", "se",
    "holding", "holdings", "netherlands", "nederland",
}


def normalise_name(raw: str) -> str:
    """
    Reduce a company name to a comparable stem.
    e.g. 'adyen netherlands b.v. i.o.' -> 'adyen', 'booking.com b.v.' -> 'booking.com'
    """
    tokens = raw.lower().strip().replace('"', "").split()
    while len(tokens) > 1 and tokens[-1] in _STRIP_SUFFIXES:
        tokens.pop()
    return " ".join(tokens)


def _cache_is_stale() -> bool:
    if not os.path.exists(IND_REGISTER_PATH):
        return True
    return time.time() - os.path.getmtime(IND_REGISTER_PATH) > REGISTER_MAX_AGE_DAYS * 86400


def load_sponsors() -> set:
    """Return a set of normalised sponsor company names (see normalise_name)."""
    names = _download_register() if _cache_is_stale() else []
    # A failed download falls back to the old cache rather than disabling the check.
    if not names and os.path.exists(IND_REGISTER_PATH):
        names = pd.read_csv(IND_REGISTER_PATH)["name"].dropna().tolist()
    return {normalise_name(n) for n in names}


# Load once at import time
_SPONSORS = None


def is_ind_sponsor(company_name: str) -> str:
    """
    Returns 'Yes', 'No', or 'Unknown' for a company name.
    Exact match on normalised names — e.g. 'Booking.com' matches 'booking.com b.v.',
    but 'Gradyent' does not match 'adyen n.v.'.
    """
    global _SPONSORS
    if _SPONSORS is None:
        _SPONSORS = load_sponsors()
    if not _SPONSORS:
        return "Unknown"
    return "Yes" if normalise_name(company_name) in _SPONSORS else "No"


def job_sponsor_status(job: dict) -> str:
    """Target-list jobs carry their registered name; 'Jump Trading' alone wouldn't match."""
    name = job.get("ind_registered_name") or job.get("company", "")
    return is_ind_sponsor(name) if name else "Unknown"
