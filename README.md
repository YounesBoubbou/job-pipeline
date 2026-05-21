# Job Pipeline 🔍

A personal job-hunting tool for the Dutch tech market. A Python pipeline scrapes job listings daily, cross-references them against the IND recognised sponsor register, and saves them to CSV. A React frontend lets you browse and filter those listings, then track your applications — with status synced to Google Sheets.

---

## How it works

```
┌─────────────────────────────────────┐
│         Python pipeline             │  runs daily (GitHub Actions or local)
│                                     │
│  RemoteOK API  ──┐                  │
│  Arbeitnow API ──┼──▶ filter ──▶ IND check ──▶ data/jobs.csv
│  Greenhouse    ──┤    (keywords,              (deduped, append-only)
│  Career pages  ──┘     location,
│                         seniority)
└─────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────┐
│       React frontend                │  npm run dev
│                                     │
│  Job Browser  ──▶ /api/jobs (FastAPI reads CSV)
│  App Tracker  ──▶ Google Sheets "Applications" tab
└─────────────────────────────────────┘
```

---

## Quick start

### 1 — Run the pipeline

```bash
git clone https://github.com/YounesBoubbou/job-pipeline
cd job-pipeline
pip install -r requirements.txt

# Windows (fixes emoji output in terminal)
$env:PYTHONUTF8=1; python main.py

# Mac / Linux
python main.py
```

Results appear in `data/jobs.csv`. On first run the IND sponsor register (~12 000 companies) is automatically scraped and cached.

### 2 — Run the frontend

Open a second terminal:

```bash
cd frontend
npm install      # first time only
npm run dev
```

Then in a third terminal (from the repo root):

```bash
python api.py
```

Open **http://localhost:5173** in your browser.

> The frontend talks to the API via Vite's proxy — both must be running at the same time.

---

## Project structure

```
job-pipeline/
│
├── main.py               # Pipeline entry point — run this to scrape jobs
├── api.py                # FastAPI backend — serves the frontend
├── config.py             # All your settings — edit this
├── filters.py            # Keyword / location filtering logic
├── ind_checker.py        # IND sponsor register lookup (scrapes IND website)
├── output.py             # CSV + Google Sheets writer
│
├── scrapers/
│   ├── indeed.py         # RemoteOK + Arbeitnow APIs
│   └── company_pages.py  # Greenhouse API + HTML career page scraper
│
├── frontend/             # React 18 + Vite app
│   ├── src/
│   │   ├── pages/
│   │   │   ├── JobBrowser.jsx   # View 1 — browse & filter jobs
│   │   │   └── Tracker.jsx      # View 2 — track applications
│   │   ├── components/
│   │   │   ├── FilterBar.jsx
│   │   │   ├── JobCard.jsx
│   │   │   └── StatusDropdown.jsx
│   │   └── context/
│   │       └── TrackerContext.jsx  # Sheets write + localStorage fallback
│   └── package.json
│
├── data/                 # Auto-created on first run (gitignored)
│   ├── jobs.csv          # Running log of all found jobs
│   ├── seen_jobs.json    # Cache — prevents duplicate entries
│   └── ind_sponsors.csv  # Cached IND register
│
├── requirements.txt
└── .github/workflows/
    └── daily.yml         # Runs every weekday at 08:00 Amsterdam time
```

---

## Job sources

| Source | Type | Notes |
|---|---|---|
| **Adyen** | Greenhouse API | Dutch fintech — IND sponsor |
| **Catawiki** | Greenhouse API | Dutch auction platform — IND sponsor |
| **Booking.com** | HTML scraper | Dutch travel tech |
| **SURF** | HTML scraper | Dutch research & education network |
| **RemoteOK** | REST API | Remote tech jobs worldwide |
| **Arbeitnow** | REST API | EU remote + Netherlands-based roles |

### Adding a Greenhouse company

Find the company's Greenhouse slug (visible in their `greenhouse.io` careers URL) and add it to `GREENHOUSE_COMPANIES` in `scrapers/company_pages.py`:

```python
GREENHOUSE_COMPANIES = {
    "Adyen":      "adyen",
    "Catawiki":   "catawiki",
    "Your Co":    "your-co-slug",   # ← add here
}
```

### Adding an HTML career page

Add an entry to `COMPANY_PAGES` in `config.py`:

```python
{
    "name": "Your Company",
    "url":  "https://yourcompany.com/careers",
    "keyword_in_url": "yourcompany",
}
```

> Note: HTML scraping works for server-rendered pages. JS-heavy SPAs (React/Next.js career sites) won't return listings — use the Greenhouse API for those.

---

## Frontend filters

The Job Browser applies all active filters simultaneously.

| Filter | Default | What it does |
|---|---|---|
| **Role type** | All | Multi-select — show only jobs matching AI Engineer / Software Engineer / Data Scientist / Data Engineer / ML Engineer |
| **Entry-level only** | ON | Hides titles/descriptions containing: senior, lead, principal, staff, head of, manager, director, 5+ years, 7+ years, 10+ years |
| **No Dutch required** | ON | Hides listings where the description mentions: Dutch, Nederlands, fluent in Dutch, native Dutch |
| **IND sponsors only** | OFF | Shows only companies confirmed as IND recognised sponsors |
| **MSc-friendly** | OFF | Shows only listings mentioning: master, MSc, M.Sc |

---

## Application tracker

Click **"Mark as Applied"** on any job card to move it to the tracker (`/tracker`). Each application gets a status dropdown:

- Applied → Waiting for answer → Got interview → Rejected → Ghosted → Withdrawn

Status changes are written asynchronously to a **Google Sheets tab named "Applications"** (columns: `title`, `company`, `url`, `date_applied`, `status`).

If Sheets is unavailable, a yellow warning banner appears and data is saved to `localStorage` instead — nothing is lost.

---

## Google Sheets setup (optional)

Both the pipeline's job output and the tracker write to Google Sheets. To enable:

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a project → enable **Google Sheets API** and **Google Drive API**
3. Create a **Service Account** → download the JSON key → save as `credentials.json` in the repo root
4. Share your Google Sheet with the service account email (e.g. `pipeline@project.iam.gserviceaccount.com`)
5. In `config.py`:
   ```python
   SHEETS_ENABLED    = True
   SPREADSHEET_NAME  = "Job Pipeline"   # exact name of your sheet
   ```

The tracker will automatically create an **"Applications"** tab in that same spreadsheet.

---

## Automated daily runs (GitHub Actions)

The workflow in `.github/workflows/daily.yml` runs every weekday at **08:00 Amsterdam time**. It:

1. Runs `python main.py`
2. Uploads `data/jobs.csv` as a build artifact (downloadable from the Actions tab)

**To enable Google Sheets in Actions:**
- Add your `credentials.json` content as a repository secret named `GOOGLE_CREDENTIALS`
- Add a workflow step that writes the secret to `credentials.json` before running `main.py`

---

## CSV columns

| Column | Description |
|---|---|
| `date_found` | Date the listing was first seen |
| `title` | Job title |
| `company` | Company name |
| `location` | Location as listed by the source |
| `ind_sponsor` | `Yes` / `No` — IND recognised sponsor status |
| `source` | Source name (e.g. `Careers (Adyen)`, `RemoteOK`) |
| `url` | Direct link to the listing |
| `description_snippet` | First 300 characters of the job description |
| `status` | Pipeline status — `To Review` by default |

---

## IND sponsor register

On first run, `ind_checker.py` scrapes the [IND public register](https://ind.nl/en/public-register-recognised-sponsors/public-register-work) (~12 000 entries) and caches it in `data/ind_sponsors.csv`. Delete that file to force a refresh.

Matching is fuzzy substring-based — `"adyen"` matches `"adyen n.v."`. Occasional false positives can occur for very short company names; always verify on the [IND website](https://ind.nl/en/public-register-recognised-sponsors).

---

## Tech stack

| Layer | Tech |
|---|---|
| Pipeline | Python 3.10+, pandas, requests, BeautifulSoup, gspread |
| Backend | FastAPI + uvicorn |
| Frontend | React 18, Vite, Tailwind CSS (CDN) |
| Storage | CSV (local) + Google Sheets (optional) |
| Automation | GitHub Actions |
