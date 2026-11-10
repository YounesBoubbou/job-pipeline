"""
scrapers/targets.py — Fetch openings for every company in targets.csv (ADR-0005).

Each row names a company, its ATS vendor (`source`) and its board token. Every vendor
here has a public JSON API, so no HTML is scraped. Boards that fail are reported at the
end of the run rather than skipped silently, since a failure usually means the company
moved to another ATS and the row needs updating.
"""

import csv
import os
import re
from datetime import datetime

import requests

from filters import names_nl_place, passes_all, strip_html

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
        location = j.get("location", {}).get("name", "")
        # Cloudflare's locations just say "Hybrid"; the actual office is listed separately.
        if location.strip().lower() == "hybrid":
            location = "; ".join([location] + [o["name"] for o in j.get("offices", [])])
        yield j["title"], location, j["absolute_url"], j.get("content", "")


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
        # Some boards leave `description` as "-" and put all the text in `requirements`.
        description = f"{j.get('description', '')} {j.get('requirements', '')}"
        yield j["title"], j.get("location", ""), j["careers_url"], description


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
    # Downloading every listing took most of an hour across all boards (P6), so the first
    # page's facets (the board's own search filters) are used to ask for Netherlands jobs
    # only (ADR-0008). Boards whose filters can't be read are still downloaded in full.
    base = token.rstrip("/")
    host, site = base.rsplit("/", 1)
    tenant = host.split("//")[1].split(".")[0]
    api = f"{host}/wday/cxs/{tenant}/{site}/jobs"
    first = _workday_page(api, 0, {})
    nl_facets = _workday_nl_facets(first.get("facets", []))
    if nl_facets is None:
        pages = _workday_pages(api, {}, first)
    elif not nl_facets:
        return  # the board has location filters, and none of them is in the Netherlands
    else:
        pages = _workday_pages(api, nl_facets, _workday_page(api, 0, nl_facets))
    for j in pages:
        if "title" not in j or "externalPath" not in j:  # some boards pad pages with stubs
            continue
        location = j.get("locationsText", "")
        # Multi-location jobs only say "3 Locations"; the detail endpoint lists them.
        if re.fullmatch(r"\d+ Locations", location):
            location = _workday_locations(f"{host}/wday/cxs/{tenant}/{site}{j['externalPath']}") or location
        yield j["title"], location, base + j["externalPath"], ""


def _workday_page(api, offset, facets):
    r = requests.post(api, json={"limit": 20, "offset": offset, "searchText": "", "appliedFacets": facets},
                      headers=HEADERS, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()


def _workday_pages(api, facets, first):
    # Yields the postings of `first` (the page at offset 0) and of every page after it.
    # The API reports `total` only on the first page (later pages say 0), so read it once.
    total, data, offset = first["total"], first, 0
    while True:
        yield from data["jobPostings"]
        offset += 20
        if offset >= total or not data["jobPostings"]:
            break
        data = _workday_page(api, offset, facets)


def _workday_nl_facets(facets):
    """Pick the search filter that asks a Workday board for its Netherlands jobs (ADR-0008).

    The filter's name differs per board (locationCountry, Country, even "a"), but its
    Netherlands value is always called "Netherlands". Boards without a country filter only
    have `locations`, a list of offices; those in the Netherlands are picked by place name.
    Returns {} when the board has location filters but none in the Netherlands (it has no
    Dutch jobs right now), and None when it has no location filter at all.
    """
    found = list(_walk_facets(facets))
    for f in found:
        if f.get("facetParameter") != "locations":
            ids = [v["id"] for v in f.get("values", [])
                   if "id" in v and v.get("descriptor", "").strip().lower() == "netherlands"]
            if ids:
                return {f["facetParameter"]: ids}
    for f in found:
        if f.get("facetParameter") == "locations":
            ids = [v["id"] for v in f.get("values", []) if "id" in v and names_nl_place(v.get("descriptor", ""))]
            if ids:
                return {"locations": ids}
    if any(f.get("facetParameter") == "locations" or "country" in f.get("facetParameter", "").lower()
           for f in found):
        return {}
    return None


def _walk_facets(facets):
    # Some boards nest their country filter inside `locationMainGroup`; a value that has
    # its own `facetParameter` is such a nested filter.
    for f in facets:
        yield f
        yield from _walk_facets([v for v in f.get("values", []) if "facetParameter" in v])


def _workday_locations(detail_url):
    try:
        r = requests.get(detail_url, headers=HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
        info = r.json()["jobPostingInfo"]
    except Exception:
        return ""
    return "; ".join([info.get("location", "")] + info.get("additionalLocations", []))


# Workday and SmartRecruiters listings carry no description, so it takes one request per job.
# On failure these return "", which leaves only the title for the filters to judge.

def _workday_description(token, url):
    base = token.rstrip("/")
    host, site = base.rsplit("/", 1)
    tenant = host.split("//")[1].split(".")[0]
    try:
        r = requests.get(f"{host}/wday/cxs/{tenant}/{site}{url[len(base):]}", headers=HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
        return r.json()["jobPostingInfo"].get("jobDescription", "")
    except Exception:
        return ""


def _smartrecruiters_description(token, url):
    try:
        r = requests.get(f"https://api.smartrecruiters.com/v1/companies/{token}/postings/{url.rsplit('/', 1)[1]}",
                         headers=HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
        sections = r.json()["jobAd"]["sections"]
        return " ".join(s.get("text", "") for s in sections.values())
    except Exception:
        return ""


DESCRIPTION_FETCHERS = {
    "workday":         _workday_description,
    "smartrecruiters": _smartrecruiters_description,
}

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


def fetch_target_jobs() -> tuple[list[dict], list[dict], list[dict]]:
    """Fetch and filter openings for every target that has a source and token.

    Returns (jobs, boards, failed). `boards` has one entry per board that answered, with
    how many listings it returned (`fetched`) and how many passed the filters (`kept`).
    `failed` has one entry per board that raised, with the reason. A board that fails
    partway is counted as failed and none of its jobs are kept.
    """
    jobs, boards, failed, skipped = [], [], [], []
    failed_lines = []  # the same failures, worded for the console

    for t in load_targets():
        name, source, token = t["company"], t.get("source", "").lower(), t.get("token", "")
        # 'review' rows have a board that may belong to another company (ADR-0006).
        if source not in FETCHERS or not token or t.get("board_status") == "review":
            skipped.append(name)
            continue

        board_jobs = []
        try:
            postings = list(FETCHERS[source](token))
            for title, location, url, description in postings:
                if not passes_all(title, location, description):
                    continue
                # Only fetched for jobs that got this far, to keep the request count down.
                if not description and source in DESCRIPTION_FETCHERS:
                    description = DESCRIPTION_FETCHERS[source](token, url)
                    if not passes_all(title, location, description):
                        continue
                board_jobs.append({
                    "title":               title,
                    "company":             name,
                    "ind_registered_name": t.get("ind_registered_name", ""),
                    "location":            location,
                    "url":                 url,
                    "source":              f"Target ({source})",
                    "date_found":          TODAY,
                    "description_snippet": strip_html(description)[:300],
                })
        except Exception as e:
            reason = f"{type(e).__name__}: {e}"
            failed.append({"name": name, "source": f"target:{source}", "reason": reason})
            failed_lines.append(f"{name} ({source}:{token}) — {reason}")
            continue

        jobs.extend(board_jobs)
        boards.append({"name": name, "source": f"target:{source}",
                       "fetched": len(postings), "kept": len(board_jobs)})
        print(f"  {name} ({source}): {len(postings)} listings, {len(board_jobs)} kept")

    if skipped:
        print(f"  Skipped {len(skipped)} targets with no source/token")
    if failed:
        print(f"\n  !! {len(failed)} BOARD(S) FAILED — check these rows in targets.csv:")
        for line in failed_lines:
            print(f"     {line}")

    print(f"  Targets total (post-filter): {len(jobs)} jobs")
    return jobs, boards, failed
