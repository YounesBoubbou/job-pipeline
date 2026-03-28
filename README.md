# Job Discovery Pipeline

Automated job discovery for the Dutch tech market. Scrapes Indeed RSS feeds and
company career pages daily, filters by role seniority and keywords, cross-references
against the IND recognized sponsor register, and outputs a deduplicated CSV (or Google Sheet).

---

## Quick Start (local)

```bash
git clone <your-repo>
cd job-pipeline
pip install -r requirements.txt
python main.py
```

Results appear in `data/jobs.csv` and are printed to the terminal.

---

## Project Structure

```
job-pipeline/
├── main.py                  # Entry point — run this
├── config.py                # All your settings (edit this)
├── filters.py               # Keyword/location filtering logic
├── ind_checker.py           # IND sponsor register lookup
├── output.py                # CSV + Google Sheets writer
├── scrapers/
│   ├── indeed.py            # Indeed RSS scraper
│   └── company_pages.py     # Company careers page scraper
├── data/
│   ├── jobs.csv             # Running log of all found jobs
│   ├── seen_jobs.json       # Cache to avoid duplicate alerts
│   └── ind_sponsors.csv     # Cached IND register (auto-downloaded)
├── requirements.txt
└── .github/workflows/
    └── daily.yml            # GitHub Actions — runs every weekday at 8am
```

---

## Customising Your Search

Open `config.py` and edit:

- `KEYWORDS_INCLUDE` — role types you want to surface
- `KEYWORDS_EXCLUDE` — titles that disqualify a listing (senior, lead, etc.)
- `INDEED_RSS_FEEDS` — add/remove search queries (see below for URL format)
- `COMPANY_PAGES` — add any company whose careers page you want watched

### Adding an Indeed RSS feed

Go to `indeed.com`, run a search, then append `/rss` to the URL and add it to `INDEED_RSS_FEEDS`. Example:

```
https://www.indeed.com/rss?q=junior+backend+engineer&l=Amsterdam&sort=date
```

### Adding a company careers page

```python
{
    "name": "Your Company",
    "url": "https://company.com/careers",
    "keyword_in_url": "company",
}
```

---

## Automated Daily Runs (GitHub Actions)

1. Push the repo to GitHub (can be private)
2. Go to **Actions** tab — the `Daily Job Pipeline` workflow runs every weekday at 08:00 Amsterdam time
3. Download the `jobs-{run_id}` artifact from each run to get the day's CSV

No server required.

---

## Google Sheets Integration (optional)

To write results directly to a Google Sheet instead of (or in addition to) CSV:

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a project → enable **Google Sheets API** and **Google Drive API**
3. Create a **Service Account** → download the JSON key → save as `credentials.json` in the project root
4. Share your Google Sheet with the service account email (e.g. `pipeline@project.iam.gserviceaccount.com`)
5. In `config.py`, set:
   ```python
   SHEETS_ENABLED = True
   SPREADSHEET_NAME = "Job Pipeline"   # exact name of your sheet
   ```
6. For GitHub Actions, store the JSON content as a secret named `GOOGLE_CREDENTIALS` and add a step to write it to `credentials.json` before running.

---

## Reading the Output CSV

| Column | Description |
|---|---|
| `date_found` | Date the listing was first seen |
| `title` | Job title |
| `company` | Company name |
| `location` | Location as listed |
| `ind_sponsor` | Yes / No / Unknown — IND recognized sponsor status |
| `source` | Indeed or Careers (Company Name) |
| `url` | Direct link to the listing |
| `description_snippet` | First 300 chars of the job description (Indeed only) |
| `status` | Your manual status — update to: Applied / Interviewing / Rejected / Pass |

---

## IND Sponsor Register

The register is downloaded automatically from the IND public website on first run and cached in `data/ind_sponsors.csv`. It refreshes when the cache file is deleted or when running with `--refresh-ind` (planned feature).

The matching is fuzzy substring-based — if the company name appears inside a registered entity name or vice versa, it counts as a match. This means occasional false positives for very short names; always verify on the [IND website](https://ind.nl/en/public-register-recognised-sponsors).
