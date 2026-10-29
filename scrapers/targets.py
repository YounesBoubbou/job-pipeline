"""
scrapers/targets.py — Fetch openings for every company in targets.csv (ADR-0005).

Each row names a company, its ATS vendor (`source`) and its board token. Every vendor
here has a public JSON API, so no HTML is scraped. Boards that fail are reported at the
end of the run rather than skipped silently, since a failure usually means the company
moved to another ATS and the row needs updating.
"""

import csv
import os
from datetime import datetime

import requests

from filters import passes_all

TARGETS_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "targets.csv")
HEADERS = {"User-Agent": "job-pipeline (personal job search)"}
TIMEOUT = 20
TODAY = datetime.today().strftime("%Y-%m-%d")


# Each fetcher takes a token and returns (title, location, url, description) tuples.

def _greenhouse(token):
    r = requests.get(f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true",
                     headers=HEADERS, timeout=TIMEOUT)
    r.raise_for_status()
    for j in r.json()["jobs"]:
        yield j["title"], j.get("location", {}).get("name", ""), j["absolute_url"], j.get("content", "")


def _lever(token):
    r = requests.get(f"https://api.lever.co/v0/postings/{token}?mode=json",
                     headers=HEADERS, timeout=TIMEOUT)
    r.raise_for_status()
    for j in r.json():
        location = j.get("categories", {}).get("location", "")
        yield j["text"], location, j["hostedUrl"], j.get("descriptionPlain", "")


def _ashby(token):
    r = requests.get(f"https://api.ashbyhq.com/posting-api/job-board/{token}",
                     headers=HEADERS, timeout=TIMEOUT)
    r.raise_for_status()
    for j in r.json()["jobs"]:
        yield j["title"], j.get("location", ""), j["jobUrl"], j.get("descriptionPlain", "")


def _recruitee(token):
    r = requests.get(f"https://{token}.recruitee.com/api/offers/", headers=HEADERS, timeout=TIMEOUT)
    r.raise_for_status()
    for j in r.json()["offers"]:
        yield j["title"], j.get("location", ""), j["careers_url"], j.get("description", "")


def _smartrecruiters(token):
    offset = 0
    while True:
        r = requests.get(f"https://api.smartrecruiters.com/v1/companies/{token}/postings",
                         params={"limit": 100, "offset": offset}, headers=HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
        data = r.json()
        for j in data["content"]:
            loc = j.get("location", {})
            location = ", ".join(p for p in (loc.get("city"), loc.get("country")) if p)
            yield j["name"], location, f"https://jobs.smartrecruiters.com/{token}/{j['id']}", ""
        offset += 100
        if offset >= data["totalFound"]:
            break


def _workday(token):
    # Token is the public board URL, e.g. https://nvidia.wd5.myworkdayjobs.com/NVIDIAExternalCareerSite
    # The listing API lives at /wday/cxs/{tenant}/{site}/jobs and caps pages at 20.
    # It reports `total` only on the first page (later pages say 0), so read it once.
    base = token.rstrip("/")
    host, site = base.rsplit("/", 1)
    tenant = host.split("//")[1].split(".")[0]
    api = f"{host}/wday/cxs/{tenant}/{site}/jobs"
    offset, total = 0, None
    while True:
        r = requests.post(api, json={"limit": 20, "offset": offset, "searchText": "", "appliedFacets": {}},
                          headers=HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
        data = r.json()
        if total is None:
            total = data["total"]
        for j in data["jobPostings"]:
            yield j["title"], j.get("locationsText", ""), base + j["externalPath"], ""
        offset += 20
        if offset >= total or not data["jobPostings"]:
            break


FETCHERS = {
    "greenhouse":      _greenhouse,
    "lever":           _lever,
    "ashby":           _ashby,
    "recruitee":       _recruitee,
    "smartrecruiters": _smartrecruiters,
    "workday":         _workday,
}


def load_targets(path: str = TARGETS_PATH) -> list[dict]:
    # utf-8-sig: the list is edited in spreadsheet tools that prepend a BOM to the header.
    with open(path, encoding="utf-8-sig", newline="") as f:
        return [{k: (v or "").strip() for k, v in row.items()} for row in csv.DictReader(f)]


def fetch_target_jobs() -> list[dict]:
    """Fetch and filter openings for every target that has a source and token."""
    jobs, failed, skipped = [], [], []

    for t in load_targets():
        name, source, token = t["company"], t.get("source", "").lower(), t.get("token", "")
        if source not in FETCHERS or not token:
            skipped.append(name)
            continue

        try:
            postings = list(FETCHERS[source](token))
        except Exception as e:
            failed.append(f"{name} ({source}:{token}) — {e}")
            continue

        kept = 0
        for title, location, url, description in postings:
            if not passes_all(title, location, description):
                continue
            kept += 1
            jobs.append({
                "title":               title,
                "company":             name,
                "location":            location,
                "url":                 url,
                "source":              f"Target ({source})",
                "date_found":          TODAY,
                "description_snippet": description[:300],
            })
        print(f"  {name} ({source}): {len(postings)} listings, {kept} kept")

    if skipped:
        print(f"  Skipped {len(skipped)} targets with no source/token")
    if failed:
        print(f"\n  !! {len(failed)} BOARD(S) FAILED — check these rows in targets.csv:")
        for f in failed:
            print(f"     {f}")

    print(f"  Targets total (post-filter): {len(jobs)} jobs")
    return jobs
