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
from scrapers.targets import fetch_target_jobs
from ind_checker import job_sponsor_status
from output import load_seen, save_seen, deduplicate, write_csv, write_run_summary


def run():
    started = datetime.now().astimezone()
    # Written to data/last_run.json at the end, even if the run crashes (P1, P5)
    summary = {
        "started_at":       started.isoformat(timespec="seconds"),
        "finished_at":      None,
        "duration_seconds": None,
        "status":           "completed",
        "error":            None,
        "jobs_added":       0,
        "boards":           [],
        "failed":           [],
    }
    try:
        _run(summary)
    except BaseException as e:
        summary["status"] = "crashed"
        summary["error"]  = f"{type(e).__name__}: {e}"
        raise
    finally:
        finished = datetime.now().astimezone()
        summary["finished_at"]      = finished.isoformat(timespec="seconds")
        summary["duration_seconds"] = round((finished - started).total_seconds())
        write_run_summary(summary)
        print(f"  Run summary: data/last_run.json "
              f"({len(summary['boards'])} boards, {len(summary['failed'])} failed)")


def _run(summary: dict):
    print(f"\n{'='*55}")
    print(f"  Job Pipeline — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*55}\n")

    # ── 1. Scrape all sources ──────────────────────────────
    # A source that crashes as a whole is recorded as failed; the others still run (P5).
    all_jobs = []
    sources = (
        ("Job boards",    "[1/5] Fetching job boards (RemoteOK, Arbeitnow)...",  fetch_indeed_jobs),
        ("Company pages", "\n[2/5] Scraping company career pages...",           fetch_company_jobs),
        ("Target list",   "\n[3/5] Fetching target-list boards...",             fetch_target_jobs),
    )
    for label, heading, fetch in sources:
        print(heading)
        try:
            jobs, boards, failed = fetch()
        except Exception as e:
            reason = f"{type(e).__name__}: {e}"
            print(f"  !! {label} FAILED: {reason}")
            summary["failed"].append({"name": label, "source": "source", "reason": reason})
            continue
        all_jobs.extend(jobs)
        summary["boards"].extend(boards)
        summary["failed"].extend(failed)

    print(f"\n  Total raw (pre-dedup): {len(all_jobs)} jobs")

    # ── 2. Deduplicate against previous runs ───────────────
    print("\n[4/5] Deduplicating against seen jobs cache...")
    seen = load_seen()
    new_jobs = deduplicate(all_jobs, seen)
    save_seen(seen)
    print(f"  New jobs this run: {len(new_jobs)}")

    if not new_jobs:
        print("\n  Nothing new today. Run again tomorrow!")
        return

    # ── 3. Enrich with IND sponsor status ─────────────────
    print("\n[5/5] Checking IND sponsor register...")
    for job in new_jobs:
        job["ind_sponsor"] = job_sponsor_status(job)

    # Summary
    yes_count     = sum(1 for j in new_jobs if j["ind_sponsor"] == "Yes")
    unknown_count = sum(1 for j in new_jobs if j["ind_sponsor"] == "Unknown")
    no_count      = sum(1 for j in new_jobs if j["ind_sponsor"] == "No")
    print(f"  IND sponsor breakdown — Yes: {yes_count} | Unknown: {unknown_count} | No: {no_count}")

    # ── 4. Write output ────────────────────────────────────
    write_csv(new_jobs)   # jobs live in the CSV only; the Sheet holds the tracker (P7)
    summary["jobs_added"] = len(new_jobs)

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
