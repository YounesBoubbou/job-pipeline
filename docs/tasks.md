# Tasks: MVP

The ordered work list for `docs/requirements.md`. Work top to bottom. A task is ticked
only after the reviewer has passed it and it is committed on the `mvp` branch.

Marks: `[ ]` to do, `[x]` done, `[!]` blocked (reason goes under "Waiting for Younes").
**plan** means the planner agent writes a step plan first. **Younes** means the task
cannot be finished without him.

## Pipeline

- [x] **1. Stop writing job rows to the Sheet** (P7).
  Files: `main.py`, `output.py`, `config.py`. The tracker's use of the Sheet in `api.py` stays.
- [x] **2. Run summary file** (P1, P5). **plan**
  Write `data/last_run.json` after every run: start and end time, jobs added, and per
  board the number fetched and kept, plus failed boards with the reason. A failing source
  never stops the run. `fetch_target_jobs` in `scrapers/targets.py` already collects
  `failed`; the job-board and company-page scrapers must report the same way.
- [x] **3. Target-list copy wins a duplicate** (P4).
  Files: `output.py` (`deduplicate`, `_posting_key`). Test: one job from both sources ends
  as one row labelled `Yes`.
- [x] **4. Test: a second run adds nothing** (P3). Files: `tests/test_output.py`.
- [x] **5. Valtech board** (P5). *Done 2026-11-10: the existing row works again (130 listings, 2 in
  Utrecht); no change needed. If it fails again it shows under `failed` in the run summary.* Its Greenhouse token returns "not found". Find the right
  board and fix the row in `targets.csv`, or leave it failing and visible in the summary.
- [x] **6. Workday speed** (P6). **plan**
  Files: `scrapers/targets.py` (`_workday`). Ask each Workday board for Netherlands jobs
  only instead of downloading every listing. Check each of the 22 boards still returns its
  Dutch jobs afterwards.
- [x] **7. Big employers, first four** (P9). **plan**
  ASML, Booking.com, ABN AMRO, Rabobank. For each: find where its jobs are published, add
  a fetcher if it is not one of the six supported kinds, add the `targets.csv` row as
  `hand`. If a site refuses automated access, stop on that employer and list it below.
  *Done: ASML, Booking.com, ABN AMRO fetched; Rabobank blocked, see below.*
- [x] **8. Big employers, other seven** (P9). **plan**
  Heineken, Signify, TomTom, Ahold Delhaize, HSBC, DSM (dsm-firmenich), AkzoNobel. Same rules.
- [x] **9. Full timed run** (P6, P9). Run the whole pipeline once. The summary must show
  15 minutes or less and at least one job fetched from each of the ten big employers.
  *Done 2026-11-11: 366 s, all ten fetched (Rabobank dropped by Younes).*

## Web app

- [x] **10. One command to start, reachable on home Wi-Fi** (W1, W7). **Younes** (phone check)
  New `start.ps1`; `frontend/vite.config.js` (listen on the network, not only this PC);
  `api.py` if needed. The script prints the address to open on the phone.
- [x] **11. Last run status** (W8). Files: `api.py`, `frontend/src/App.jsx`.
- [x] **12. Mark new jobs** (W3). **plan** Files: `api.py`, `frontend/src/components/JobCard.jsx`.
- [x] **13. Sponsors-only on by default; card shows all required fields** (W2, W4).
  Files: `frontend/src/constants/filters.js`, `frontend/src/components/JobCard.jsx`.
- [x] **14. Phone layout** (W6). Files: `JobBrowser.jsx`, `FilterBar.jsx`, `Tracker.jsx`, `JobCard.jsx`.
  Found in task 12: job cards overflow sideways at every width, desktop too; the badge row in
  `JobCard.jsx` (`shrink-0 flex-wrap`, ~line 83) never shrinks so never wraps. Fix for all widths.
  Check both pages at 375 pixels wide and save screenshots to `docs/screenshots/`.
- [x] **15. Tracker check** (W5). Mark a job as applied, reload, confirm. Fix what fails.

## Wrap-up

- [x] **16. GitHub job runs tests only** (Q4). Files: `.github/workflows/daily.yml`.
- [!] **17. Windows scheduled task** (P8). **Younes**
  New `run_daily.ps1` that runs the pipeline and keeps a log. Write the exact command that
  registers the task for weekdays at 08:00, but do not run it: list it below for Younes.
- [x] **18. Documentation** (Q5). `README.md` and the "Project" section of `CLAUDE.md`.
- [x] **19. Final report.** `docs/mvp-report.md`: every requirement, its check, pass or fail.

## Follow-ups after first use (Younes, 2026-11-10)

- [x] **20. Exclude 3+ years, not 5+** (P2, changed by Younes). First version committed as
  `3e7446f` before review; review failed twice. **Round 3 allowed by Younes (2026-11-11):**
  on branch `task20-years-round2`, fix "a 3-5 year contract", "between 1 and 3 years" and
  "max / no more than 3 years" (none of these may hide a job), review, merge into `mvp`.
  *Done 2026-11-11: passed review on the second try of round 3, merged.*
- [x] **21. Tracker keeps changes made while the Sheet is down.** Files:
  `frontend/src/context/TrackerContext.jsx`. Today a job marked applied (or a status changed)
  while the Sheet is unreachable lives only in the browser and is overwritten by the Sheet's
  contents on the next successful load. Keep such changes and send them to the Sheet once it
  answers again; never add the same job twice. Also use the local date, not UTC, for
  `date_applied` (line 72).
- [x] **22. Filter out jobs that require Dutch.** Merged as is on Younes's decision
  (2026-11-11) after two failed reviews. **plan** Files: `filters.py`, `config.py`,
  `frontend/src/constants/filters.js`, tests. The language rule only drops postings written
  in Dutch; English postings that say Dutch is required ("fluent in Dutch", "Dutch is a
  must", "native Dutch speaker", "Nederlands vereist") get through. Drop those; keep postings
  where Dutch is only a plus ("Dutch is a plus", "nice to have", "not required").
- [x] **23. Code leftovers** (from task 18). `main.py` says "Fetching jobs from Indeed RSS"
  but fetches RemoteOK and Arbeitnow; unused `IND_REGISTER_URL` and stale comments in
  `config.py`. No behaviour change.

- [x] **24. Heineken descriptions** (P2). **plan** Files: `scrapers/targets.py` (the
  `heineken` fetcher). Fetch each job's page for its description, obeying the site's
  5-second crawl delay, only for jobs that pass the title and location filters (as Workday
  does), so the Dutch and years rules apply to Heineken too. Report the extra run time.
  *Done 2026-11-11 (ADR-0012): live check 46 page fetches, 285 s for Heineken (was ~30 s),
  17 Dutch-language or Dutch-required jobs now dropped, 29 kept. Full run expected ~10.5 min.*
- [x] **25. NXP board** (P5). Its Workday board answers 422. Find where NXP now publishes
  jobs, confirm it is NXP, and fix its `targets.csv` row. If no readable board exists, set
  it to `none` and say so below. *Done 2026-11-11: moved to `nxp.myworkdayjobs.com/careers`
  (no `wd3.`), 39 Dutch jobs.*
- [x] **26. Three dead Recruitee boards** (P5). Payconiq, 50five and Leiden University answer
  404. Same as task 25 for each. *Done 2026-11-11: all three set to `none`, see below.*

## Waiting for Younes

- **FYI, three boards set to `none` (task 26).** Payconiq: the company is being renamed
  Bancontact Company (Belgian) and takes applications by e-mail. 50five: jobs are plain pages
  on its own site, applications by e-mail; reading it needs a new fetcher. Leiden University:
  now on `careers.universiteitleiden.nl`, which runs SAP SuccessFactors, a system the pipeline
  can't read yet (other universities may use it too). Say if you want either fetcher built.

- **Task 17: check tomorrow.** The task is registered (2026-11-11, daily 08:00). P8 passes
  when `data\last_run.json` shows a `started_at` after 08:00 on 2026-11-12 without a manual
  run, and the newest `logs\` file ends in `exit code 0`. Claude can check this.
- **FYI, cross-run labels (task 3).** A job already saved from a job board on an earlier
  day keeps its `No` label when the target list later finds it, because P3 forbids
  re-adding it. Say if you want old rows relabelled.
- **FYI, task 22 merged as is (2026-11-11).** Known misses: "our colleagues speak Dutch, but
  English is our working language", "Don't speak Dutch? No problem!", "If you speak Dutch,
  that's a plus", "Dutch is appreciated" are still dropped.
- **FYI, no way to remove an application from the tracker** (task 15), in the app or the
  API; delete the row in the Sheet.
- **GitHub after you push `mvp` (task 16, Q4).** Check the "Tests" workflow goes green on the
  Actions tab. Optional: the Sheets secrets under Settings > Secrets and variables > Actions
  are unused now, and old `seen-jobs-*` / `ind-register-*` caches can be deleted.
- **FYI, ASML robots.txt (task 7, went ahead).** `asml.wd3.myworkdayjobs.com/robots.txt`
  disallows the board's web pages (`/ASMLEXT1/`). The pipeline reads only the JSON API
  (`/wday/cxs/asml/ASMLEXT1/...`), which is not disallowed, as with the other Workday boards.
  Say if you read the rule as a refusal and want ASML held.
