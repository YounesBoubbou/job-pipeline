# ─────────────────────────────────────────────
#  Job Pipeline — Configuration
#  Edit this file to customise your search
# ─────────────────────────────────────────────

from dotenv import load_dotenv

load_dotenv()  # loads ANTHROPIC_API_KEY (and any other secrets) from .env, if present

# ── Search terms ──────────────────────────────
# Whole words in the title. "Junior" alone isn't enough: it let in nurses and marketers.
KEYWORDS_INCLUDE = [
    "engineer", "engineering", "developer", "programmer", "software",
    "data", "analytics", "scientist", "machine learning", "ml", "ai", "genai",
    "llm", "llms", "algorithms", "quant", "quantitative", "devops", "sre",
    "backend", "back end", "frontend", "front end", "fullstack", "full stack",
    "python", "java", "php",
    # Entry-level routes that often have no tech word in the title
    "graduate", "internship",
]

# Checked against the title only: descriptions say things like "report to your manager"
KEYWORDS_EXCLUDE = [
    "senior", "sr", "lead", "principal", "staff", "head of",
    "manager", "director", "vp ", "c-level",
    # Titles with an include word that still aren't software or data jobs
    "sales", "presales", "account", "business developer", "writer",
    "mechanical", "electrical", "electronic", "geotechnical", "material", "wind", "aircraft",
]

# Checked against the title and description, on top of the "3 or more years" pattern in filters.py
EXPERIENCE_EXCLUDE = ["3+ years", "4+ years", "5+ years", "7+ years", "10+ years"]

# "Dutch" meant as the language, not as an adjective: it ends the sentence or is followed by
# words like "language", "and English", "is", "written", "skills". So "fluent in Dutch" and
# "fluent Dutch, written and spoken" count, but "knowledge of the Dutch market" does not.
_DUTCH_LANGUAGE = (
    r"dutch(?=\s*(?:$|[,().!?;:]|(?:language|and\s+english|&\s*english|is|are|written|spoken|both"
    r"|fluently|skills|speakers?|at|as|level|required|mandatory|essential)\b))"
)

# Ways a posting says Dutch is required; regex pieces, matched per sentence on lowercase text,
# with "-" turned into " " and the ":" after "Dutch", "English" or "Language(s)" dropped.
# Bare "Dutch speaking" is left out on purpose, so "our Dutch-speaking customers" is kept.
DUTCH_REQUIRED = [
    r"(?:fluent|fluency|proficient|proficiency|command|knowledge|mastery)\s+(?:in|of)\s+(?:(?:both|the|english|and|&|,)\s*)*" + _DUTCH_LANGUAGE,
    r"(?:fluent|native|excellent|proficient|business level|native level)\s+" + _DUTCH_LANGUAGE,
    # "you speak Dutch", "must speak and write Dutch"; not "we speak Dutch" or "our team speaks Dutch"
    r"(?<!\bwe )(?<!team )\b(?:speak|write|master)\s+(?:(?:and|&|write|fluent|the)\s+)*" + _DUTCH_LANGUAGE,
    r"skills\s+in\s+(?:(?:both|english|and|&|,)\s*)*" + _DUTCH_LANGUAGE,
    r"dutch\s+(?:and|&)\s+english\s+(?:language\s+)?skills",
    r"dutch\s*(?:at\s+)?\(?\s*[abc][12]\b",   # "Dutch (C1)", "Dutch at B2 level"
    # language lines: "Dutch: fluent", "Dutch (native) and English", "Dutch and English (fluent)"
    r"dutch\s*(?:(?:and|&)\s*english\s*)?[:(]?\s*(?:fluent|native)\b",
    r"dutch\s+(?:native\s+)?speaker\b|dutch\s+(?:language\s+)?(?:skills|proficiency|fluency)",
    r"(?:english\s+(?:and|&)\s+)?dutch(?:\s+(?:and|&)\s+english)?\s+(?:(?:speaking|language|skills)\s+)*(?:is|are)\s+(?:a\s+)?(?:must|required|mandatory|essential|requirement)",
    r"dutch\s+(?:required|mandatory|essential)",
    r"nederlands\w*\s+(?:is\s+)?(?:vereist|verplicht)|vloeiend\s+nederlands|nederlandstalig",
]

# Whole words that make a Dutch mention only a wish, so the job is kept. They count when they are in
# the comma-separated part of the sentence that names Dutch, or in the heading above it ("Nice to have").
DUTCH_OPTIONAL = [
    "plus", "pluses", "nice to have", "nice to haves", "advantage", "advantageous", "bonus",
    "preferred", "preferable", "preferably", "ideally", "desirable", "beneficial", "helpful",
    "optional", "welcome", "asset", "or not", "not required", "not a requirement",
    "not necessary", "not needed", "not mandatory", "not a must", "not essential",
    "not a prerequisite", "don't need", "do not need", "no need", "don't have to",
    "do not have to", "don't require", "does not require", "no dutch", "pluspunt",
]

# ── Location filter ───────────────────────────
LOCATIONS = [
    "netherlands", "nederland", "nl", "holland", "hybrid", "remote",
    "amsterdam", "amstelveen", "diemen", "hoofddorp", "schiphol", "haarlem", "almere", "hilversum",
    "rotterdam", "den haag", "the hague", "gravenhage", "delft", "leiden", "utrecht", "amersfoort",
    "eindhoven", "veldhoven", "hertogenbosch", "den bosch", "tilburg", "breda", "nijmegen", "arnhem",
    "groningen", "enschede", "zwolle", "deventer", "maastricht", "wageningen",
]

# ── Company career pages to watch ─────────────
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
    # Note: Catawiki and Adyen are fetched via the Greenhouse API
    # in scrapers/company_pages.py — no need to list them here.
]

# ── Google Sheets (application tracker only) ──
# Used by api.py for the "Applications" tab. The pipeline never writes jobs here.
SHEETS_CREDENTIALS_FILE = "credentials.json"   # service account JSON
SPREADSHEET_NAME = "Job Pipeline"              # exact name of your Sheet

# ── Job list (the only place jobs are written) ─
CSV_OUTPUT_PATH = "data/jobs.csv"

# ── Run summary (P1, P5) ──────────────────────
# Rewritten after every run: times, jobs added, boards tried and boards that failed
RUN_SUMMARY_PATH = "data/last_run.json"

# ── Seen jobs cache (avoid duplicates) ────────
SEEN_CACHE_PATH = "data/seen_jobs.json"

# ── IND sponsor register ──────────────────────
# Scraped from the IND web page by ind_checker.py and cached here; refreshed after 30 days
IND_REGISTER_PATH = "data/ind_sponsors.csv"

# ── ATS resolution (sponsor → careers board) ──
# Built incrementally by ats_resolver.py — see ADR-0003
ATS_MAP_PATH      = "data/ats_map.json"
ATS_BATCH_SIZE    = 150     # sponsor names probed per run (~25 min at 1 req/s)

# ── Tailored CV generation ────────────────────
# Requires ANTHROPIC_API_KEY set in your environment
BASE_CV_PATH     = "data/base_cv.tex"
GENERATED_CV_DIR = "data/generated"