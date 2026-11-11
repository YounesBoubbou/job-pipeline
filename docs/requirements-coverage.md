# Requirements: more companies covered

Status: **draft, waiting for Younes's sign-off** (written 2026-11-11)

This is the single source of truth for the coverage work that follows the MVP. Anyone
building it, human or agent, follows it to the letter. If something is not written here, it
is not in scope: ask rather than guess. `docs/requirements.md` (the MVP) stays in force;
where the two disagree, this document says so explicitly (only T1 does).

Each requirement has an ID and a **check**: a concrete test that proves it is met. A
requirement is done only when its check passes.

## 1. Goal

`targets.csv` lists 1,045 companies, all recognised visa sponsors. The pipeline fetches jobs
from only 183 of them each day. The goal is to fetch from as many of the other 862 as can be
read politely and reliably, and to end with an exact, evidence-backed answer for every
company: fetched, or why not.

No target number is promised. Several hundred is realistic; all 1,045 is not, because some
sites refuse automated access and some companies publish jobs nowhere readable.

## 2. Where things stand (2026-11-11)

| `board_status` | Rows | Meaning (ADR-0006) | Fetched daily |
|---|---|---|---|
| `auto` | 112 | Board found, lists a job in the Netherlands | yes |
| `hand` | 71 | Board confirmed by hand | yes |
| `review` | 21 | Board found but not confirmed | no |
| `none` | 839 | No board found | no |
| blank | 2 | Lookup failed (Ncardia, Tech Rise People) | no |

**Why 839 rows say `none`.** `ats_resolver.py` guessed a board address from the company
name ("flow traders" → `flowtraders`, `flow-traders`) and tried it on five job-board
systems: Greenhouse, Recruitee, Lever, Ashby, SmartRecruiters. `none` means the guess
missed. It does not mean the company has no job board. Workday was never guessed; its 24
boards were added by hand.

The 839 therefore hold three groups of unknown size:

1. **On a system the pipeline already reads, under an address the guess missed.**
2. **On a job-board system the pipeline cannot read yet** (SAP SuccessFactors is one known
   case: Leiden University).
3. **On a careers page the company built itself** (50five is one known case).

The pipeline reads 12 kinds of board today, the keys of `FETCHERS` in
`scrapers/targets.py`: `greenhouse`, `lever`, `lever_eu`, `ashby`, `recruitee`,
`smartrecruiters`, `workday`, `jibe`, `getnoticed`, `eightfold`, `phenom`, `heineken`.

`targets.csv` has no column for a company's website. Finding it is part of this work.

## 3. Approach, in four phases

The work starts from each company's own careers page instead of a guessed address: the
"apply" links on that page show which system the company uses and the exact address of its
board. Each phase ends with a report and **stops for Younes** before the next one starts.

| Phase | What happens | Ends with |
|---|---|---|
| A. Scan | Find every unfetched company's website and careers page; record which system it uses | A report with counts per system |
| B. Known systems | Fill in the boards of companies on the 12 kinds already read | More rows fetched, no new fetcher code |
| C. New readers | Add readers for the most-used systems not read yet | More rows fetched |
| D. What is left | Count what remains and why | A report; no building |

## 4. Requirements

### Phase A: the scan

**A1. Scope of the scan.** Every row whose `board_status` is `none`, `review` or blank is
scanned (862 rows). The 183 `auto` and `hand` rows are scanned too, read-only, as the
accuracy test of A7; their `source`, `token` and `board_status` are never changed by the scan.
*Check:* the report's totals add up to 1,045.

**A2. Website.** For each company the scan records its official website in a new `website`
column. Two steps, in this order:
1. A script guesses addresses from `company` and `ind_registered_name` (for example
   `<name>.com`, `<name>.nl`, `<name>.io`) and accepts one only if the page it loads names
   the company (in its title, its main heading or its site-name tag).
2. Rows still empty are looked up by an agent with web search, in batches. The agent records
   the address and one line of evidence. This is a one-off; no search service is added to
   the pipeline.
A row whose website cannot be established stays empty with the reason in `scan_note`.
*Check:* A8.

**A3. Careers page.** From the website, the scan finds the page that lists jobs and records
it in a new `careers_url` column. It looks at links whose text or address says careers,
jobs, vacancies, "work at", "join us", or the Dutch `vacatures` and `werken bij`, and
follows at most one more step (a "see all jobs" link).
*Check:* A8.

**A4. Which system.** The scan records the system in a new `ats_seen` column, with the
address that proves it in `ats_evidence`. It looks at links, embedded frames, scripts and
redirects on the careers page. `ats_seen` is one of:
- a kind the pipeline already reads (one of the 12 names in section 2);
- the name of a system it does not read. Starting list, each pattern to be confirmed on a
  real page before it is relied on: Teamtailor, Personio, Workable, BambooHR, SAP
  SuccessFactors, Oracle Recruiting, Taleo, iCIMS, Jobvite, Homerun, Breezy, JOIN, Pinpoint,
  and the Dutch systems AFAS, OTYS, Carerix, Connexys, Emply, Hireserve. Any other system
  met during the scan is added under its own name, not lumped together;
- `custom`: the company's own page lists the jobs, no outside system found;
- `needs_browser`: the page shows no jobs or links until scripts run (see A6);
- `blocked`: the site refused the request (robots.txt, 403, a bot wall);
- `no_careers_page`: a website was found but no page listing jobs;
- empty, when A2 found no website.
*Check:* every scanned row has an `ats_seen` value or an empty `website` with a `scan_note`.

**A5. Embedded job data.** For `custom` and `needs_browser` rows the scan also records, in
`scan_note`, whether the careers page carries schema.org `JobPosting` data (the
machine-readable job block sites add for Google's job search). This sizes the generic reader
of C4.
*Check:* the report gives the count.

**A6. Politeness.** The scan:
- obeys each site's `robots.txt`, including any crawl delay;
- makes at most 6 requests per company website, at least 1 second apart on the same site;
- sends the same honest `User-Agent` as `scrapers/targets.py`, with no personal details;
- uses plain web requests only. No headless browser (a browser run by a program), no
  logging in, no working around a block. A page that needs any of these is recorded as
  `needs_browser` or `blocked` and left alone.
*Check:* tests with fake sites prove the request limit, the delay and the robots.txt rule.

**A7. Accuracy on known answers.** Run on the 183 `auto` and `hand` rows, whose system is
already known, the scan must name the right system for at least 80% of those whose website
it found, and must never name a wrong board-reading kind for more than 5 of them. Every
mismatch is listed in the report with its cause.
*Check:* the report shows the two numbers and the list.

**A8. Accuracy by hand.** The reviewer opens 40 randomly chosen scanned rows in a browser
(the random pick is recorded): at least 36 must have the right website, careers page and
system. Fewer means the scan is fixed and rerun, not signed off.
*Check:* the 40 rows and verdicts are in the report.

**A9. Survives interruption.** The scan saves after every company and, when started again,
continues where it stopped. (Earlier long runs on this PC were killed three times for low
memory.)
*Check:* a test stops a fake scan halfway and shows the second start skips finished rows.

**A10. Report.** `docs/coverage-scan-report.md` gives: rows per `ats_seen` value; the same
split per `category`; the size of the three groups of section 2; the full list of systems
with 3 or more companies; and a proposed order for phase C with the number of companies
each new reader would unlock. Then the work stops for Younes.
*Check:* the report exists and its numbers match `targets.csv`.

### Phase B: boards on systems already read

**B1. Fill in.** For every row whose `ats_seen` is one of the 12 kinds, the board's token is
taken from `ats_evidence` (not guessed), written to `source` and `token`, and the board is
fetched once through its `FETCHERS` entry.
*Check:* B4.

**B2. Status.** The fetched board decides `board_status`, by the existing rules of ADR-0006:
`auto` if it lists at least one job naming a Dutch place and no "(Sample)" job; `review`
otherwise.
*Check:* tests cover both outcomes with fake boards.

**B3. Review rows.** Every `review` row, the 21 old ones included, is then settled by an
agent with the evidence written in `scan_note`: `hand` if the board is the right company's
(the link came from the company's own verified website, and the board's own name or jobs
match), `none` if not. No row is left as `review` at the end of phase B. The 2 blank rows
are settled the same way.
*Check:* zero `review` and zero blank rows; Younes spot-checks 15 of the new `hand` rows.

**B4. They fetch.** A fetch of only the newly added boards finishes with every one of them
either returning jobs or listed as failed with a reason; failed ones are fixed or set back
to `none`.
*Check:* the run summary of that fetch, attached to the phase report.

**B5. Existing rows are safe.** No row that was `auto` or `hand` before this work changes,
unless the scan proved its board dead or moved, and then only with the proof in `scan_note`.
*Check:* `git diff` of `targets.csv` shows changes to old `auto`/`hand` rows only where
`scan_note` explains them.

### Phase C: new readers

**C1. Which systems.** A new reader is built for each unread system used by 10 or more
companies in the scan, biggest first. Systems with 3 to 9 companies are listed for Younes
to decide one by one. The order and the list come from the phase A report, confirmed by
Younes before phase C starts.
*Check:* the phase C task list matches what Younes confirmed.

**C2. Before building each reader.** The planner confirms and writes down: that the system
offers a public listing meant to be read without logging in (a public API or feed is
preferred over reading web pages); what its `robots.txt` and terms say; whether jobs can be
asked for by country (as ADR-0008 does for Workday); and where the description is. A system
that fails this is not built; it goes to the phase D report.
*Check:* each reader's ADR records these four points.

**C3. Each reader.** A new reader follows the pattern of the existing ones in
`scrapers/targets.py`: one function in `FETCHERS` that yields
`(title, location, description, url)`; a `DESCRIPTION_FETCHERS` entry when descriptions need
a second request, used only for jobs that already pass the title and location rules; a
failing board never stops the run and shows under `failed` in the run summary. Its rows get
`source`, `token` and a status by B1 to B4.
*Check:* tests with fake responses for the listing, the description, an empty board and a
failing board; then a live fetch of three real boards of that system returning Dutch jobs.

**C4. Generic reader for embedded job data.** Built only if the phase A report shows 10 or
more `custom` companies whose careers page carries `JobPosting` data that can be reached
within the request limits of A6. Same rules as C3.
*Check:* as C3, on three real sites.

### Run time

**T1. The daily run.** *This replaces P6 of the MVP for runs with the new boards.* A full
run takes 30 minutes or less on Younes's PC. Boards on different sites may be fetched at the
same time; requests to the same site are never faster or more frequent than today. If a full
run cannot meet 30 minutes, the work stops and the options are put to Younes.
*Check:* `duration_seconds` in `data/last_run.json` after each phase that adds boards.

### Phase D: what is left

**D1. Final report.** `docs/coverage-final-report.md` gives, for all 1,045 companies: how
many are fetched; and for the rest, counts per reason (`needs_browser`, `blocked`, `custom`,
small systems, no website, no careers page), with the company names. It prices the three
ways to go further, without building any: reading pages with a headless browser, reading
pages with an AI model, and filling gaps from a job-search API. Then the work stops.
*Check:* the report's counts match `targets.csv`.

### Quality

**Q1.** `python -m pytest` passes before every commit.
**Q2.** Every new rule, reader and scan step comes with a test.
**Q3.** Tests never call real websites, real job boards or the real Google Sheet.
**Q4.** Each phase's design choices are recorded in an ADR in `docs/adr/` before they are
built: one for the scan and its new columns, one per batch of readers, one for T1.
**Q5.** `README.md` and the "Project" section of `CLAUDE.md` are updated at the end of each
phase to describe the pipeline as it then works.

## 5. Not in scope

- Adding companies beyond the 1,045, or other fields (marketing, finance, HR)
- Any change to the filter rules in `filters.py`, or to the web app
- A headless browser, AI reading of pages, or job-search APIs (phase D only prices them)
- The public, cloud-hosted version of the project
- Getting around a site that refuses automated access
- The register-wide lookup of all 13,000 sponsors (still on hold, ADR-0005)

## 6. Rules for whoever builds this

- **Work in a separate folder.** The daily scheduled task runs the pipeline from
  `C:\Users\Younes\Desktop\job-pipeline` at 08:00, so that folder must always hold working
  code. Create a branch `coverage` from `mvp` as a git worktree at
  `C:\Users\Younes\Desktop\job-pipeline-coverage` and build there. Never switch branch in
  the main folder. Do not push; do not touch `master`. Younes merges at the end of a phase.
- **Never write to the main folder's `data/`.** Scans and test fetches use the worktree's
  own `data/` folder, so the web app's job list and the "seen jobs" record are untouched.
- **`targets.csv`:** add columns and fill rows as this document says; keep its encoding
  (UTF-8, no byte-order mark) and line endings (LF); never reorder or remove rows or touch
  `company`, `ind_registered_name`, `other_ind_entities`, `category`, `already_applied`.
- The process is the one in `CLAUDE.md`: planner, builder, reviewer, one task at a time,
  two failed reviews and the task goes to "Waiting for Younes". The task list for this work
  is `docs/tasks-coverage.md`, written after sign-off.
- A long job (the scan, an agent lookup batch) runs in the background, saves as it goes, and
  its log's failure list is read before its result is trusted: an exit code of 0 is not enough.
- Manual edits by Younes are the intended direction: build on them, never revert them.
- When a requirement cannot be met as written, stop and report; do not quietly do something
  close to it.

## 7. To confirm at sign-off

Proposed by Claude; each needs a yes or a correction from Younes:

1. **A2:** websites are found by a guess-and-verify script first, then by an agent with web
   search for the rest. The agent step costs Claude usage once, nothing per day.
2. **A6:** no headless browser in this work; such pages are counted, not read.
3. **C1:** a system gets a reader at 10 or more companies; 3 to 9 is your call per system.
4. **T1:** the run-time limit goes from 15 to 30 minutes, and boards on different sites may
   be fetched at the same time.
5. **B3:** an agent settles the `review` rows with written evidence, and you spot-check 15.
6. **Section 6:** the work is built in a second folder so the 08:00 run is never disturbed.
