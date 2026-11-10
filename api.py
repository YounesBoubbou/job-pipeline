"""
api.py — Minimal FastAPI backend for the job-pipeline React frontend.

Run with:
    python api.py
  or:
    uvicorn api:app --reload
"""

import json
import os
import sys
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Make config, scrapers, etc. importable from the repo root
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Pull paths from config; fall back to sensible defaults so api.py
# works even if config.py has import-time side effects that fail.
try:
    from config import CSV_OUTPUT_PATH, RUN_SUMMARY_PATH, SHEETS_CREDENTIALS_FILE, SPREADSHEET_NAME
except Exception:
    CSV_OUTPUT_PATH = "data/jobs.csv"
    RUN_SUMMARY_PATH = "data/last_run.json"
    SHEETS_CREDENTIALS_FILE = "credentials.json"
    SPREADSHEET_NAME = "Job Pipeline"

_ROOT = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(_ROOT, CSV_OUTPUT_PATH)
CREDS_PATH = os.path.join(_ROOT, SHEETS_CREDENTIALS_FILE)
SUMMARY_PATH = os.path.join(_ROOT, RUN_SUMMARY_PATH)

TRACKER_TAB = "Applications"
TRACKER_COLUMNS = ["title", "company", "url", "date_applied", "status"]

# ── App ────────────────────────────────────────────────────────────────────────

app = FastAPI(title="Job Pipeline API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Google Sheets helper ───────────────────────────────────────────────────────

def _get_tracker_sheet():
    """Open (or create) the Applications worksheet in the configured spreadsheet."""
    import gspread
    from google.oauth2.service_account import Credentials

    if not os.path.exists(CREDS_PATH):
        raise FileNotFoundError(
            f"credentials.json not found at {CREDS_PATH}. "
            "See README.md for Google Sheets setup instructions."
        )

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = Credentials.from_service_account_file(CREDS_PATH, scopes=scopes)
    client = gspread.authorize(creds)
    spreadsheet = client.open(SPREADSHEET_NAME)

    try:
        return spreadsheet.worksheet(TRACKER_TAB)
    except gspread.exceptions.WorksheetNotFound:
        ws = spreadsheet.add_worksheet(title=TRACKER_TAB, rows=1000, cols=10)
        ws.insert_row(TRACKER_COLUMNS, index=1)
        return ws


# ── Run summary helpers ────────────────────────────────────────────────────────

def _read_summary():
    """Read data/last_run.json. Returns (summary, None) or (None, message) when the
    file is missing, unreadable or not a JSON object."""
    if not os.path.exists(SUMMARY_PATH):
        return None, "The pipeline has not run yet (no run summary file)."
    try:
        with open(SUMMARY_PATH, encoding="utf-8") as f:
            summary = json.load(f)
    except (OSError, ValueError) as exc:
        return None, f"The run summary file could not be read: {exc}"
    if not isinstance(summary, dict):
        return None, "The run summary file could not be read: not a JSON object."
    return summary, None


def _last_run_added_count():
    """How many jobs the last run added (its jobs_added), or 0 when that is unknown:
    no or unreadable summary, or jobs_added missing, not a whole number, or negative."""
    summary, _ = _read_summary()
    if summary is None:
        return 0
    added = summary.get("jobs_added")
    if isinstance(added, bool) or not isinstance(added, int) or added < 0:
        return 0
    return added


# ── Endpoints ──────────────────────────────────────────────────────────────────

@app.get("/api/jobs")
def get_jobs():
    """Return all jobs from data/jobs.csv as JSON (column names preserved).

    Each job also gets is_new (W3): True for the jobs added by the most recent run.
    jobs.csv is append-only, so those are its last jobs_added rows (ADR 0011). If that
    count is unknown or larger than the file, no job is marked."""
    if not os.path.exists(CSV_PATH):
        return []
    df = pd.read_csv(CSV_PATH, dtype=str).fillna("")
    jobs = df.to_dict(orient="records")
    added = _last_run_added_count()
    first_new = len(jobs) - added if 0 < added <= len(jobs) else len(jobs)
    for i, job in enumerate(jobs):
        job["is_new"] = i >= first_new
    return jobs


@app.get("/api/last-run")
def get_last_run():
    """Return the summary of the last pipeline run (W8), read from data/last_run.json.
    A missing or unreadable file is not an error: the app shows the message instead."""
    summary, message = _read_summary()
    if summary is None:
        return {"found": False, "message": message}
    return {"found": True, "summary": summary}


class TrackerEntry(BaseModel):
    title: str
    company: str
    url: str
    date_applied: str
    status: str = "Applied"


class StatusUpdate(BaseModel):
    url: str
    status: str


class CVRequest(BaseModel):
    url: str


@app.post("/api/jobs/generate-cv")
def generate_cv(req: CVRequest):
    """Generate a JD-tailored CV (.tex) for the job identified by its URL."""
    if not os.path.exists(CSV_PATH):
        raise HTTPException(status_code=404, detail="No jobs data found")

    df = pd.read_csv(CSV_PATH, dtype=str).fillna("")
    matches = df[df["url"] == req.url]
    if matches.empty:
        raise HTTPException(status_code=404, detail="Job not found")
    job = matches.iloc[0].to_dict()

    from cv_generator import generate_tailored_cv, save_generated_cv

    try:
        tex = generate_tailored_cv(job)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    filename = save_generated_cv(job, tex)
    return {"ok": True, "filename": filename, "tex": tex}


@app.post("/api/jobs/generate-cover-letter")
def generate_cover_letter_endpoint(req: CVRequest):
    """Generate a JD-tailored cover letter (.txt) for the job identified by its URL."""
    if not os.path.exists(CSV_PATH):
        raise HTTPException(status_code=404, detail="No jobs data found")

    df = pd.read_csv(CSV_PATH, dtype=str).fillna("")
    matches = df[df["url"] == req.url]
    if matches.empty:
        raise HTTPException(status_code=404, detail="Job not found")
    job = matches.iloc[0].to_dict()

    from cover_letter_generator import generate_cover_letter, save_cover_letter

    try:
        letter = generate_cover_letter(job)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    filename = save_cover_letter(job, letter)
    return {"ok": True, "filename": filename, "letter": letter}


@app.get("/api/tracker")
def get_tracker():
    """Return all rows from the Applications Google Sheet tab."""
    try:
        ws = _get_tracker_sheet()
        return ws.get_all_records()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@app.post("/api/tracker")
def add_to_tracker(entry: TrackerEntry):
    """Append a new application row to the Applications Google Sheet tab."""
    try:
        ws = _get_tracker_sheet()
        ws.append_row([
            entry.title,
            entry.company,
            entry.url,
            entry.date_applied,
            entry.status,
        ])
        return {"ok": True}
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@app.patch("/api/tracker/status")
def update_status(update: StatusUpdate):
    """Update the status cell for a tracked job identified by its URL."""
    try:
        ws = _get_tracker_sheet()
        cell = ws.find(update.url)
        if cell:
            status_col = TRACKER_COLUMNS.index("status") + 1  # 1-indexed
            ws.update_cell(cell.row, status_col, update.status)
        return {"ok": True}
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc))


# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="127.0.0.1", port=8000, reload=True)
