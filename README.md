# Job Pipeline

A personal job-hunting tool for English-language, entry-level tech jobs in the Netherlands.

- The **pipeline** (a Python program) collects job openings every weekday morning, keeps the
  ones that pass the filters, labels each with whether the company is a visa sponsor, and
  appends the new ones to `data/jobs.csv`.
- The **web app** shows those jobs on the PC or on a phone at home, and tracks the ones you
  applied to.

"Sponsor" means a company on the IND public register of recognised sponsors: the Dutch
immigration service's list of employers allowed to hire on a skilled-migrant visa.

---

## How it works

```
 Windows scheduled task, weekdays 08:00  ──▶  run_daily.ps1  ──▶  python main.py
                                                                       │
   targets.csv (1,045 companies, main source) ──┐                      │
   RemoteOK + Arbeitnow (job-board sites)     ──┼──▶ filters ──▶ remove repeats ──▶ IND sponsor label
   Adyen, Catawiki, Booking.com, SURF pages   ──┘                      │
                                                                       ▼
                                  data/jobs.csv (new rows appended)  +  data/last_run.json (run summary)
                                                                       │
 start.ps1 ──▶ API (FastAPI, port 8000) reads both files ──▶ web app (React + Vite, port 5173)
                                                                       │
                       Tracker page ──▶ "Applications" tab of the Google Sheet (or browser storage)
```

Jobs are never written to the Google Sheet; it holds only the application tracker.

---

## Set up from scratch (Windows)

You need **Python 3.10** and **Node.js 18 or newer** (Node runs the web app).

```powershell
git clone https://github.com/YounesBoubbou/job-pipeline
cd job-pipeline

# A venv (virtual environment) is a private copy of Python for this project.
# start.ps1 and run_daily.ps1 expect it at venv\Scripts\python.exe.
python -m venv venv
venv\Scripts\python.exe -m pip install -r requirements.txt

# The web app's packages. start.ps1 also does this the first time.
cd frontend
npm install
cd ..
```

The pipeline needs nothing else. Only the application tracker needs `credentials.json`; see
[Google Sheet for the tracker](#google-sheet-for-the-tracker). Without it the tracker still
works, but saves to the browser only.

---

## Run the pipeline once

```powershell
$env:PYTHONUTF8=1; venv\Scripts\python.exe main.py
```

`PYTHONUTF8=1` stops the Windows console from crashing on symbols in job titles. A full run
takes about 5 minutes. It prints each board it tries, with the number of jobs it fetched and
kept, then the new jobs. On the first run it also downloads the IND sponsor register.

A board that fails (not found, time-out, network down) does not stop the run: it is listed in
the console and in `data/last_run.json`.

## Run it every weekday by itself

`run_daily.ps1` runs the pipeline once and saves everything it prints to a log file. A
Windows scheduled task (Windows' built-in timer for running programs) starts it every weekday
at 08:00. The command that registers the task, and the commands to check, test and remove it,
are in `docs/tasks.md` under "Waiting for Younes", item "Task 17". It runs only while you are
signed in (a locked screen is fine). If the PC is off or asleep at 08:00, it runs as soon as
the PC is back.

**Logs:** `logs\run_YYYY-MM-DD_HHmm.log`, one per scheduled run, ending with the exit code
(`0` = worked). Logs older than 30 days are deleted. A run started by hand with `main.py`
prints to the console only and writes no log.

To run the scheduled version by hand:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\run_daily.ps1
```

---

## Run the web app

From the repo root, one command starts the API and the frontend:

```powershell
powershell -ExecutionPolicy Bypass -File .\start.ps1
```

It runs `npm install` the first time (when `frontend\node_modules` is missing), then
prints two addresses: **http://localhost:5173** for this PC, and `http://<this PC's
Wi-Fi address>:5173` for a phone on the same Wi-Fi. Ctrl+C stops both halves.

> The frontend talks to the API via Vite's proxy (it passes the page's data requests on),
> so the API stays on this PC only (127.0.0.1:8000) and the phone needs just port 5173.

If the phone cannot open the page, Windows Firewall is probably blocking port 5173.
Allow Node.js when Windows asks, or run once in an administrator PowerShell:

```powershell
New-NetFirewallRule -DisplayName "Job pipeline web app (5173)" -Direction Inbound -Protocol TCP -LocalPort 5173 -Action Allow -Profile Private,Public
```

The phone works only on the home Wi-Fi, while the PC is on and `start.ps1` is running.

### What the app shows

- **Last run bar** (top): when the pipeline last finished and how many boards failed, read
  from `data/last_run.json`.
- **Jobs page** (`#/`): every job in `data/jobs.csv`, newest first. Each card shows title,
  company, location, date found, the sponsor label (`IND Yes` / `IND No`) and a link to the
  posting. Jobs added by the most recent run carry an amber **New** badge.
- **Filters** (behind a "Filters" button on the phone):

  | Filter | Default | What it does |
  |---|---|---|
  | Role type | none picked | Show only AI Engineer / Software Engineer / Data Scientist / Data Engineer / ML Engineer |
  | Entry-level only | on | Hides titles with senior, sr, lead, principal, staff, head of, manager or director, and jobs asking 3 or more years (e.g. 3+, 3-5, "at least three") |
  | No Dutch required | on | Hides jobs with a sentence requiring Dutch ("fluent in Dutch", "Dutch is a must", "Dutch (C1)", "Nederlands vereist"), unless it calls Dutch a plus |
  | IND sponsors | **on** | Shows only jobs labelled `Yes` |
  | MSc-friendly | off | Shows only jobs mentioning master, MSc or M.Sc |

  The text checks look at the title and the first 300 characters of the description.
- **Mark as Applied** on a card moves the job to the **Tracker page** (`#/tracker`) and hides
  it from the job list. There each application has a status: Applied, Waiting for answer,
  Got interview, Rejected, Ghosted, Withdrawn.

The card's "Tailor CV" and "Cover Letter" buttons are older work outside the MVP; they need
an `ANTHROPIC_API_KEY` in a `.env` file and are untested.

---

## Google Sheet for the tracker

The tracker saves to a tab named **Applications** (columns `title`, `company`, `url`,
`date_applied`, `status`) in a Google Sheet. When the Sheet cannot be reached, a yellow
banner appears and the tracker saves to the browser's own storage instead.

1. In the [Google Cloud Console](https://console.cloud.google.com), create a project and
   enable the **Google Sheets API** and **Google Drive API**.
2. Create a **service account** (a robot Google account for programs), download its JSON
   key, and save it as `credentials.json` in the repo root. It is gitignored.
3. Create a Google Sheet named **Job Pipeline** (or change `SPREADSHEET_NAME` in
   `config.py`) and share it with the service account's email address as an editor.

The Applications tab is created on first use.

---

## Data files

All in `data/`, created by the first run, and kept out of git.

| File | What it is |
|---|---|
| `jobs.csv` | Every job ever kept, one row each. New rows are only ever appended, never changed or removed: the app's **New** badge relies on that. |
| `seen_jobs.json` | Memory of saved jobs: each one's link and its "company\|title". A job matching either is not added again, even from another source. Delete it only together with `jobs.csv`, or old jobs come back as duplicates. |
| `last_run.json` | Summary of the latest run, rewritten every run (see below). |
| `ind_sponsors.csv` | Cached IND sponsor register. Downloaded again when older than 30 days; delete it to force a download. |
| `ats_map.json` | Results of `ats_resolver.py`'s register-wide search, on hold (ADR-0005). |
| `generated/`, `base_cv.tex` | CV and cover-letter generator files (outside the MVP). |

**`jobs.csv` columns:** `date_found`, `title`, `company`, `location`, `ind_sponsor` (`Yes`,
`No`, or `Unknown` when the register could not be loaded), `source` (for example `RemoteOK`,
`Careers (Adyen)`, `Target (workday)`), `url`, `description_snippet` (first 300 characters),
`status` (always `To Review`; the tracker keeps its own status).

**`last_run.json` fields:** `started_at`, `finished_at`, `duration_seconds`, `status`
(`completed`, or `crashed` with the reason in `error`), `jobs_added`, `boards` (each board
that answered: `name`, `source`, `fetched` = listings it returned, `kept` = listings that
passed the filters) and `failed` (each board that failed: `name`, `source`, `reason`).

---

## Where jobs come from

### The target list, `targets.csv` (main source)

A hand-reviewed list of 1,045 companies from the IND register, kept in git. Columns:

| Column | Meaning |
|---|---|
| `company` | Name shown in the app |
| `ind_registered_name` | Exact name on the IND register; used for the sponsor label |
| `other_ind_entities` | Other registered names of the same group (for reference) |
| `category` | Sector, for reference |
| `already_applied` | `yes` if applied there before (for reference; the app never hides a company) |
| `source` | Kind of careers site, see below |
| `token` | Which board on that site: a short name or a URL, see below |
| `board_status` | `auto`, `hand`, `review`, `none` or blank, see below |

**`board_status`** (ADR-0006):

| Value | Meaning | Fetched daily |
|---|---|---|
| `auto` | Found by `ats_resolver.py`; the board lists at least one Dutch job | yes |
| `hand` | Checked by hand: the right company | yes |
| `review` | A board was found but not confirmed to be the company's | no |
| `none` | No board found | no |
| blank | Not probed yet | no |

**`source` kinds.** An ATS (applicant tracking system) is the software a company's careers
site runs on. Each kind has its own fetcher in `scrapers/targets.py`:

| `source` | Token example | Notes |
|---|---|---|
| `greenhouse` | `bolcom` | |
| `lever` | `palantir` | |
| `lever_eu` | `tomtom` | Lever's EU servers (TomTom) |
| `ashby` | `prosus` | |
| `recruitee` | `effectory` | |
| `smartrecruiters` | `picnic` | |
| `workday` | `https://adobe.wd5.myworkdayjobs.com/external_experienced` | Asks for Netherlands jobs only (ADR-0008) |
| `jibe` | `https://jobs.booking.com` | Booking.com; Netherlands jobs only (ADR-0009) |
| `getnoticed` | `https://www.werkenbijabnamro.nl` | ABN AMRO; Netherlands jobs only (ADR-0009) |
| `eightfold` | `https://portal.careers.hsbc.com/careers?domain=hsbc.com` | HSBC, DSM-Firmenich (ADR-0010) |
| `phenom` | `https://careers.akzonobel.com/gb/en` | AkzoNobel (ADR-0010) |
| `heineken` | `https://careers.theheinekencompany.com` | Heineken's own site, read as HTML; no descriptions (ADR-0010) |

For the boards that ask for Netherlands jobs only, `fetched` in the run summary counts Dutch
listings, not every listing worldwide.

**To add a company:** fill in `source` and `token`, set `board_status` to `hand` after
checking on the board that it is the right company, and put its exact IND name in
`ind_registered_name`. To let the program look instead, leave `board_status` blank and run
`venv\Scripts\python.exe ats_resolver.py targets`: it guesses the board on Greenhouse, Lever,
Ashby, Recruitee and SmartRecruiters and fills `source`, `token` and `board_status` (`auto`,
`review` or `none`; ADR-0006). The other kinds are added by hand.

### Other sources

| Source | Where it is set | Notes |
|---|---|---|
| RemoteOK | `scrapers/indeed.py` | Public API, remote tech jobs worldwide |
| Arbeitnow | `scrapers/indeed.py` | Public API, EU and Dutch jobs |
| Adyen, Catawiki | `GREENHOUSE_COMPANIES` in `scrapers/company_pages.py` | Greenhouse boards |
| Booking.com, SURF | `COMPANY_PAGES` in `config.py` | Generic HTML scraper; finds little on sites built with JavaScript |

When the same job comes from the target list and one of these, the target-list copy is kept.

### Filters

A job is kept only if it passes all five rules in `filters.py` (word lists in `config.py`):
a tech word in the title; no seniority word in the title and no 3+ years asked; a Dutch
place in the location, or plain "Remote"; not written mostly in Dutch; and no sentence that
requires Dutch ("fluent in Dutch", "Dutch is a must") without calling it a plus or nice to have.

### Sponsor label

`ind_checker.py` downloads the [IND public register](https://ind.nl/en/public-register-recognised-sponsors/public-register-work)
and matches names exactly after removing endings like "B.V." and "N.V.". Target-list jobs
are matched on their row's `ind_registered_name`; other jobs on the company name as given.

---

## Tests

```powershell
venv\Scripts\python.exe -m pytest -q
```

Tests use fake data only: they never call the Google Sheet or a real job board. GitHub runs
the same tests on every push (`.github/workflows/daily.yml`, named "Tests"). It does not run
the pipeline.

---

## Project structure

```
job-pipeline/
├── main.py                  # Pipeline: run this to collect jobs
├── config.py                # Settings: filter word lists, file paths, Sheet name
├── filters.py               # The four filter rules
├── ind_checker.py           # IND register download and sponsor label
├── output.py                # Removes repeats; writes jobs.csv and last_run.json
├── scrapers/
│   ├── targets.py           # Fetchers for targets.csv, one per source kind
│   ├── indeed.py            # RemoteOK + Arbeitnow (the name is historical)
│   └── company_pages.py     # Adyen, Catawiki (Greenhouse) + HTML career pages
├── ats_resolver.py          # Finds boards for targets.csv rows (run by hand)
├── api.py                   # FastAPI backend for the web app
├── cv_generator.py, cover_letter_generator.py   # Outside the MVP, untested
├── targets.csv              # The target list
├── run_daily.ps1            # Runs the pipeline with a log (for the scheduled task)
├── start.ps1                # Starts the web app
├── frontend/                # React 18 + Vite web app
│   └── src/
│       ├── App.jsx                     # Page frame, navigation, last run bar
│       ├── pages/JobBrowser.jsx        # Jobs page
│       ├── pages/Tracker.jsx           # Tracker page
│       ├── components/                 # FilterBar, JobCard, StatusDropdown
│       ├── constants/filters.js        # Web app filter word lists and defaults
│       └── context/TrackerContext.jsx  # Tracker data: Sheet, with browser fallback
├── tests/                   # pytest tests
├── docs/
│   ├── requirements.md      # What the MVP must do
│   ├── tasks.md             # Work list, and what is waiting for Younes
│   ├── adr/                 # Design decisions and their reasons
│   └── screenshots/         # The app at phone and desktop width
├── data/                    # Created by the first run (gitignored)
└── logs/                    # Scheduled-run logs (gitignored)
```

---

## Tech stack

| Part | Tech |
|---|---|
| Pipeline | Python 3.10, requests, BeautifulSoup, pandas |
| API | FastAPI + uvicorn |
| Web app | React 18, Vite 5, Tailwind CSS (loaded from a CDN) |
| Storage | `data/jobs.csv`; tracker in Google Sheets (gspread) |
| Daily run | Windows scheduled task + `run_daily.ps1` |
| Tests | pytest, run on every push by GitHub Actions |
