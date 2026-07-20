# ─────────────────────────────────────────────
#  Job Pipeline — Configuration
#  Edit this file to customise your search
# ─────────────────────────────────────────────

# ── Search terms ──────────────────────────────
KEYWORDS_INCLUDE = [
    "junior", "graduate", "traineeship", "trainee",
    "data engineer", "data scientist", "ml engineer",
    "machine learning engineer", "software engineer",
    "backend engineer", "python developer", "medior",
    "data analyst", "analytics engineer",
]

KEYWORDS_EXCLUDE = [
    "senior", "lead", "principal", "staff", "head of",
    "manager", "director", "vp ", "5+ years", "7+ years",
    "10+ years", "c-level",
]

# ── Location filter ───────────────────────────
LOCATIONS = ["amsterdam", "netherlands", "nl", "hybrid", "remote"]

# ── Job board search queries ──────────────────
# Used by Werkzoeken.nl scraper — edit in scrapers/indeed.py → SEARCH_QUERIES

# ── Company career pages to watch ─────────────
# Note: Picnic and bol.com are fetched via their JSON APIs in the job boards scraper
# Add more companies here — needs a careers URL and a name
COMPANY_PAGES = [
    {
        "name": "Booking.com",
        "url": "https://jobs.booking.com/careers",
        "keyword_in_url": "booking",
    },
    {
        "name": "SURF",
        "url": "https://werkenbij.surf.nl",
        "keyword_in_url": "surf",
    },
    # Note: Catawiki, Adyen, TomTom are fetched via Greenhouse API
    # in scrapers/company_pages.py — no need to list them here.
]

# ── Google Sheets output ──────────────────────
# Set SHEETS_ENABLED = False to just output a local CSV instead
SHEETS_ENABLED = True           # credentials.json is set up and sheet is shared
SHEETS_CREDENTIALS_FILE = "credentials.json"   # service account JSON
SPREADSHEET_NAME = "Job Pipeline"              # exact name of your Sheet

# ── Local CSV fallback (always written) ───────
CSV_OUTPUT_PATH = "data/jobs.csv"

# ── Seen jobs cache (avoid duplicates) ────────
SEEN_CACHE_PATH = "data/seen_jobs.json"

# ── IND sponsor register ──────────────────────
# Downloaded automatically if not present
IND_REGISTER_PATH = "data/ind_sponsors.csv"
IND_REGISTER_URL  = (
    "https://ind.nl/en/documents/02-2022/publiekregister_erkende_referenten_en.xlsx"
)