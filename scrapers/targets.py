"""
scrapers/targets.py — Fetch openings for every company in targets.csv (ADR-0005).

Each row names a company, its ATS vendor (`source`) and its board token. Every vendor
here has a public JSON API (GetNoticed's descriptions come from its RSS feed), except
Heineken's own site, whose job list is read from HTML (ADR-0010). Boards that fail are
reported at the end of the run rather than skipped silently, since a failure usually means
the company moved to another ATS and the row needs updating.
"""

import csv
import os
import re
import time
import xml.etree.ElementTree as ET
from datetime import datetime
from urllib.parse import parse_qs, urlsplit

import requests
from bs4 import BeautifulSoup

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


def _lever(token, api="https://api.lever.co"):
    # TomTom's board is on Lever's EU instance, api.eu.lever.co (ADR-0010).
    r = requests.get(f"{api}/v0/postings/{token}?mode=json",
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


# Booking.com and ABN AMRO run their own careers sites on iCIMS Jibe and GetNoticed
# (ADR-0009). Both are asked for Netherlands jobs only, like Workday (ADR-0008).

def _jibe_job_url(base, j):
    # Mammoet's jobs (iCIMS behind Jibe) have no canonical_url. Its site opens a job at
    # /jobs/<slug>?lang=<language>; without the language it shows an empty page.
    url = (j.get("meta_data") or {}).get("canonical_url")
    if url:
        return url
    slug = j.get("slug") or j.get("req_id")
    if not slug:
        return ""
    return f"{base}/jobs/{slug}" + (f"?lang={j['language']}" if j.get("language") else "")


def _jibe(token):
    # Token is the careers site, e.g. https://jobs.booking.com. Its robots.txt asks for
    # 5 seconds between requests.
    base, page = token.rstrip("/"), 1
    while True:
        r = requests.get(f"{base}/api/jobs", params={"page": page, "limit": 100, "country": "Netherlands"},
                         headers=HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
        data = r.json()
        for x in data["jobs"]:
            j = x["data"]
            url = _jibe_job_url(base, j)
            if url:  # a job without an address can't be opened or deduplicated
                yield j["title"], j.get("full_location", ""), url, j.get("description", "")
        if page * 100 >= data["totalCount"] or not data["jobs"]:
            break
        page += 1
        time.sleep(5)


def _getnoticed(token):
    # Token is the careers site, e.g. https://www.werkenbijabnamro.nl. The API answers with
    # JSON only when the request says it comes from the page's own script, and pages are
    # fixed at 8 vacancies. The country filter is picked from the first page's facets.
    base = token.rstrip("/")
    headers = {**HEADERS, "X-Requested-With": "XMLHttpRequest"}

    def page(n, filters):
        r = requests.get(f"{base}/api/vacancy/", params={"pageNumber": n, **filters},
                         headers=headers, timeout=TIMEOUT)
        r.raise_for_status()
        return r.json()

    first, filters = page(1, {}), {}
    for f in first.get("facets", []):
        for v in f.get("values", []):
            # The API matches a filter on the value's display name, not its slug: Ahold
            # Delhaize's "The Netherlands" has slug "nld", which is ignored (ADR-0010).
            name = v.get("value", "").strip().lower()
            if v.get("slug") in ("nederland", "netherlands") or name in NL_NAMES:
                filters = {f"filters[{f['slug']}][]": v.get("value", v["slug"])}
        if filters:
            break
    data = page(1, filters) if filters else first
    descriptions = _getnoticed_descriptions(base)
    n = 1
    while True:
        for v in data["vacancies"]:
            location = _spell_nl(", ".join(p for p in (v.get("city"), v.get("country")) if p))
            yield (v["title"], location, f"{base}/vacature/{v['id']}/{v['slug']}",
                   descriptions.get(str(v["id"]), ""))
        n += 1
        if n > data["meta"]["totalPageCount"] or not data["vacancies"]:
            break
        data = page(n, filters)


def _getnoticed_descriptions(base):
    # The listings carry no description, but the RSS feed has every vacancy with its full
    # text. Returns {vacancy id: description}; {} if the feed can't be read.
    try:
        r = requests.get(f"{base}/feeds/rss", headers=HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
        descriptions = {}
        for item in ET.fromstring(r.content).iter("item"):
            m = re.search(r"/vacature/(\d+)/", item.findtext("link") or "")
            if m:
                descriptions[m.group(1)] = item.findtext("description") or ""
        return descriptions
    except Exception:
        return {}


# HSBC and DSM-Firmenich (Eightfold), AkzoNobel (Phenom) and Heineken (its own site) are
# asked for Netherlands jobs only too (ADR-0010).

NL_NAMES = ("nederland", "netherlands", "the netherlands")


def _spell_nl(location):
    # GetNoticed and Phenom sites may write the country as "NLD", which the location filter
    # doesn't know. Spelled out here so the filter rules stay as they are (ADR-0010).
    return re.sub(r"\bNLD\b", "Netherlands", location)


def _eightfold_site(token):
    # Token is the public search page, e.g. https://jobs.dsm-firmenich.com/careers?domain=dsm.com
    parts = urlsplit(token)
    return f"{parts.scheme}://{parts.netloc}", parse_qs(parts.query)["domain"][0]


def _eightfold(token):
    # Eightfold has two listing APIs and each site has only one switched on; the other
    # answers 403. The newer one is tried first. Both return pages of 10.
    base, domain = _eightfold_site(token)
    newer, start = True, 0
    while True:
        if newer:
            r = requests.get(f"{base}/api/pcsx/search", headers=HEADERS, timeout=TIMEOUT,
                             params={"domain": domain, "query": "", "location": "Netherlands", "start": start})
            if r.status_code == 403 and start == 0:
                newer = False
                continue
        else:
            r = requests.get(f"{base}/api/apply/v2/jobs", headers=HEADERS, timeout=TIMEOUT,
                             params={"domain": domain, "start": start, "num": 10, "location": "Netherlands"})
        r.raise_for_status()
        data = r.json()["data"] if newer else r.json()
        for j in data["positions"]:
            location = "; ".join(j.get("locations") or []) or j.get("location", "")
            url = base + j["positionUrl"] if newer else j["canonicalPositionUrl"]
            yield j["name"], location, url, "" if newer else j.get("job_description", "")
        start += 10
        if start >= data["count"] or not data["positions"]:
            break
        time.sleep(1)


def _phenom(token):
    # Token is the site with its country and language, e.g. https://careers.akzonobel.com/gb/en.
    # The page loads jobs by POSTing to /widgets. The first answer lists the country filter,
    # whose Dutch value is then asked for.
    base, country, lang = _phenom_site(token)

    def page(start, selected):
        r = requests.post(f"{base}/widgets", headers=HEADERS, timeout=TIMEOUT, json={
            "ddoKey": "refineSearch", "lang": lang, "country": country, "siteType": "external",
            "pageName": "search-results", "keywords": "", "global": True, "jobs": True, "counts": True,
            "all_fields": ["country"], "size": 100, "from": start, "selected_fields": selected})
        r.raise_for_status()
        return r.json()["refineSearch"]

    data, selected = page(0, {}), {}
    countries = [a.get("value", {}) for a in data["data"].get("aggregations", []) if a.get("field") == "country"]
    if countries:
        dutch = [k for k in countries[0] if k.strip().lower() in NL_NAMES + ("nld", "nl")]
        if not dutch:
            return  # the site has a country filter, and no Dutch jobs right now
        selected = {"country": dutch[:1]}
        data = page(0, selected)
    start = 0
    while True:
        for j in data["data"]["jobs"]:
            location = "; ".join(j.get("multi_location") or []) or j.get("location", "")
            yield j["title"], _spell_nl(location), f"{token.rstrip('/')}/job/{j['jobSeqNo']}", ""
        start += 100
        if start >= data["totalHits"] or not data["data"]["jobs"]:
            break
        data = page(start, selected)


def _phenom_site(token):
    base, country, lang = token.rstrip("/").rsplit("/", 2)
    return base, country, f"{lang}_{country}"


def _heineken(token):
    # Token is https://careers.theheinekencompany.com. No API: the job list is server-rendered
    # HTML, 10 jobs a page. robots.txt asks for 5 seconds between requests. The order shifts
    # a little between pages, so a job can show up twice. Descriptions are only on each job's
    # own page; _heineken_description reads them (ADR-0012).
    base, seen = token.rstrip("/"), set()
    for n in range(30):
        if n:
            time.sleep(5)
        r = requests.get(f"{base}/Job-Listing", headers=HEADERS, timeout=TIMEOUT,
                         params={"field_location_country_code_1[]": "NL", "page": f"0,0,{n}"})
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        items = soup.select(".job-list-item")
        for item in items:
            a, nation = item.select_one(".job-title a"), item.select_one(".nation")
            if a is None or not a.get("href"):
                continue
            url = base + a["href"]
            if url in seen:
                continue
            seen.add(url)
            yield a.get_text(strip=True), nation.get_text(" ", strip=True) if nation else "", url, ""
        if not items or soup.select_one("a[rel=next]") is None:
            break


# Workday, SmartRecruiters, Eightfold, Phenom and Heineken listings carry no description, so
# it takes one request per job. Heineken waits 5 seconds before each one (its robots.txt).
# On failure these return "", which leaves only the title and location for the filters to judge.

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


def _eightfold_description(token, url):
    base, domain = _eightfold_site(token)
    try:
        r = requests.get(f"{base}/api/apply/v2/jobs/{url.rstrip('/').rsplit('/', 1)[1]}",
                         params={"domain": domain}, headers=HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
        return r.json().get("job_description", "")
    except Exception:
        return ""


def _phenom_description(token, url):
    base, country, lang = _phenom_site(token)
    try:
        r = requests.post(f"{base}/widgets", headers=HEADERS, timeout=TIMEOUT, json={
            "ddoKey": "jobDetail", "jobSeqNo": url.rsplit("/job/", 1)[1], "lang": lang,
            "country": country, "siteType": "external", "pageName": "job"})
        r.raise_for_status()
        return r.json()["jobDetail"]["data"]["job"].get("description", "")
    except Exception:
        return ""


def _heineken_description(token, url):
    # token is unused; it is here so all description fetchers take the same arguments.
    try:
        time.sleep(5)
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
        fields = BeautifulSoup(r.text, "html.parser").select_one(".job-fields")
        return fields.get_text(" ", strip=True) if fields else ""
    except Exception:
        return ""


DESCRIPTION_FETCHERS = {
    "workday":         _workday_description,
    "smartrecruiters": _smartrecruiters_description,
    "eightfold":       _eightfold_description,
    "phenom":          _phenom_description,
    "heineken":        _heineken_description,
}

FETCHERS = {
    "greenhouse":      _greenhouse,
    "lever":           _lever,
    "ashby":           _ashby,
    "recruitee":       _recruitee,
    "smartrecruiters": _smartrecruiters,
    "workday":         _workday,
    "jibe":            _jibe,
    "getnoticed":      _getnoticed,
    "lever_eu":        lambda token: _lever(token, "https://api.eu.lever.co"),
    "eightfold":       _eightfold,
    "phenom":          _phenom,
    "heineken":        _heineken,
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
