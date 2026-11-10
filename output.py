"""
output.py — Write results to data/jobs.csv. Jobs never go to the Google Sheet (P7).
"""

import os
import csv
import json
from datetime import datetime
from config import CSV_OUTPUT_PATH, SEEN_CACHE_PATH
from ind_checker import normalise_name

COLUMNS = [
    "date_found", "title", "company", "location",
    "ind_sponsor", "source", "url", "description_snippet", "status"
]


# ── Seen-jobs cache ───────────────────────────────────────────────────────────

def load_seen() -> set:
    if not os.path.exists(SEEN_CACHE_PATH):
        return set()
    with open(SEEN_CACHE_PATH) as f:
        return set(json.load(f))


def save_seen(seen: set):
    os.makedirs(os.path.dirname(SEEN_CACHE_PATH), exist_ok=True)
    with open(SEEN_CACHE_PATH, "w") as f:
        json.dump(list(seen), f)


def _posting_key(job: dict) -> str:
    """Same company + title = same posting, even when two sources give different URLs."""
    title = " ".join(job["title"].lower().split())
    return f"{normalise_name(job['company'])}|{title}"


def deduplicate(jobs: list[dict], seen: set) -> list[dict]:
    """Filter out jobs already seen in previous runs, or earlier in this one."""
    new_jobs = []
    for j in jobs:
        key = _posting_key(j)
        if j["url"] in seen or key in seen:
            continue
        seen.add(j["url"])
        seen.add(key)
        new_jobs.append(j)
    return new_jobs


# ── CSV output ────────────────────────────────────────────────────────────────

def write_csv(jobs: list[dict]):
    os.makedirs(os.path.dirname(CSV_OUTPUT_PATH), exist_ok=True)
    file_exists = os.path.exists(CSV_OUTPUT_PATH)

    with open(CSV_OUTPUT_PATH, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS, extrasaction="ignore")
        if not file_exists:
            writer.writeheader()
        for job in jobs:
            job.setdefault("status", "To Review")
            writer.writerow(job)

    print(f"  CSV updated: {CSV_OUTPUT_PATH} (+{len(jobs)} rows)")

