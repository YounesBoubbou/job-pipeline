"""
scrapers/company_pages.py — Scrape job listings from company career pages.

Two strategies:
  1. Generic HTML scraper  — for most static/JS-light pages.
  2. Greenhouse JSON API   — for companies that use Greenhouse ATS
     (boards-api.greenhouse.io/v1/boards/{slug}/jobs).
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime
from filters import passes_all
from config import COMPANY_PAGES

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

TODAY = datetime.today().strftime("%Y-%m-%d")

# Companies with Greenhouse ATS — slug maps to boards-api.greenhouse.io/v1/boards/{slug}
GREENHOUSE_COMPANIES = {
    "Catawiki": "catawiki",
    "Adyen":    "adyen",
}


def _slug_to_title(url: str) -> str:
    import re
    from urllib.parse import urlparse
    path = urlparse(url).path
    slug = path.rstrip("/").split("/")[-1]
    slug = re.sub(r"-\d{4,}$", "", slug)
    return slug.replace("-", " ").replace("_", " ").title()


def _extract_job_links(soup: BeautifulSoup, base_url: str) -> list[dict]:
    """Generic link extraction for HTML career pages."""
    job_url_keywords = ["/job", "/vacancy", "/vacature", "/career", "/opening", "/position", "/role"]
    generic_texts = {"apply", "view", "read more", "meer info", "bekijk", "open", "details"}
    results = []
    seen = set()

    for a in soup.find_all("a", href=True):
        href = a["href"]
        text = a.get_text(strip=True)

        if href.startswith("/"):
            from urllib.parse import urlparse
            parsed = urlparse(base_url)
            href = f"{parsed.scheme}://{parsed.netloc}{href}"
        elif not href.startswith("http"):
            continue

        if href in seen:
            continue
        if not any(kw in href.lower() for kw in job_url_keywords):
            continue

        seen.add(href)

        if not text or len(text) < 5 or text.lower() in generic_texts:
            text = _slug_to_title(href)
        if not text or len(text) < 5:
            continue

        results.append({"title": text, "url": href})

    return results


def _fetch_greenhouse(company_name: str, gh_slug: str) -> list[dict]:
    """
    Fetch jobs from the Greenhouse public JSON API.
    No auth required. Returns full job list with title, location, and absolute URL.
    """
    jobs = []
    try:
        api_url = f"https://boards-api.greenhouse.io/v1/boards/{gh_slug}/jobs?content=true"
        r = requests.get(api_url, headers=HEADERS, timeout=15)
        r.raise_for_status()
        items = r.json().get("jobs", [])
        print(f"  {company_name} (Greenhouse): {len(items)} listings found")

        for item in items:
            title    = item.get("title", "")
            href     = item.get("absolute_url", "")
            location = item.get("location", {}).get("name", "Netherlands")
            content  = item.get("content", "")[:300]   # job description HTML snippet

            if not title or not href:
                continue
            if not passes_all(title, location, content):
                continue

            jobs.append({
                "title":               title,
                "company":             company_name,
                "location":            location,
                "url":                 href,
                "source":              f"Careers ({company_name})",
                "date_found":          TODAY,
                "description_snippet": content[:300],
            })

    except Exception as e:
        print(f"  Warning: Greenhouse fetch failed for {company_name} — {e}")
    return jobs


def fetch_company_jobs() -> list[dict]:
    """Scrape all configured company career pages."""
    jobs = []

    # ── Greenhouse companies (JSON API — fast and reliable) ────────────────
    for name, slug in GREENHOUSE_COMPANIES.items():
        jobs.extend(_fetch_greenhouse(name, slug))

    # ── HTML-scraped career pages (from config.py COMPANY_PAGES) ──────────
    for company in COMPANY_PAGES:
        name = company["name"]
        url  = company["url"]

        # Skip if this company is already handled via Greenhouse
        if name in GREENHOUSE_COMPANIES:
            continue

        try:
            r = requests.get(url, headers=HEADERS, timeout=15)
            r.raise_for_status()
            soup = BeautifulSoup(r.text, "html.parser")

            candidates = _extract_job_links(soup, url)
            print(f"  {name}: {len(candidates)} links found on careers page")

            for c in candidates:
                title = c["title"]
                link  = c["url"]

                if not passes_all(title, location="Netherlands"):
                    continue

                jobs.append({
                    "title":               title,
                    "company":             name,
                    "location":            "Netherlands",
                    "url":                 link,
                    "source":              f"Careers ({name})",
                    "date_found":          TODAY,
                    "description_snippet": "",
                })

        except Exception as e:
            print(f"  Warning: could not scrape {name} ({url}) — {e}")

    print(f"  Company pages total (post-filter): {len(jobs)} jobs")
    return jobs
