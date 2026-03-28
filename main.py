"""
main.py — Entry point for the job discovery pipeline.
Run with:  python main.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from datetime import datetime
from scrapers.indeed import fetch_indeed_jobs
from scrapers.company_pages import fetch_company_jobs
from ind_checker import is_ind_sponsor
from output import load_seen, save_seen, deduplicate, write_csv, write_sheets


def run():
    print(f"\n{'='*55}")
    print(f"  Job Pipeline — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*55}\n")

    # ── 1. Scrape all sources ──────────────────────────────
    print("[1/4] Fetching jobs from Indeed RSS...")
    indeed_jobs = fetch_indeed_jobs()

    print("\n[2/4] Scraping company career pages...")
    company_jobs = fetch_company_jobs()

    all_jobs = indeed_jobs + company_jobs
    print(f"\n  Total raw (pre-dedup): {len(all_jobs)} jobs")

    # ── 2. Deduplicate against previous runs ───────────────
    print("\n[3/4] Deduplicating against seen jobs cache...")
    seen = load_seen()
    new_jobs = deduplicate(all_jobs, seen)
    save_seen(seen)
    print(f"  New jobs this run: {len(new_jobs)}")

    if not new_jobs:
        print("\n  Nothing new today. Run again tomorrow!")
        return

    # ── 3. Enrich with IND sponsor status ─────────────────
    print("\n[4/4] Checking IND sponsor register...")
    for job in new_jobs:
        company = job.get("company", "")
        job["ind_sponsor"] = is_ind_sponsor(company) if company else "Unknown"

    # Summary
    yes_count     = sum(1 for j in new_jobs if j["ind_sponsor"] == "Yes")
    unknown_count = sum(1 for j in new_jobs if j["ind_sponsor"] == "Unknown")
    no_count      = sum(1 for j in new_jobs if j["ind_sponsor"] == "No")
    print(f"  IND sponsor breakdown — Yes: {yes_count} | Unknown: {unknown_count} | No: {no_count}")

    # ── 4. Write output ────────────────────────────────────
    write_csv(new_jobs)
    write_sheets(new_jobs)

    # ── 5. Print digest to terminal ───────────────────────
    print(f"\n{'─'*55}")
    print(f"  TODAY'S NEW JOBS ({len(new_jobs)} found)")
    print(f"{'─'*55}")
    for job in sorted(new_jobs, key=lambda x: x["ind_sponsor"] == "Yes", reverse=True):
        sponsor_tag = f"[IND✓]" if job["ind_sponsor"] == "Yes" else ""
        print(f"  {sponsor_tag} {job['title']} @ {job['company']}")
        print(f"     {job['url'][:80]}")
        print()

    print(f"  Full list saved to: data/jobs.csv")
    print(f"{'='*55}\n")


if __name__ == "__main__":
    run()
