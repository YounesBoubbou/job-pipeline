# Requirements: MVP

Status: **signed off by Younes** (2026-11-10)

This is the single source of truth for what the MVP must do. Anyone building it, human or
agent, follows it to the letter. If something is not written here, it is not in the MVP:
ask rather than guess. The reasons behind past design choices are in `docs/adr/`.

Each requirement has an ID and a **check**: a concrete test that proves it is met. A
requirement is done only when its check passes.

## 1. Goal

Every morning, Younes opens one web app, on his PC or phone, and sees the new
English-language, entry-level tech jobs in the Netherlands, mostly from companies that can
sponsor a visa. He marks the ones he applied to and tracks their status.

"Sponsor" means a company on the IND public register of recognised sponsors, the Dutch
immigration service's list of employers allowed to hire on a skilled-migrant visa.

## 2. Decisions already made

| Topic | Decision | Decided |
|---|---|---|
| Where jobs are read | The web app. Not the Google Sheet | 2026-11-10 |
| Where the daily run happens | On Younes's PC | 2026-11-10 |
| Phone use | The web app must be mobile-friendly | 2026-11-10 |
| Non-sponsor jobs | Kept and labelled; hidden by default | 2026-11-10 |
| CV and cover letter generation | Not in the MVP. Code stays, untouched and untested | 2026-11-10 |
| Morning email summary | Wanted, but after the MVP | 2026-11-10 |
| Big employers (ASML, Booking.com, ABN AMRO and others) | In the MVP: they matter most and post the most jobs | 2026-11-10 |
| Main job source | `targets.csv`, the hand-reviewed company list | ADR-0005, ADR-0006 |
| Job-board sites (RemoteOK, Arbeitnow) | Kept alongside the target list | ADR-0003 |
| Jobs from companies already applied to | Never hidden by company; only the exact same job is hidden | 2026-10-30 |

## 3. Requirements

### Finding jobs (the pipeline: the Python program that collects jobs)

**P1. Sources.** One run fetches every `targets.csv` row whose `board_status` is `auto` or
`hand`, plus RemoteOK, Arbeitnow and the boards in `scrapers/company_pages.py`.
*Check:* the run log names every board it tried, with the number of jobs fetched and kept.

**P2. Filters.** A job is kept only if it passes all four existing rules in `filters.py`:
tech word in the title, no seniority word in the title and no 5+ years asked, a Dutch
location (or plain "Remote"), and not written in Dutch. The rules themselves do not change
in the MVP.
*Check:* `python -m pytest` passes, including the existing filter tests.

**P3. No repeats.** A job seen in an earlier run is not added again, whether it comes back
with the same link or as the same company and title from another source.
*Check:* running the pipeline twice in a row adds zero rows the second time.

**P4. Sponsor label.** Every job is labelled `Yes` or `No`. A job from a target-list
company is labelled using that row's `ind_registered_name`. When the same job arrives from
both the target list and a job-board site, the target-list copy is the one kept.
*Check:* a test with one job present in both sources ends with one row, labelled `Yes`.
(This fixes the known Stream case.)

**P5. Failures are visible.** A board that fails (page not found, time-out, network down)
does not stop the run. Each run writes a summary file with: start and end time, jobs
added, and the list of boards that failed with the reason.
*Check:* a test with one board forced to fail still completes, and the summary lists that
board. (Valtech's board, currently "not found", must either be fixed or show up here.)

**P6. Run time.** A full run finishes in 15 minutes or less on Younes's PC. It takes about
55 minutes today, nearly all spent on Workday boards (Workday is the careers-site software
used by banks and large companies).
*Check:* the summary file from a full run shows 15 minutes or less.

**P7. No job rows in the Google Sheet.** The pipeline stops writing jobs to the Sheet.
Jobs live in `data/jobs.csv` only.
*Check:* a full run makes no Google Sheets request.

**P8. Runs every morning by itself.** A Windows scheduled task (Windows' built-in timer for
running programs) starts the pipeline each weekday morning without Younes doing anything.
*Check:* the task exists, and a summary file dated that morning appears without a manual run.

**P9. Big employers.** Jobs from these eleven employers are fetched in every run. First
priority: ASML, Booking.com, ABN AMRO, Rabobank. Then: Heineken, Signify, TomTom, Ahold
Delhaize, HSBC, DSM (dsm-firmenich), AkzoNobel. Each gets a `targets.csv` row with status
`hand`, after confirming by hand that the board belongs to the right company. Several run
their own careers sites instead of one of the six supported kinds, so new fetchers are
expected.
*Check:* the summary file of a full run lists each of the eleven with at least one job
fetched (counted before filtering). If an employer's site cannot be read by a program
(it blocks automated access, or its terms forbid it), the builder stops and reports that
employer to Younes, who decides. The MVP is not done until all eleven are either fetched
or decided by him.

### The web app

**W1. One command to start.** A single command or double-click starts both halves of the
app (the Python part that serves the data and the React part that draws the pages).
*Check:* from a fresh terminal, that one command leads to a working page at the printed address.

**W2. Job list.** Shows every job in `data/jobs.csv`, newest first. Each card shows title,
company, location, date found, sponsor label, and a link to the posting.
*Check:* the count on the page equals the number of rows in the file with all filters off.

**W3. What is new.** Jobs added by the most recent run are visibly marked as new.
*Check:* after a run that adds jobs, exactly those jobs carry the marker.

**W4. Filters.** The existing five filters stay (role type, entry-level only, no Dutch
required, sponsors only, MSc-friendly). **Sponsors only** is on by default.
*Check:* on first load, no job labelled `No` is visible; switching the filter off shows them.

**W5. Application tracker.** "Mark as applied" moves a job to the tracker page, where its
status can be changed (Applied, Waiting for answer, Got interview, Rejected, Ghosted,
Withdrawn). Tracker data is stored in the "Applications" tab of the Google Sheet, with the
existing fallback to browser storage when the Sheet cannot be reached.
*Check:* mark a job, reload the page: it is on the tracker page and gone from the job list.

**W6. Mobile-friendly.** At a phone-sized screen (375 pixels wide) every page is usable:
no sideways scrolling, filters reachable, buttons large enough to tap.
*Check:* both pages checked in a browser at 375 pixels wide, with screenshots.

**W7. Reachable from the phone at home.** With the PC on, the app opens on a phone
connected to the same Wi-Fi.
*Check:* Younes opens the printed address on his phone and sees the job list.

**W8. Last run status.** The app shows when the pipeline last ran and how many boards
failed, read from the summary file of P5.
*Check:* the time shown matches the latest summary file.

### Quality

**Q1.** `python -m pytest` passes before every commit.
**Q2.** Every new pipeline rule or bug fix comes with a test.
**Q3.** Tests never call the real Google Sheet or real job boards.
**Q4.** The GitHub job no longer runs the pipeline; it runs the tests whenever code is pushed.
**Q5.** `README.md` and the "Project" section of `CLAUDE.md` describe the app as it
actually works when the MVP is done.

## 4. Not in the MVP

- CV and cover letter generation (code stays as it is)
- Morning email summary (first thing after the MVP)
- Using the app on the phone away from home (needs the app hosted on the internet)
- Resolving the 19 `review` rows and re-probing `none` rows in `targets.csv`
- dbt, databases, or any change of storage away from the CSV file

## 5. Rules for whoever builds this

- Work on a branch named `mvp`. Do not push to `master`; Younes merges.
- Do not change the filter rules or anything in section 4. Change `targets.csv` only where
  P5 or P9 needs it.
- Manual edits by Younes are the intended direction: build on them, never revert them.
- A design choice not covered here gets a short ADR in `docs/adr/` before it is built.
- When a requirement cannot be met as written, stop and report; do not quietly do
  something close to it.

## 6. Confirmed details

Proposed by Claude and confirmed by Younes on 2026-11-10:

1. **P6:** the limit is 15 minutes.
2. **P8:** the run starts at 08:00 on weekdays.
3. **Section 5:** work lands on the `mvp` branch and Younes merges it.
4. **Q4:** the GitHub job only runs the tests.
5. **W3:** "new" means added by the most recent run, not "new since you last looked".
