"""
scrapers/indeed.py — Scrape Dutch job boards.
Sources: Werkzoeken.nl (server-side rendered, reliable)
         + direct JSON APIs for Picnic and bol.com
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime
from filters import passes_all

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9,nl;q=0.8",
}

TODAY = datetime.today().strftime("%Y-%m-%d")

SEARCH_QUERIES = [
    "junior data engineer",
    "graduate software engineer",
    "junior machine learning engineer",
    "junior python developer",
    "data engineer trainee",
    "junior backend engineer",
    "graduate data scientist",
    "analytics engineer",
]


def _fetch_werkzoeken(query: str) -> list[dict]:
    """
    Scrape Werkzoeken.nl — one of the best aggregators for NL jobs.
    Server-side rendered so BeautifulSoup works perfectly.
    """
    jobs = []
    try:
        q = query.replace(" ", "+")
        url = f"https://werkzoeken.nl/vacatures/?q={q}&where=Nederland"
        r = requests.get(url, headers=HEADERS, timeout=15)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")

        # Werkzoeken job cards
        for card in soup.select("article.vacancy, div.vacancy, .job-item, li.job"):
            title_el = card.select_one("h2, h3, .title, .vacancy-title")
            link_el  = card.select_one("a[href]")
            comp_el  = card.select_one(".company, .employer, [class*='company']")
            loc_el   = card.select_one(".location, [class*='location']")

            if not title_el or not link_el:
                continue

            title    = title_el.get_text(strip=True)
            href     = link_el["href"]
            company  = comp_el.get_text(strip=True) if comp_el else ""
            location = loc_el.get_text(strip=True) if loc_el else "Netherlands"

            if not href.startswith("http"):
                href = "https://werkzoeken.nl" + href

            if not passes_all(title, location):
                continue

            jobs.append({
                "title":    title,
                "company":  company,
                "location": location,
                "url":      href,
                "source":   "Werkzoeken",
                "date_found": TODAY,
                "description_snippet": "",
            })
    except Exception as e:
        print(f"    Werkzoeken warning ({query}): {e}")
    return jobs


def _fetch_picnic_api() -> list[dict]:
    """
    Picnic exposes a public jobs JSON endpoint — much more reliable than scraping.
    """
    jobs = []
    try:
        url = "https://jobs.picnic.app/api/jobs?language=en"
        r = requests.get(url, headers=HEADERS, timeout=15)
        r.raise_for_status()
        data = r.json()

        # Handle both list and dict responses
        items = data if isinstance(data, list) else data.get("jobs", data.get("data", []))

        for item in items:
            title    = item.get("title", item.get("name", ""))
            location = item.get("location", item.get("city", "Netherlands"))
            job_id   = item.get("id", item.get("slug", ""))
            href     = f"https://jobs.picnic.app/en/vacancies/{job_id}" if job_id else ""

            if not title or not href:
                continue
            if not passes_all(title, location):
                continue

            jobs.append({
                "title":    title,
                "company":  "Picnic",
                "location": location,
                "url":      href,
                "source":   "Careers (Picnic)",
                "date_found": TODAY,
                "description_snippet": item.get("description", "")[:300],
            })
        print(f"    Picnic API: {len(jobs)} matching jobs")
    except Exception as e:
        print(f"    Picnic API warning: {e}")
    return jobs


def _fetch_bol_api() -> list[dict]:
    """
    bol.com careers JSON API.
    """
    jobs = []
    try:
        url = "https://careers.bol.com/en/jobs.json"
        r = requests.get(url, headers=HEADERS, timeout=15)
        r.raise_for_status()
        data = r.json()

        items = data if isinstance(data, list) else data.get("jobs", data.get("data", []))

        for item in items:
            title    = item.get("title", item.get("name", ""))
            location = item.get("location", "Netherlands")
            href     = item.get("url", item.get("link", item.get("apply_url", "")))

            if not title or not href:
                continue
            if not passes_all(title, location):
                continue

            jobs.append({
                "title":    title,
                "company":  "bol.com",
                "location": location,
                "url":      href,
                "source":   "Careers (bol.com)",
                "date_found": TODAY,
                "description_snippet": "",
            })
        print(f"    bol.com API: {len(jobs)} matching jobs")
    except Exception as e:
        print(f"    bol.com API warning: {e}")
    return jobs


def fetch_indeed_jobs() -> list[dict]:
    """
    Main entry point — named fetch_indeed_jobs for drop-in compatibility.
    Scrapes Werkzoeken.nl + Picnic/bol.com JSON APIs.
    """
    all_jobs = []
    seen_urls = set()

    # Werkzoeken for broad market coverage
    for query in SEARCH_QUERIES:
        for job in _fetch_werkzoeken(query):
            if job["url"] not in seen_urls:
                seen_urls.add(job["url"])
                all_jobs.append(job)

    # Direct APIs for key target companies
    for job in _fetch_picnic_api() + _fetch_bol_api():
        if job["url"] not in seen_urls:
            seen_urls.add(job["url"])
            all_jobs.append(job)

    print(f"  Job boards total (post-filter): {len(all_jobs)} jobs")
    return all_jobs