"""
coverage_scan.py — Find each target company's website, careers page and job-board system
(ADR-0013; docs/requirements-coverage.md, phase A).

Fills five columns of targets.csv: website, careers_url, ats_seen, ats_evidence, scan_note.
No other column is ever changed. targets.csv is the only state: a row is done once its
scan_note is filled, and the file is saved after every company, so a killed run continues
where it stopped. Don't have targets.csv open in Excel during a run (saving would fail).

    python coverage_scan.py                     # every row not scanned yet
    python coverage_scan.py 50                  # the next 50
    python coverage_scan.py --company "Mollie"  # rescan the named rows, even if done
    python coverage_scan.py --known-websites    # rows with a website but no ats_seen (A-4)
    python coverage_scan.py --retry-no-answer   # rows whose note starts with "no answer:"

A row that already has a website is not re-guessed; clear the cell to force a guess.
"""

import argparse
import csv
import json
import os
import re
import socket
import sys
import time
import unicodedata
from urllib import robotparser
from urllib.parse import urljoin, urlsplit

import requests
from bs4 import BeautifulSoup

from ind_checker import normalise_name
from scrapers.targets import FETCHERS, HEADERS, TARGETS_PATH, load_targets

NEW_COLUMNS = ["website", "careers_url", "ats_seen", "ats_evidence", "scan_note"]
MAX_REQUESTS_PER_SITE = 6   # per company, robots.txt and redirect hops included (A6)
MIN_GAP = 1.0               # seconds between requests to the same site (A6)
MAX_CRAWL_DELAY = 30        # a longer robots.txt Crawl-delay is not waited out: blocked
TIMEOUT = 15
MAX_BYTES = 2_000_000
MAX_HOPS = 5
MAX_GUESSES = 6             # guessed domains loaded per company (A2)
UA = HEADERS["User-Agent"]


class Blocked(Exception):
    """robots.txt refuses the page, or can't be read."""


class NoAnswer(Exception):
    """Timeout or connection error."""


class LimitReached(Exception):
    """The company's request limit for this site is used up."""


# Kept for the whole run: robots.txt per origin, and the last request time and crawl
# delay per site, so sites shared by several companies are never hit faster.
_robots = {}
_last_request = {}
_crawl_delay = {}


class Scan:
    """Request counts for one company."""

    def __init__(self):
        self.used = {}      # site -> requests made to it
        self.requests = 0


class Page:
    def __init__(self, url, status=None, html="", redirects=(), ats_url="", wall=""):
        self.url, self.status, self.html = url, status, html
        self.redirects = list(redirects)  # every Location followed on the way to url
        self.ats_url = ats_url            # set when a link or redirect led to a job system
        self.wall = wall                  # why the page refused us ("HTTP 403", "bot wall …")


# ---------------------------------------------------------------- HTTP layer

def site_key(host: str) -> str:
    """The registrable domain: 'jobs.funda.nl' -> 'funda.nl', 'www.bbc.co.uk' -> 'bbc.co.uk'."""
    labels = (host or "").lower().rstrip(".").split(".")
    if len(labels) >= 3 and labels[-2] in ("co", "com", "ac", "org") and len(labels[-1]) == 2:
        return ".".join(labels[-3:])
    return ".".join(labels[-2:])


def _host(url: str) -> str:
    return (urlsplit(url).hostname or "").lower()


def _origin(url: str) -> str:
    p = urlsplit(url)
    return f"{p.scheme}://{p.netloc}"


def _get(url: str, scan: Scan):
    """One GET, within the site's request limit and spacing. Returns (status, headers, text)."""
    key = site_key(_host(url))
    if scan.used.get(key, 0) >= MAX_REQUESTS_PER_SITE:
        raise LimitReached(key)
    gap = max(MIN_GAP, _crawl_delay.get(key, 0))
    if key in _last_request:
        wait = _last_request[key] + gap - time.monotonic()
        if wait > 0:
            time.sleep(wait)
    scan.used[key] = scan.used.get(key, 0) + 1
    scan.requests += 1
    try:
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT, allow_redirects=False, stream=True)
        try:
            text = _read(r)
        finally:
            r.close()
    except (requests.RequestException, OSError, ValueError) as e:
        raise NoAnswer(f"{type(e).__name__} on {_host(url)}")
    finally:
        _last_request[key] = time.monotonic()
    return r.status_code, r.headers, text


def _read(r) -> str:
    chunks, size = [], 0
    for chunk in r.iter_content(65536):
        chunks.append(chunk)
        size += len(chunk)
        if size >= MAX_BYTES:
            break
    raw = b"".join(chunks)[:MAX_BYTES]
    # requests assumes Latin-1 for text/html without a charset; most pages are UTF-8.
    enc = r.encoding if r.encoding and "charset" in r.headers.get("Content-Type", "").lower() else "utf-8"
    try:
        return raw.decode(enc, errors="replace")
    except LookupError:
        return raw.decode("utf-8", errors="replace")


def _robots_for(origin: str, scan: Scan):
    """A RobotFileParser for the origin, or a reason string if the site counts as blocked.

    Fetched with our own User-Agent: RobotFileParser.read() sends Python's, which many
    sites refuse, and they would then look like "disallow all" (ADR-0013).
    """
    if origin in _robots:
        return _robots[origin]
    url = origin + "/robots.txt"
    for _ in range(MAX_HOPS + 1):
        status, headers, text = _get(url, scan)
        if status in (301, 302, 303, 307, 308) and headers.get("Location"):
            url = urljoin(url, headers["Location"])
            if is_vendor_url(url):  # never requested; treated as no robots.txt, and the
                status = 404        # page itself then redirects to the job system as evidence
                break
            continue
        break
    rp = robotparser.RobotFileParser()
    if status == 200:
        rp.parse(text.splitlines())
    elif status in (401, 403):
        rp = f"robots.txt refused (HTTP {status})"
    elif status == 429 or status >= 500:
        rp = f"robots.txt unreachable (HTTP {status})"
    else:
        rp.parse([])  # no robots.txt: everything allowed
    if not isinstance(rp, str):
        delay = rp.crawl_delay(UA)
        if delay:
            if float(delay) > MAX_CRAWL_DELAY:
                rp = f"robots.txt crawl-delay {delay}s"
            else:
                key = site_key(urlsplit(origin).hostname)
                _crawl_delay[key] = max(_crawl_delay.get(key, 0), float(delay))
    _robots[origin] = rp
    final = _origin(url)
    if final != origin and site_key(urlsplit(final).hostname) == site_key(urlsplit(origin).hostname):
        _robots.setdefault(final, rp)  # sendcloud.com/robots.txt -> www.sendcloud.com: one request, not two
    return rp


def _check_robots(url: str, scan: Scan):
    rp = _robots_for(_origin(url), scan)
    if isinstance(rp, str):
        raise Blocked(rp)
    if not rp.can_fetch(UA, url):
        raise Blocked(f"robots.txt disallows {urlsplit(url).path or '/'}")


def _title(html: str) -> str:
    m = re.search(r"<title[^>]*>(.*?)</title>", html, re.I | re.S)
    return m.group(1).strip() if m else ""


WALL_STATUSES = (401, 403, 429, 503)
WALL_PHRASES = ("just a moment", "attention required", "access denied", "access blocked",
                "toegang geblokkeerd", "je bent bijna op de pagina",
                "captcha", "verify you are human", "cf-chl", "datadome", "incapsula")


def _wall(status: int, html: str) -> str:
    if status in WALL_STATUSES:
        return f"HTTP {status}"
    title = _title(html).lower()
    # The body is only searched when it is small (a bot wall is a short page), and without
    # script tags and the word "recaptcha": normal pages load Google's reCAPTCHA for a form.
    body = html.lower() if len(html) < 20000 else ""
    body = re.sub(r"<script[^>]*>|recaptcha", " ", body)
    for phrase in WALL_PHRASES:
        if phrase in title or phrase in body:
            return f"bot wall ({phrase})"
    return ""


def _fetch(url: str, scan: Scan) -> Page:
    """GET a page politely, following redirects by hand. A link or redirect to a job
    system's host is recorded, never requested."""
    redirects = []
    for _ in range(MAX_HOPS + 1):
        if urlsplit(url).scheme not in ("http", "https"):
            return Page(url, None, "", redirects, wall="not a web address")
        if is_vendor_url(url):
            return Page(url, None, "", redirects, ats_url=url)
        _check_robots(url, scan)
        status, headers, text = _get(url, scan)
        if status in (301, 302, 303, 307, 308) and headers.get("Location"):
            url = urljoin(url, headers["Location"])
            redirects.append(url)
            continue
        return Page(url, status, text, redirects, wall=_wall(status, text))
    return Page(url, None, "", redirects, wall="too many redirects")


# ---------------------------------------------------------------- detection (A4)

# Hosts of job systems. Never requested: an address on one of them is only evidence.
VENDOR_HOST = re.compile(
    r"(?:^|\.)(?:greenhouse\.io|lever\.co|ashbyhq\.com|smartrecruiters\.com|recruitee\.com"
    r"|myworkdayjobs\.com|myworkdaysite\.com|eightfold\.ai|teamtailor\.com|teamtailor-cdn\.com"
    r"|personio\.de|personio\.com|successfactors\.com|successfactors\.eu|jobs\.sap\.com"
    r"|[\w-]+\.homerun\.co|icims\.com|workable\.com|bamboohr\.com|oraclecloud\.com|taleo\.net"
    r"|jobvite\.com|breezy\.hr|join\.com|pinpointhq\.com|afasinsite\.nl|otys\.nl|otys\.com"
    r"|carerix\.com|carerix\.net|connexys\.nl|connexys\.com|cxsrecruit\.\w+|emply\.com|emply\.net"
    r"|hireserve\.com|hireservecloud\.com|jibeapply\.com|jibecdn\.com|phenompeople\.com"
    r"|careers\.theheinekencompany\.com)$")


def is_vendor_url(url: str) -> bool:
    return bool(VENDOR_HOST.search(_host(url)))


_SUB = r"//(?:[\w-]+\.)*"  # any subdomains

# (kind, pattern on a full address). Order does not matter; priority is decided in _choose.
URL_PATTERNS = [
    ("greenhouse", r"//(?:boards|job-boards)(?:\.eu)?\.greenhouse\.io/|//boards-api\.greenhouse\.io/v1/boards/|[?&]gh_jid=\d"),
    ("recruitee", r"//(?!(?:www|app|api|cdn|careers|blog)\.)[a-z0-9-]+\.recruitee\.com"),
    ("lever", r"//(?:jobs|api)\.lever\.co/"),
    ("lever_eu", r"//(?:jobs|api)\.eu\.lever\.co/"),
    ("ashby", r"//jobs\.ashbyhq\.com/|//api\.ashbyhq\.com/posting-api/job-board/"),
    ("smartrecruiters", r"//(?:jobs|careers)\.smartrecruiters\.com/[\w-]|//(?:www\.)?smartrecruiters\.com/[A-Z][\w-]+/"
                        r"|//api\.smartrecruiters\.com/v1/companies/[\w-]"),
    ("workday", r"//[\w-]+\.(?:wd\d+\.)?myworkdayjobs\.com|myworkdaysite\.com"),
    ("phenom", r"//cdn\.phenompeople\.com/CareerConnectResources/"),
    ("jibe", r"jibecdn\.com|jibeapply\.com"),
    ("eightfold", r"//[\w-]+\.eightfold\.ai|^https?://[^/]+/careers\?(?:[^#]*&)?(?:domain=[\w.-]+|pid=\d)"),
    ("heineken", r"//careers\.theheinekencompany\.com"),
    ("Teamtailor", r"teamtailor-cdn\.com|//[\w-]+\.teamtailor\.com"),
    ("Personio", r"//[\w-]+\.jobs\.personio\.(?:de|com)"),
    ("SAP SuccessFactors", r"successfactors\.(?:com|eu)|//jobs\.sap\.com"),
    ("Homerun", r"//(?!www\.)[\w-]+\.homerun\.co\b"),
    ("iCIMS", r"//careers-[\w-]+\.icims\.com|//[\w-]+\.icims\.com/jobs"),
    ("Workable", r"//apply\.workable\.com/[\w-]"),
    ("BambooHR", r"//[\w-]+\.bamboohr\.com/(?:careers|jobs)"),
    ("Oracle Recruiting", r"\.oraclecloud\.com/hcmUI/CandidateExperience"),
    ("Taleo", r"//[\w-]+\.taleo\.net"),
    ("Jobvite", r"//jobs\.jobvite\.com/"),
    ("Breezy", r"//[\w-]+\.breezy\.hr"),
    ("JOIN", r"//join\.com/companies/"),
    ("Pinpoint", r"//[\w-]+\.pinpointhq\.com"),
    ("AFAS", r"//[\w-]+\.afasinsite\.nl"),  # never the bare word: it shows up in customer-logo strips
    ("OTYS", _SUB + r"otys\.(?:nl|com)\b"),
    ("Carerix", _SUB + r"carerix\.(?:com|net)\b"),
    ("Connexys", _SUB + r"connexys\.(?:nl|com)\b|cxsrecruit"),
    ("Emply", _SUB + r"emply\.(?:com|net)\b"),
    ("Hireserve", _SUB + r"hireserve(?:cloud)?\.com\b"),
]
URL_PATTERNS = [(kind, re.compile(p)) for kind, p in URL_PATTERNS]

DIRECT = ["workday", "greenhouse", "lever", "lever_eu", "ashby", "smartrecruiters", "recruitee"]
FRONT = ["jibe", "phenom", "eightfold", "getnoticed"]
PAGE_LEVEL = ("jibe", "phenom")  # the token comes from the careers page's own address
# Patterns not yet seen on a real company page (ADR-0013); such rows are noted.
UNCONFIRMED = {"lever_eu", "getnoticed", "eightfold", "Homerun", "iCIMS", "Workable", "BambooHR",
               "Oracle Recruiting", "Taleo", "Jobvite", "Breezy", "JOIN", "Pinpoint", "AFAS", "OTYS",
               "Carerix", "Connexys", "Emply", "Hireserve"}

URL_IN_TEXT = re.compile(r"(?:https?:)?//[\w-]+(?:\.[\w-]+)+[^\s\"'<>\\)]*", re.I)


def _soup(html: str):
    return BeautifulSoup(html or "", "html.parser")


def _page_urls(page_url, html, redirects, soup):
    """Every address on the page: its own, redirects, attributes, and those inside its data."""
    urls = [page_url] + list(redirects)
    if html:
        for tag in soup.find_all(True):
            for attr in ("href", "src", "action", "data-src"):
                v = tag.get(attr)
                if isinstance(v, str) and v.strip():
                    urls.append(urljoin(page_url, v.strip()))
        text = html.replace("\\/", "/").replace("&amp;", "&")
        urls += ["https:" + u if u.startswith("//") else u for u in URL_IN_TEXT.findall(text)]
    return list(dict.fromkeys(urls))


def detect(page_url: str, html: str = "", redirects=(), soup=None) -> dict:
    """The systems a page shows: {kind: [evidence, ...]}, in the order first seen."""
    soup = soup if soup is not None else _soup(html)
    hits = {}
    for u in _page_urls(page_url, html, redirects, soup):
        for kind, pattern in URL_PATTERNS:
            if pattern.search(u):
                hits.setdefault(kind, []).append(f"{page_url} | {u}" if kind in PAGE_LEVEL else u)
    if html:
        text = html.replace("&quot;", '"')
        sub = re.search(r'"subdomain"\s*:\s*"([a-z0-9-]+)"', text)
        if sub and re.search(r"atsHost.{0,40}recruitee\.com", text, re.S):
            hits.setdefault("recruitee", []).append(f'{page_url} | "subdomain":"{sub.group(1)}"')
        if "logo getnoticed" in html.lower() and re.search(r"/vacature/\d+/|/api/vacancy", html):
            hits.setdefault("getnoticed", []).append(f"{page_url} | logo Getnoticed")
    return hits


def token_from_evidence(kind: str, evidence: str) -> str:
    """The `token` targets.csv would hold for this kind, read from the evidence ('' if none)."""
    page, _, snippet = evidence.partition(" | ")
    if kind == "greenhouse":
        m = (re.search(r"(?:boards|job-boards)(?:\.eu)?\.greenhouse\.io/(?:embed/job_(?:board|app)(?:/js)?\?for=)?([\w-]+)", evidence)
             or re.search(r"boards-api\.greenhouse\.io/v1/boards/([\w-]+)", evidence))
        return m.group(1) if m and m.group(1) != "embed" else ""
    if kind == "recruitee":
        m = (re.search(r"//(?!(?:www|app|api|cdn|careers|blog)\.)([a-z0-9-]+)\.recruitee\.com", evidence)
             or re.search(r'"subdomain"\s*:\s*"([a-z0-9-]+)"', evidence))
        return m.group(1) if m else ""
    if kind in ("lever", "lever_eu"):
        eu = r"\.eu" if kind == "lever_eu" else ""
        m = re.search(rf"//(?:jobs|api){eu}\.lever\.co/(?:v0/postings/)?([\w.-]+)", evidence)
        return m.group(1) if m else ""
    if kind == "ashby":
        m = (re.search(r"jobs\.ashbyhq\.com/([^/?#\"']+)", evidence)
             or re.search(r"posting-api/job-board/([^/?#\"']+)", evidence))
        return m.group(1) if m and not re.search(r"[${}]", m.group(1)) else ""
    if kind == "smartrecruiters":
        m = (re.search(r"(?:jobs|careers)\.smartrecruiters\.com/([\w-]+)", evidence)
             or re.search(r"api\.smartrecruiters\.com/v1/companies/([\w-]+)", evidence)
             or re.search(r"//(?:www\.)?smartrecruiters\.com/([A-Z][\w-]+)/", evidence))
        return m.group(1).lower() if m else ""  # the API is case-insensitive
    if kind == "workday":
        m = re.search(r"https://([\w-]+\.(?:wd\d+\.)?myworkdayjobs\.com)/(?:[a-z]{2}-[A-Z]{2}/)?([\w-]+)", evidence)
        if not m or m.group(2) in ("wday", "login") or re.fullmatch(r"[a-z]{2}-[A-Z]{2}", m.group(2)):
            return ""  # a bare locale link (.../en-US/) names no board
        return f"https://{m.group(1)}/{m.group(2)}"
    if kind in ("phenom", "jibe", "getnoticed") and is_vendor_url(page):
        return ""  # a link to the vendor's own site, not the company's careers site
    if kind == "phenom":
        m = re.match(r"(https?://[^/]+)(/[a-z]{2}/[a-z]{2})(?:/|$)", page)
        return m.group(1) + m.group(2) if m else ""
    if kind in ("jibe", "getnoticed"):
        return _origin(page)
    if kind == "eightfold":
        m = re.search(r"[?&]domain=([\w.-]+)", evidence)
        return f"{_origin(evidence)}/careers?domain={m.group(1)}" if m else ""
    if kind == "heineken":
        return "https://careers.theheinekencompany.com"
    if kind == "Teamtailor":
        return evidence
    return ""


def _choose(hits: dict):
    """The system to record when a page shows several (ADR-0013 priority). Returns
    (kind, evidence, notes)."""
    def with_token(k):
        return next((e for e in hits[k] if token_from_evidence(k, e)), "")

    order = ["heineken"] if "heineken" in hits else []
    order += [k for k in DIRECT if k in hits and with_token(k)]
    order += [k for k in FRONT if k in hits]
    order += [k for k in DIRECT if k in hits and not with_token(k)]
    order += sorted((k for k in hits if k not in FETCHERS), key=lambda k: -len(hits[k]))
    kind = order[0]
    evidence = with_token(kind) or hits[kind][0]
    notes = []
    if kind in UNCONFIRMED:
        notes.append("pattern unconfirmed")
    if kind in FETCHERS and not token_from_evidence(kind, evidence):
        notes.append("no token in evidence")
    if kind == "workday" and "myworkdaysite.com" in evidence:
        notes.append("different URL form")
    if order[1:]:
        notes.append("also: " + ", ".join(order[1:]))
    return kind, evidence, notes


# ---------------------------------------------------------------- page reading

CAREERS_WORDS = re.compile(
    r"\b(?:careers?|jobs|job openings|vacancies|open positions|work at|working at|work with us|join us"
    r"|join the team|we'?re hiring|vacatures?|werken[ -]?bij|carri[eè]res?|kom werken)\b", re.I)
EXACT_TEXT = {"careers", "career", "jobs", "vacatures", "vacancies", "werken bij", "werkenbij"}
SEE_ALL = re.compile(
    r"\b(?:all jobs|view (?:all )?(?:jobs|openings|vacancies|positions)|search jobs|see (?:all )?(?:jobs|openings)"
    r"|open positions|all openings|vacancies|alle vacatures|bekijk (?:alle |onze )?vacatures)\b", re.I)
SKIP_HOSTS = re.compile(r"(?:^|\.)(?:linkedin\.com|facebook\.com|twitter\.com|x\.com|instagram\.com|youtube\.com"
                        r"|glassdoor\.\w+|indeed\.\w+|tiktok\.com)$")
FALLBACK_PATHS = ["/careers", "/jobs", "/vacatures", "/werken-bij"]
SOFT_404 = re.compile(r"404|not found|niet gevonden|page (?:doesn'?t|does not) exist|pagina bestaat niet", re.I)
NO_OPENINGS = re.compile(r"no current (?:openings|vacancies)|geen (?:openstaande )?vacatures", re.I)
JOB_PATH = re.compile(r"/(?:careers?|jobs?|vacatures?|vacancies|vacancy)/(?:[^?#]*/)?([^/?#]+)/?$", re.I)
JOB_SYSTEM_WORDS = re.compile(r"recruit|talent|career|jobs|vacan|hiring|werving")


def _links(page_url, soup):
    """(address, text) of the page's ordinary web links."""
    out = []
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
            continue
        url = urljoin(page_url, href).split("#")[0]
        if urlsplit(url).scheme in ("http", "https") and not SKIP_HOSTS.search(_host(url)):
            out.append((url, a.get_text(" ", strip=True)))
    return out


def careers_links(page_url, soup) -> list:
    """Homepage links that look like the careers page, best first (A3)."""
    site = site_key(_host(page_url))
    found = {}
    for url, text in _links(page_url, soup):
        if url.rstrip("/") == page_url.rstrip("/") or url in found:
            continue
        p = urlsplit(url)
        if CAREERS_WORDS.search(text) or CAREERS_WORDS.search(p.netloc + p.path.replace("-", " ")):
            exact = text.strip().lower() in EXACT_TEXT
            found[url] = (0 if exact else 1, 0 if site_key(_host(url)) == site else 1)
    return sorted(found, key=lambda u: found[u])  # stable: page order breaks ties


def _is_job_link(url: str) -> bool:
    m = JOB_PATH.search(urlsplit(url).path)
    return bool(m) and ("-" in m.group(1) or bool(re.search(r"\d{3,}", m.group(1))))


def job_links(page_url, soup) -> set:
    """Same-site links to a single job's page (a slug or an ID after careers/jobs/vacatures)."""
    site = site_key(_host(page_url))
    return {u for u, _ in _links(page_url, soup) if site_key(_host(u)) == site and _is_job_link(u)}


def see_all_link(page_url, soup) -> str:
    """The one "see all jobs" link followed from a careers page (A3), or ''."""
    here = urlsplit(page_url)
    deeper = ""
    for url, text in _links(page_url, soup):
        if url.rstrip("/") == page_url.rstrip("/") or _is_job_link(url):
            continue
        if SEE_ALL.search(text):
            return url
        p = urlsplit(url)
        if (not deeper and p.netloc == here.netloc and p.path.startswith(here.path.rstrip("/") + "/")
                and (CAREERS_WORDS.search(text) or CAREERS_WORDS.search(p.path.replace("-", " ")))):
            deeper = url
    return deeper


def has_jobposting(soup) -> bool:
    """Whether the page carries schema.org JobPosting data (A5)."""
    def walk(x):
        if isinstance(x, dict):
            t = x.get("@type")
            if t == "JobPosting" or (isinstance(t, list) and "JobPosting" in t):
                return True
            return any(walk(v) for v in x.values())
        return isinstance(x, list) and any(walk(v) for v in x)

    for s in soup.find_all("script", type="application/ld+json"):
        try:
            if walk(json.loads(s.string or s.get_text() or "")):
                return True
        except ValueError:
            continue
    return False


def _unknown_hosts(page_url, soup, website) -> list:
    """Off-site hosts that look like a job system we have no pattern for."""
    own = {site_key(_host(page_url)), site_key(_host(website))}
    hosts = []
    for tag in soup.find_all(["a", "iframe", "script", "form"]):
        v = tag.get("href") or tag.get("src") or tag.get("action")
        if not isinstance(v, str):
            continue
        h = _host(urljoin(page_url, v))
        if (h and site_key(h) not in own and not is_vendor_url("https://" + h) and not SKIP_HOSTS.search(h)
                and JOB_SYSTEM_WORDS.search(h) and h not in hosts):
            hosts.append(h)
    return hosts[:3]


def _soft_404(page: Page, soup) -> bool:
    h1 = soup.h1.get_text(" ", strip=True) if soup.h1 else ""
    return bool(SOFT_404.search(_title(page.html)) or SOFT_404.search(h1))


# ---------------------------------------------------------------- website (A2 step 1)

def _fold(s: str) -> str:
    """Lowercase, no accents, punctuation to spaces: 'Carrière.NL' -> 'carriere nl'."""
    s = "".join(c for c in unicodedata.normalize("NFKD", s or "") if not unicodedata.combining(c))
    return " ".join(re.findall(r"[a-z0-9]+", s.lower()))


def company_names(row) -> list:
    """Names to guess and verify with: company, registered name, and bracket parts."""
    names = []
    for raw in (row.get("company", ""), row.get("ind_registered_name", "")):
        parts = [raw]
        m = re.match(r"^(.*?)\((.*?)\)(.*)$", raw)
        if m:  # "Bird (MessageBird)" -> "Bird", "MessageBird"
            parts += [m.group(1) + m.group(3), re.sub(r"^(?:formerly|previously)\s+", "", m.group(2).strip(), flags=re.I)]
        for p in parts:
            n = normalise_name(p.strip()) if p.strip() else ""
            if n:
                names.append(n)
    return list(dict.fromkeys(names))


DOMAIN_IN_NAME = re.compile(r"\b[a-z0-9-]+\.(?:com|nl|io|dev|ai|eu|net|org|co)\b")


def candidate_domains(names) -> list:
    """'flow traders' -> flowtraders.com, .nl, .io, flow-traders.com, ...; a name that is a
    domain already ('booking.com') comes first."""
    domains = [d for n in names for d in DOMAIN_IN_NAME.findall(n)]
    for n in names:
        words = _fold(DOMAIN_IN_NAME.sub(lambda m: m.group(0).rsplit(".", 1)[0], n)).split()
        if not words:
            continue
        for sep in ("", "-"):
            for tld in ("com", "nl", "io"):
                domains.append(f"{sep.join(words)}.{tld}")
    return list(dict.fromkeys(domains))


def _resolves(host: str) -> bool:
    try:
        socket.getaddrinfo(host, 443)
        return True
    except (OSError, UnicodeError):
        return False


PARKED = re.compile(  # sale wording only: a bare "domain" or "te koop" is a registrar or Funda
    r"this (?:website|site|domain)(?: name)? (?:is|may be) for sale|resources and information|\.[a-z]{2,} is for sale|(?:domain|domein)(?:naam| name)? (?:is )?te koop"
    r"|buy this domain|\bparked\b|\b(?:hugedomains|sedo|dan\.com|afternic)\b", re.I)


def _fields(soup) -> list:
    og = soup.find("meta", property="og:site_name")
    return [soup.title.get_text(" ", strip=True) if soup.title else "",
            soup.h1.get_text(" ", strip=True) if soup.h1 else "",
            og.get("content", "") if og else ""]


def is_parked(soup) -> bool:
    """A domain-parking or domain-sale page ("flowtraders.com is for sale!")."""
    title, h1, _ = _fields(soup)
    return bool(PARKED.search(title) or PARKED.search(h1))


def names_company(names, soup, hosts=()) -> str:
    """The name that the page's title, first heading or site name gives, or ''.

    The page's own host names ("flowtraders com") are removed first, so a page that only
    repeats its address does not count, unless the address is part of the company's name. A name may also match with its spaces removed
    ("flowtraders" = "Flow Traders"), but only on whole words ("bird" is not "Thunderbird").
    """
    strip = [_fold(h) for h in hosts if h] + [_fold(h[4:]) for h in hosts if h and h.startswith("www.")]
    # An address that is (part of) the company's name stays: "Booking.com", "Smartly.io".
    strip = [h for h in strip if not any(f" {h} " in f" {_fold(n)} " for n in names)]
    for field in map(_fold, _fields(soup)):
        for h in sorted(strip, key=len, reverse=True):
            field = f" {field} ".replace(f" {h} ", " ").strip()
        words = field.split()
        for name in names:
            folded = _fold(name)
            if not folded or not words:
                continue
            if f" {folded} " in f" {field} ":
                return name
            compact = folded.replace(" ", "")
            if len(compact) >= 4 and any("".join(words[a:b]) == compact
                                         for a in range(len(words)) for b in range(a + 1, len(words) + 1)):
                return name
    return ""


def find_website(row, scan: Scan):
    """Guess and verify the company's website. Returns (website, homepage Page, notes);
    website is '' when none was verified."""
    names = company_names(row)
    tried, loaded = [], 0
    for domain in candidate_domains(names):
        if loaded >= MAX_GUESSES:
            break
        host = next((h for h in (domain, "www." + domain) if _resolves(h)), None)
        if not host:
            continue
        loaded += 1
        try:
            page = _fetch(f"https://{host}/", scan)
        except Blocked as e:
            tried.append(f"{domain} ({e})")
            continue
        except NoAnswer:
            tried.append(f"{domain} (no answer)")
            continue
        except LimitReached:
            tried.append(f"{domain} (request limit reached)")
            continue
        if page.ats_url or page.status != 200:
            tried.append(f"{domain} ({page.wall or ('redirects to a job system' if page.ats_url else f'HTTP {page.status}')})")
            continue
        soup = _soup(page.html)
        moved = site_key(_host(page.url)) != site_key(host)
        if is_parked(soup):
            tried.append(f"{domain} ({'redirects to ' + _host(page.url) + ', ' if moved else ''}a parked domain)")
            continue
        name = names_company(names, soup, (domain, host, _host(page.url)))
        if name:
            notes = [f"redirected from {domain}"] if moved else []
            if len(_fold(name).replace(" ", "")) <= 4:
                notes.append("short name, check")
            return _origin(page.url), page, notes
        if moved:
            tried.append(f"{domain} redirects to {_host(page.url)}, which does not name the company")
        else:
            tried.append(f"{domain} (does not name the company)")
    if not tried:
        return "", None, ["no website: no guessed domain resolves"]
    return "", None, ["no website: tried " + ", ".join(tried)]


# ---------------------------------------------------------------- careers page (A3)

class Found:
    """What the careers search has learned so far, for the decision in scan_row."""

    def __init__(self):
        self.careers_url = ""
        self.hits = {}
        self.jobs = 0
        self.jsonld = False
        self.no_openings = False
        self.careers_found = False
        self.blocked = ""
        self.no_answer = ""
        self.limit = False
        self.unknown = []


def _add_hits(found: Found, hits: dict) -> bool:
    for kind, evidence in hits.items():
        found.hits.setdefault(kind, []).extend(evidence)
    return bool(hits)


def _examine(page: Page, website: str, found: Found) -> bool:
    """Read a careers page into `found`. True if it shows a job system or lists jobs."""
    if page.ats_url:
        return _add_hits(found, detect(page.ats_url, "", page.redirects))
    soup = _soup(page.html)
    hits = detect(page.url, page.html, page.redirects, soup)
    jsonld = has_jobposting(soup)
    jobs = len(job_links(page.url, soup))
    found.jsonld = found.jsonld or jsonld
    found.jobs = max(found.jobs, jobs)
    found.no_openings = found.no_openings or bool(NO_OPENINGS.search(soup.get_text(" ")))
    found.unknown += [h for h in _unknown_hosts(page.url, soup, website) if h not in found.unknown]
    return _add_hits(found, hits) or jsonld or jobs >= 2


def _open(url: str, scan: Scan, found: Found):
    """Load a candidate careers page; None if it is no use (404, refused, soft 404)."""
    try:
        page = _fetch(url, scan)
    except Blocked as e:
        found.blocked = str(e)
        return None
    if page.ats_url:
        return page
    if page.wall:
        found.blocked = page.wall
        return None
    if page.status != 200 or _soft_404(page, _soup(page.html)):
        return None
    return page


def find_careers(website: str, home: Page, scan: Scan) -> Found:
    found = Found()
    try:
        _find_careers(website, home, scan, found)
    except LimitReached:
        found.limit = True
    except NoAnswer as e:
        found.no_answer = str(e)
    return found


def _refused(found: Found) -> bool:
    """A site that refused a page (401/403/429/503 or a bot wall) is left alone. Live, Leiden
    University refused the connection outright after serving one "Access Blocked" page."""
    return found.blocked.startswith(("HTTP", "bot wall"))


def _find_careers(website, home, scan, found):
    soup = _soup(home.html)
    # A homepage link straight to a job system is the answer; it is not loaded.
    for url, _ in _links(home.url, soup):
        hits = detect(url)
        if hits:
            found.careers_url = url
            _add_hits(found, hits)
            return
    url, page = "", None
    for url in careers_links(home.url, soup)[:3]:
        page = _open(url, scan, found)
        if page or _refused(found):
            break  # a site that refuses us is left alone
    if page is None and not _refused(found):
        for path in FALLBACK_PATHS:
            url = website.rstrip("/") + path
            page = _open(url, scan, found)
            if page or _refused(found):
                break
    if page is None:
        return
    found.careers_found = True
    # A careers link that redirects to a job system: careers_url is the company's own link.
    found.careers_url = url if page.ats_url else page.url
    _examine(page, website, found)
    if found.hits or page.ats_url:
        return
    # One more step at most: a "see all jobs" link (A3).
    nxt = see_all_link(page.url, _soup(page.html))
    deeper = _open(nxt, scan, found) if nxt else None
    if deeper and _examine(deeper, website, found):
        found.careers_url = nxt if deeper.ats_url else deeper.url


# ---------------------------------------------------------------- one company

def _result(website="", careers_url="", ats_seen="", evidence="", notes=(), scan=None) -> dict:
    notes = [n for n in notes if n] + [f"requests={scan.requests if scan else 0}"]
    return {"website": website, "careers_url": careers_url, "ats_seen": ats_seen,
            "ats_evidence": evidence, "scan_note": "; ".join(notes)}


def scan_row(row) -> dict:
    """The five scan columns for one company (ADR-0013, decision rules in order)."""
    scan = Scan()
    website, notes = row.get("website", ""), []
    try:
        if website:  # filled by an earlier scan, A-4 or Younes: not re-guessed
            home = _fetch(website.rstrip("/") + "/", scan)
        else:
            website, home, notes = find_website(row, scan)
            if not website:
                return _result(notes=notes, scan=scan)
    except Blocked as e:
        return _result(website, "", "blocked", "", [str(e)], scan)
    except NoAnswer as e:
        return _result(website, "", "blocked", "", [f"no answer: {e}"], scan)
    except LimitReached:
        return _result(website, "", "blocked", "", ["request limit reached"], scan)
    if home.ats_url:  # the website itself redirects to a job system
        kind, evidence, more = _choose(detect(home.ats_url, "", home.redirects))
        return _result(website, home.ats_url, kind, evidence, notes + more, scan)
    if home.wall or home.status != 200:
        return _result(website, "", "blocked", "", [f"homepage: {home.wall or f'HTTP {home.status}'}"] + notes, scan)

    found = find_careers(website, home, scan)
    tail = ["request limit reached"] if found.limit else []
    if found.hits:
        kind, evidence, more = _choose(found.hits)
        return _result(website, found.careers_url, kind, evidence, notes + more + tail, scan)
    if found.no_answer:
        return _result(website, found.careers_url, "blocked", "", [f"no answer: {found.no_answer}"] + notes, scan)
    if found.blocked and not found.careers_found:
        return _result(website, "", "blocked", "", [f"careers page: {found.blocked}"] + notes + tail, scan)
    extra = [f"jobposting={'yes' if found.jsonld else 'no'}"]
    if found.unknown:
        extra.append("unknown hosts: " + ", ".join(found.unknown))
    if found.jsonld or found.jobs >= 2:
        return _result(website, found.careers_url, "custom", "", notes + [f"job links={found.jobs}"] + extra + tail, scan)
    if found.careers_found:
        if found.no_openings:
            return _result(website, found.careers_url, "custom", "", notes + ["says no openings"] + extra + tail, scan)
        return _result(website, found.careers_url, "needs_browser", "", notes + extra + tail, scan)
    return _result(website, "", "no_careers_page", "", notes + tail, scan)


# ---------------------------------------------------------------- targets.csv

def save_targets(rows: list, fields: list, path: str = TARGETS_PATH):
    """UTF-8 without BOM, LF line endings, rows in their order (requirements §6)."""
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    os.replace(tmp, path)


def select_rows(rows, limit=None, companies=(), known_websites=False, retry_no_answer=False) -> list:
    if companies:
        todo = [r for r in rows if r["company"] in companies]
    elif known_websites:
        todo = [r for r in rows if r["website"] and not r["ats_seen"]]
    elif retry_no_answer:
        todo = [r for r in rows if r["scan_note"].startswith("no answer:")]
    else:
        todo = [r for r in rows if not r["scan_note"]]
    return todo[:limit]


FAILURE_WORDS = ("no answer", "unreachable", "request limit reached", "scan error")


def run(limit=None, companies=(), known_websites=False, retry_no_answer=False, path: str = TARGETS_PATH):
    rows = load_targets(path)
    fields = list(rows[0].keys()) + [c for c in NEW_COLUMNS if c not in rows[0]]
    for row in rows:
        for col in NEW_COLUMNS:
            row.setdefault(col, "")
    todo = select_rows(rows, limit, companies, known_websites, retry_no_answer)
    print(f"  {sum(1 for r in rows if r['scan_note'])}/{len(rows)} rows scanned before, scanning {len(todo)}...")

    failures = []
    for i, row in enumerate(todo, 1):
        try:
            result = scan_row(row)
        except Exception as e:  # one odd page must not end a run of hours; the row stays unscanned
            failures.append(f"{row['company']}: scan error {type(e).__name__}: {e}")
            print(f"  [{i}/{len(todo)}] {row['company']}: scan error ({type(e).__name__}), left unscanned")
            continue
        row.update(result)
        save_targets(rows, fields, path)  # after every company, so a killed run loses nothing (A9)
        print(f"  [{i}/{len(todo)}] {row['company']}: {row['ats_seen'] or '-'} {row['careers_url']} ({row['scan_note']})")
        if any(w in row["scan_note"] for w in FAILURE_WORDS):
            failures.append(f"{row['company']}: {row['scan_note']}")

    counts = {}
    for r in rows:
        if r["scan_note"]:
            key = r["ats_seen"] or "(no website)"
            counts[key] = counts.get(key, 0) + 1
    print("\n  ats_seen over all scanned rows:")
    for key, n in sorted(counts.items(), key=lambda kv: -kv[1]):
        print(f"    {key}: {n}")
    print(f"\n  Failures this run: {len(failures)}")
    for f in failures:
        print(f"    {f}")


def main(argv=None):
    p = argparse.ArgumentParser(description="Find each target company's careers page and job system (ADR-0013).")
    p.add_argument("limit", nargs="?", type=int, help="scan at most this many rows")
    p.add_argument("--company", action="append", default=[], help="rescan this company (repeatable)")
    p.add_argument("--known-websites", action="store_true", help="rows with a website but no ats_seen")
    p.add_argument("--retry-no-answer", action="store_true", help='rows whose note starts with "no answer:"')
    a = p.parse_args(argv)
    sys.stdout.reconfigure(errors="replace")  # a company name the console can't show must not stop the run
    run(a.limit, a.company, a.known_websites, a.retry_no_answer)


if __name__ == "__main__":
    main()
