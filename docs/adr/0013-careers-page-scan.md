# 0013. Scan each company's own careers page to find its job-board system

Date: 2026-11-11

Status: accepted by Younes on 2026-11-11, through the signed-off coverage requirements
(`docs/requirements-coverage.md`, phase A). The coordinator's answers to the planner's
open questions are recorded under "Decisions on open questions" below.

## Context

`targets.csv` lists 1,045 companies; only 183 are fetched daily. 839 rows say `none`, but
that only means `ats_resolver.py` guessed a board address from the company name and the
guess missed on five vendors (ADR-0004, ADR-0006). Behind those rows are three groups of
unknown size: companies on a system we already read under an address the guess missed;
companies on a system we cannot read yet (SAP SuccessFactors at Leiden University); and
companies with a careers page they built themselves (50five).

Guessing more addresses cannot tell these apart. The company's own careers page can: its
"apply" links, frames and scripts show which system it uses and the exact board address.
So the scan starts from the company's website, which `targets.csv` does not have yet.

## Decision

`python coverage_scan.py` visits each company's website and careers page with plain web
requests and records what it finds in `targets.csv`.

### 1. Five new columns

Appended after the existing columns, in this order: `website`, `careers_url`, `ats_seen`,
`ats_evidence`, `scan_note`. The scan writes only these five. It never changes `company`,
`ind_registered_name`, `other_ind_entities`, `category`, `already_applied`, and never
`source`, `token` or `board_status`, also not on the 183 `auto`/`hand` rows it scans as an
accuracy test (A7). The file keeps its encoding (UTF-8, no byte-order mark), its LF line
endings and its row order.

- `website`: the company's site, as the origin (`https://www.effectory.com`) after redirects.
- `careers_url`: the page where the jobs or the system's evidence were found.
- `ats_seen`: see 2.
- `ats_evidence`: the address that proves `ats_seen`, or `<page url> | <snippet>` when the
  proof is inside the page's own data (a Recruitee custom domain, a GetNoticed site).
- `scan_note`: why, in a few words; every scanned row has one, ending in `requests=N`.

### 2. `ats_seen` values (A4)

- one of the 12 kinds the pipeline reads: `greenhouse`, `lever`, `lever_eu`, `ashby`,
  `recruitee`, `smartrecruiters`, `workday`, `jibe`, `getnoticed`, `eightfold`, `phenom`,
  `heineken`;
- the name of a system it does not read: `Teamtailor`, `Personio`, `Workable`, `BambooHR`,
  `SAP SuccessFactors`, `Oracle Recruiting`, `Taleo`, `iCIMS`, `Jobvite`, `Homerun`,
  `Breezy`, `JOIN`, `Pinpoint`, `AFAS`, `OTYS`, `Carerix`, `Connexys`, `Emply`, `Hireserve`.
  A host that looks like a job system but matches none of these is written into
  `scan_note` ("unknown hosts: …"), so the report can name it rather than lump it in;
- `custom`: the company's own page lists jobs (schema.org `JobPosting` data or at least two
  job links), or says it has no openings right now (note "says no openings");
- `needs_browser`: a careers page was found but shows no jobs, links or job data without
  running its scripts;
- `blocked`: robots.txt refuses or cannot be read, the site answers 401/403/429/503 or
  shows a bot wall, or the site did not answer (note starts with "no answer:");
- `no_careers_page`: a website, but no careers page;
- empty: no website found (the reason is in `scan_note`).

**Priority when a page shows several systems:** (1) the Heineken careers host; (2) a kind we
read whose board address is in the evidence (workday, greenhouse, lever, lever_eu, ashby,
smartrecruiters, recruitee); (3) the front-end platforms we read (jibe, phenom, eightfold,
getnoticed); (4) a kind we read without a board address; (5) systems we do not read, most
links first. The others seen are listed in `scan_note` as "also: …". Booking's Jibe site
also links iCIMS, Heineken's site also links SuccessFactors: the rule names the one we read.

For `custom` and `needs_browser` rows, `scan_note` says `jobposting=yes` or `jobposting=no`
(A5): whether the careers page carries schema.org `JobPosting` data.

### 3. Website: guess and verify (A2 step 1)

Names come from `company` and `ind_registered_name` (through `normalise_name`), plus the
parts in and outside brackets ("Bird (MessageBird)"). A name that already is a domain
(Booking.com, Aanmelder.nl) is tried first. Then, per name, `joined.com`, `joined.nl`,
`joined.io`, `hyphen-ated.com`, `.nl`, `.io`. A candidate must resolve in DNS (no web
request), then at most 6 resolving candidates are loaded. One is accepted only if its
`<title>`, first `<h1>` or `og:site_name` names the company: the name's words appear as
whole words, or, for names of 4 or more letters, the name without spaces is part of the
field without spaces, on whole words only ("flowtraders" matches "Flow Traders"; "bird" does
not match "Thunderbird"). The page's own address ("flowtraders.com") is removed from these
fields first, unless it is part of the company's name (Booking.com, Smartly.io). A page
whose title or heading uses sale wording ("this domain/website/site ... for sale",
"x.com is for sale", "resources and information",
"domeinnaam te koop", "buy this domain", "parked", or names HugeDomains, Sedo, Dan.com or
Afternic) is a parked domain and rejected, whether loaded directly or after a redirect. A
bare "domain" or "te koop" is not enough: registrars (SIDN, Hostnet) and Funda use them. A website found through a name of 4 letters or fewer is
noted "short name, check". A redirect to another domain is
accepted only if that page names the company (noted "redirected from …"). Nothing accepted:
`website` stays empty and the note lists what was tried. A guessed domain that times out is
just a miss in that list: the note does not start with "no answer:", so
`--retry-no-answer` skips it; A-4's web search handles these rows. A-4 fills these rows by web
search; the scan then reuses a filled-in `website` without guessing.

### 4. Careers page (A3)

On the homepage, a link straight to a job system is the answer at once and is not loaded.
Otherwise the links whose text or address says careers, jobs, vacancies, open positions,
work at, join us, we're hiring, vacature(s), werken bij or carrière are ranked (exact text
"careers"/"jobs"/"vacatures" first, then the same site, then other sites) and the best is
loaded (up to 3 tried if earlier ones fail). Without such a link, `/careers`, `/jobs`,
`/vacatures` and `/werken-bij` are tried; a 404 or a "page not found" page does not count.
From the careers page, at most **one** more step is followed, to a "see all jobs" link.
Nothing beyond that: no job's own page is opened (see Q3 below).

### 5. Detection by address only

A system is recognised by the host and path of a link, frame, script, form, redirect or an
address written inside the page's data, never by a bare word (the word "AFAS" on a
customer-logo strip is not evidence). Two exceptions read page data: a Recruitee custom
domain (`atsHost` recruitee.com plus `"subdomain":"x"`) and GetNoticed ("logo Getnoticed"
plus its `/vacature/<id>/` or `/api/vacancy` links). `token_from_evidence(kind, evidence)`
turns the evidence into the `token` form `targets.csv` uses; phase B (B1) reuses it.

Patterns confirmed on a real company page by the planner: greenhouse, recruitee (subdomain
and custom domain), lever, ashby, smartrecruiters, workday, phenom, jibe, heineken,
Teamtailor, Personio, SAP SuccessFactors. Not yet confirmed: lever_eu, getnoticed,
eightfold (partly), and Homerun, iCIMS, Workable, BambooHR, Oracle Recruiting, Taleo,
Jobvite, Breezy, JOIN, Pinpoint, AFAS, OTYS, Carerix, Connexys, Emply, Hireserve. A row
named by an unconfirmed pattern gets "pattern unconfirmed" in its note; one evidence
address per system is checked by hand before phase C relies on it.

### 6. Politeness (A6)

- **robots.txt** is fetched with our own User-Agent (`scrapers.targets.HEADERS`) and parsed
  with `urllib.robotparser`. Never `RobotFileParser.read()`: it sends Python's default
  User-Agent, which many sites refuse, and they then look like "disallow all". 200: obey it,
  including `Crawl-delay`. 404 and other 4xx: allowed. 401/403: `blocked`. 429 and 5xx:
  `blocked` ("robots.txt unreachable"). A network error on robots.txt: `blocked`, "no answer:".
  A robots.txt that redirects within the same site (sendcloud.com to www.sendcloud.com) is
  also used for the host it redirected to, saving a request. A robots.txt redirect to a job
  system's host is not followed (treated as no robots.txt).
  robotparser applies the first matching rule rather than the longest one (RFC 9309); that
  is stricter, so it is kept, and sites like HSBC (`Disallow: /` before `Allow: /careers`)
  come out `blocked`. A crawl delay above 30 seconds is not waited out; the site is noted
  `blocked` ("robots.txt crawl-delay …").
- **At most 6 requests per site per company**, robots.txt and each redirect hop included. A
  site is a registrable domain (`jobs.funda.nl` and `funda.nl` are one site;
  `werkenbijachmea.nl` is another, with its own 6). When the limit is reached, the row is
  decided from what is known, noted "request limit reached".
- **At least 1 second between requests to the same site**, or the crawl delay if longer,
  kept for the whole run (sites shared by several companies, such as relx.com).
- **Job-system hosts are never requested.** Their addresses are only evidence, so the scan
  sends nothing to Greenhouse, Workday and the like.
- Redirects are followed by hand (at most 5), each through robots.txt and the limit.
- **Bot wall:** status 401/403/429/503, or a page whose title, or whose body when under
  20,000 characters, says "just a moment", "attention required", "access denied", "access
  blocked", "toegang geblokkeerd", "je bent bijna op de pagina", "captcha", "verify you are
  human", "cf-chl", "datadome" or "incapsula". Script tags and the word "recaptcha" are
  removed from the body first, since normal pages load Google's reCAPTCHA for a form. After
  any refusal the site is left alone for that company.
- Plain requests only, 15 s timeout, at most 2 MB read per page. No headless browser, no
  logging in, nothing that gets round a refusal.

### 7. Resuming (A9)

`targets.csv` is the only state. A row is done when `scan_note` is filled. The file is
rewritten (temporary file, then replace) after every company, so a killed run loses at
most the company it was on and the next start continues there. A company whose scan
crashes on something unexpected is listed as a failure and left unscanned, so the next
start retries it.

### 8. Command line

- `python coverage_scan.py`: every row not scanned yet (resumes).
- `python coverage_scan.py 50`: the next 50.
- `python coverage_scan.py --company "Mollie" --company "bol"`: rescan these rows, done or not.
- `python coverage_scan.py --known-websites`: rows with a `website` but no `ats_seen` (A-4).
- `python coverage_scan.py --retry-no-answer`: rows whose note starts with "no answer:".

A row that already has a `website` is never re-guessed; clear the cell to force a guess.

## Decisions on open questions (coordinator, 2026-11-11)

- **Q1.** The 6-request limit is per registrable domain (per site), robots.txt included.
- **Q2.** robots.txt is fetched with `requests` and our headers and parsed with robotparser;
  401/403/5xx/unreachable robots means `blocked`; first-match strictness is kept.
- **Q3.** No peek at a job's own page. A3 allows one step after the careers page. Sites
  whose system only shows on a job page (Mollie) end as `custom` or `needs_browser`; the
  A-5 accuracy report counts them so Younes can decide later.
- **Q4.** Timeouts and connection errors give `blocked` with a note starting "no answer:",
  and `--retry-no-answer` rescans exactly those rows.
- **Q5.** Unconfirmed patterns are used, with "pattern unconfirmed" in the note, and are
  confirmed before phase C relies on them.
- **Q6.** A careers page saying there are no openings is `custom`, note "says no openings".

## Consequences

- About 7-10 requests per company at 1 s or more apart: 3.5 to 5 hours for all 1,045 rows,
  run in the background (A-3).
- The A7 answer key is partly stale (Extreme Networks moved from Lever to Workday) and some
  sites put a front-end platform over a board we read (Adobe: Phenom over Workday). Those
  show up as mismatches with their cause, for Younes to judge.
- Careers pages that load jobs only by script (TomTom, Elastic) or show the board only on a
  job page (Mollie) are not identified; they are counted as `needs_browser` or `custom`.
- First-match robots.txt reading blocks a few sites the standard would allow.

## Alternatives rejected

- **More token guessing** (ADR-0004): cannot find boards under unexpected names, nor tell
  "unknown system" from "own page".
- **A headless browser**: out of scope (requirements §5); such pages are counted instead.
- **A search API** to find websites: out of scope; A-4 uses a one-off agent search.
