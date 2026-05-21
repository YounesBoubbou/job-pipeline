"""
api.py — Minimal FastAPI backend for the job-pipeline React frontend.

Run with:
    python api.py
  or:
    uvicorn api:app --reload
"""

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
    from config import CSV_OUTPUT_PATH, SHEETS_CREDENTIALS_FILE, SPREADSHEET_NAME
except Exception:
    CSV_OUTPUT_PATH = "data/jobs.csv"
    SHEETS_CREDENTIALS_FILE = "credentials.json"
    SPREADSHEET_NAME = "Job Pipeline"

_ROOT = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(_ROOT, CSV_OUTPUT_PATH)
CREDS_PATH = os.path.join(_ROOT, SHEETS_CREDENTIALS_FILE)

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
        ws.append_row(TRACKER_COLUMNS)
        return ws


# ── Endpoints ──────────────────────────────────────────────────────────────────

@app.get("/api/jobs")
def get_jobs():
    """Return all jobs from data/jobs.csv as JSON (column names preserved)."""
    if not os.path.exists(CSV_PATH):
        return []
    df = pd.read_csv(CSV_PATH, dtype=str).fillna("")
    return df.to_dict(orient="records")


class TrackerEntry(BaseModel):
    title: str
    company: str
    url: str
    date_applied: str
    status: str = "Applied"


class StatusUpdate(BaseModel):
    url: str
    status: str


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
