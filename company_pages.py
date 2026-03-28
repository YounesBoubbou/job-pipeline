"""
scrapers/company_pages.py — Scrape job listings from company career pages.
Uses a generic approach that works for most static/JS-light pages.
For JS-heavy pages (React SPAs), results may be limited without a headless browser.
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime
from filters import passes_all
from config import COMPANY_PAGES

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

TODAY = datetime.today().strftime("%Y-%m-%d")


def _extract_job_links(soup: BeautifulSoup, base_url: str) -> list[dict]:
    """
    Generic link extraction — looks for <a> tags that look like job listings.
    Heuristic: links containing /job/ /vacancy/ /careers/ /opening/ /position/
    """
    job_keywords = ["/job", "/vacancy", "/vacature", "/career", "/opening", "/position", "/role"]
    results = []
    seen = set()

    for a in soup.find_all("a", href=True):
        href = a["href"]
        text = a.get_text(strip=True)

        if not text or len(text) < 4:
            continue

        # Make absolute URL
        if href.startswith("/"):
            from urllib.parse import urlparse
            parsed = urlparse(base_url)
            href = f"{parsed.scheme}://{parsed.netloc}{href}"
        elif not href.startswith("http"):
            continue

        if href in seen:
            continue

        if any(kw in href.lower() for kw in job_keywords):
            seen.add(href)
            results.append({"title": text, "url": href})

    return results


def fetch_company_jobs() -> list[dict]:
    """Scrape all configured company career pages and return filtered jobs."""
    jobs = []

    for company in COMPANY_PAGES:
        name = company["name"]
        url  = company["url"]

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
                    "title":    title,
                    "company":  name,
                    "location": "Netherlands",
                    "url":      link,
                    "source":   f"Careers ({name})",
                    "date_found": TODAY,
                    "description_snippet": "",
                })

        except Exception as e:
            print(f"  Warning: could not scrape {name} ({url}) — {e}")

    print(f"  Company pages total (post-filter): {len(jobs)} jobs")
    return jobs
