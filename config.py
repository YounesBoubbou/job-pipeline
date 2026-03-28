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

# ── Indeed RSS searches ───────────────────────
# Each entry is one RSS feed (one search query + location)
INDEED_RSS_FEEDS = [
    "https://www.indeed.com/rss?q=junior+data+engineer&l=Amsterdam%2C+Netherlands&sort=date",
    "https://www.indeed.com/rss?q=graduate+software+engineer&l=Amsterdam%2C+Netherlands&sort=date",
    "https://www.indeed.com/rss?q=junior+machine+learning+engineer&l=Netherlands&sort=date",
    "https://www.indeed.com/rss?q=junior+python+developer&l=Amsterdam%2C+Netherlands&sort=date",
    "https://www.indeed.com/rss?q=data+engineer+trainee&l=Netherlands&sort=date",
    "https://www.indeed.com/rss?q=graduate+data+scientist&l=Netherlands&sort=date",
]

# ── Company career pages to watch ─────────────
# Add more as you like — just needs a careers URL and a name
COMPANY_PAGES = [
    {
        "name": "Picnic",
        "url": "https://jobs.picnic.app/en/vacancies",
        "keyword_in_url": "picnic",
    },
    {
        "name": "bol.com",
        "url": "https://careers.bol.com/en/jobs",
        "keyword_in_url": "bol.com",
    },
    {
        "name": "Booking.com",
        "url": "https://jobs.booking.com/careers",
        "keyword_in_url": "booking",
    },
    {
        "name": "RIPE NCC",
        "url": "https://www.ripe.net/about-us/careers/",
        "keyword_in_url": "ripe",
    },
]

# ── Google Sheets output ──────────────────────
# Set SHEETS_ENABLED = False to just output a local CSV instead
SHEETS_ENABLED = False          # flip to True once you add credentials
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
