"""
scrapers/indeed.py — Pull job listings from Indeed via RSS feeds.
Indeed provides RSS for any search query — no scraping needed.
"""

import feedparser
from datetime import datetime
from filters import passes_all
from config import INDEED_RSS_FEEDS


def _parse_date(entry) -> str:
    """Extract a clean date string from a feed entry."""
    if hasattr(entry, "published_parsed") and entry.published_parsed:
        return datetime(*entry.published_parsed[:3]).strftime("%Y-%m-%d")
    return datetime.today().strftime("%Y-%m-%d")


def fetch_indeed_jobs() -> list[dict]:
    """Fetch and filter jobs from all configured Indeed RSS feeds."""
    jobs = []
    seen_urls = set()

    for feed_url in INDEED_RSS_FEEDS:
        try:
            feed = feedparser.parse(feed_url)
            print(f"  Indeed RSS: {len(feed.entries)} entries from {feed_url[:80]}...")

            for entry in feed.entries:
                title    = entry.get("title", "")
                link     = entry.get("link", "")
                summary  = entry.get("summary", "")
                location = entry.get("location", "") or ""

                # Deduplicate within this run
                if link in seen_urls:
                    continue
                seen_urls.add(link)

                # Try to extract company from title (Indeed format: "Title - Company")
                company = ""
                if " - " in title:
                    parts = title.rsplit(" - ", 1)
                    title_clean = parts[0].strip()
                    company = parts[1].strip() if len(parts) > 1 else ""
                else:
                    title_clean = title

                if not passes_all(title_clean, location, summary):
                    continue

                jobs.append({
                    "title":   title_clean,
                    "company": company,
                    "location": location or "Netherlands",
                    "url":     link,
                    "source":  "Indeed",
                    "date_found": _parse_date(entry),
                    "description_snippet": summary[:300].strip(),
                })

        except Exception as e:
            print(f"  Warning: failed to fetch {feed_url[:60]}... — {e}")

    print(f"  Indeed total (post-filter): {len(jobs)} jobs")
    return jobs
