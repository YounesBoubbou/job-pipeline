"""
scrapers/indeed.py — Scrape tech job listings.
Sources:
  - RemoteOK API  (free, no auth — remote tech jobs worldwide)
  - Arbeitnow API (free, no auth — EU / remote tech jobs)
"""

import requests
from datetime import datetime
from filters import passes_all, strip_html

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9,nl;q=0.8",
}

TODAY = datetime.today().strftime("%Y-%m-%d")


def _fetch_remoteok() -> list[dict]:
    """
    RemoteOK — free API, no auth required, all-remote tech jobs.
    https://remoteok.com/api
    First element in the JSON array is metadata, skip it.
    """
    jobs = []
    try:
        r = requests.get(
            "https://remoteok.com/api",
            headers={**HEADERS, "Accept": "application/json"},
            timeout=15,
        )
        r.raise_for_status()
        items = [j for j in r.json() if isinstance(j, dict) and j.get("position")]

        for item in items:
            title       = item.get("position", "")
            company     = item.get("company", "")
            description = item.get("description", "")[:300]
            href        = item.get("apply_url") or item.get("url", "")

            # All RemoteOK jobs are remote — ensure location passes our filter
            raw_loc  = item.get("location", "")
            location = raw_loc if raw_loc and raw_loc.lower() != "worldwide" else "Remote"

            if not title or not href:
                continue
            if not passes_all(title, location, description):
                continue

            jobs.append({
                "title":               title,
                "company":             company,
                "location":            location,
                "url":                 href,
                "source":              "RemoteOK",
                "date_found":          TODAY,
                "description_snippet": strip_html(description),
            })

        print(f"    RemoteOK: {len(jobs)} matching jobs")
    except Exception as e:
        print(f"    RemoteOK warning: {e}")
    return jobs


def _fetch_arbeitnow() -> list[dict]:
    """
    Arbeitnow — free API, no auth, EU & remote tech jobs.
    Only keeps remote=True OR Netherlands-based roles.
    https://arbeitnow.com/api
    """
    jobs = []
    try:
        seen_urls = set()
        for page in range(1, 4):
            url = f"https://www.arbeitnow.com/api/job-board-api?page={page}"
            r = requests.get(url, headers=HEADERS, timeout=15)
            r.raise_for_status()
            items = r.json().get("data", [])
            if not items:
                break

            for item in items:
                title       = item.get("title", "")
                raw_loc     = item.get("location", "")
                href        = item.get("url", "")
                description = item.get("description", "")[:300]
                company     = item.get("company_name", "")
                remote      = item.get("remote", False)

                if href in seen_urls:
                    continue

                is_nl = any(kw in raw_loc.lower() for kw in ["netherlands", "amsterdam", "rotterdam", "eindhoven"])
                if not remote and not is_nl:
                    continue

                location = raw_loc if raw_loc else ("Remote" if remote else "Netherlands")
                if not passes_all(title, location, description):
                    continue

                seen_urls.add(href)
                jobs.append({
                    "title":               title,
                    "company":             company,
                    "location":            location,
                    "url":                 href,
                    "source":              "Arbeitnow",
                    "date_found":          TODAY,
                    "description_snippet": strip_html(description),
                })

        print(f"    Arbeitnow: {len(jobs)} matching jobs")
    except Exception as e:
        print(f"    Arbeitnow warning: {e}")
    return jobs


def fetch_indeed_jobs() -> list[dict]:
    """Main entry point — named for drop-in compatibility with main.py."""
    all_jobs  = []
    seen_urls = set()

    for job in _fetch_remoteok() + _fetch_arbeitnow():
        if job["url"] not in seen_urls:
            seen_urls.add(job["url"])
            all_jobs.append(job)

    print(f"  Job boards total (post-filter): {len(all_jobs)} jobs")
    return all_jobs
