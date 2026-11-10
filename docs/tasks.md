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
- [!] **9. Full timed run** (P6, P9). Run the whole pipeline once. The summary must show
  15 minutes or less and at least one job fetched from each of the eleven big employers.

## Web app

- [!] **10. One command to start, reachable on home Wi-Fi** (W1, W7). **Younes** (phone check)
  New `start.ps1`; `frontend/vite.config.js` (listen on the network, not only this PC);
  `api.py` if needed. The script prints the address to open on the phone.
- [x] **11. Last run status** (W8). Files: `api.py`, `frontend/src/App.jsx`.
- [ ] **12. Mark new jobs** (W3). **plan** Files: `api.py`, `frontend/src/components/JobCard.jsx`.
- [ ] **13. Sponsors-only on by default; card shows all required fields** (W2, W4).
  Files: `frontend/src/constants/filters.js`, `frontend/src/components/JobCard.jsx`.
- [ ] **14. Phone layout** (W6). Files: `JobBrowser.jsx`, `FilterBar.jsx`, `Tracker.jsx`.
  Check both pages at 375 pixels wide and save screenshots to `docs/screenshots/`.
- [ ] **15. Tracker check** (W5). Mark a job as applied, reload, confirm. Fix what fails.

## Wrap-up

- [ ] **16. GitHub job runs tests only** (Q4). Files: `.github/workflows/daily.yml`.
- [ ] **17. Windows scheduled task** (P8). **Younes**
  New `run_daily.ps1` that runs the pipeline and keeps a log. Write the exact command that
  registers the task for weekdays at 08:00, but do not run it: list it below for Younes.
- [ ] **18. Documentation** (Q5). `README.md` and the "Project" section of `CLAUDE.md`.
- [ ] **19. Final report.** `docs/mvp-report.md`: every requirement, its check, pass or fail.

## Waiting for Younes

- **ADR-0007 sign-off** (`docs/adr/0007-run-summary-file.md`, status "proposed"). Three readings to
  confirm or overrule: "kept" counts jobs that passed the filters at a board, before removing
  repeats from earlier runs; P1's "run log" is the console output plus the `boards` list in
  `data/last_run.json`; the file also records `duration_seconds` (read by task 9's 15-minute check).
- **FYI, cross-run labels (task 3).** P4 is handled within one run. A job already saved from a job
  board on an earlier day keeps its `No` label when the target list later finds it, because P3
  forbids re-adding it. Same if a target board fails on the day a job board lists the job. Say if
  you want old rows relabelled.
- **NXP's Workday board is down (found in task 6).** Its careers page returns 500 and the jobs API
  returns 422, before any change of ours. It shows under `failed` in the run summary, which meets
  P5. Say if you want its new board looked up (that means editing `targets.csv`).
- **ADR-0008 sign-off (task 6).** Workday boards are now asked for Netherlands jobs only, so for
  them "fetched" counts the board's Dutch listings, not every listing worldwide. Confirm this
  server-side country filter does not count as "filtering" for P9's "at least one job fetched".
- **Rabobank is blocked (task 7, P9 stop rule).** Every Rabobank careers site (`rabobank.jobs`,
  `rabobank.com/careers`, `rabobank.nl/werken-bij`, even their robots.txt) answers 403 from an
  Akamai bot wall, and no public job-board system was found. Its `targets.csv` row is left as
  `none`. Your call: drop Rabobank from P9, give another route, or accept it as not fetched.
- **ASML robots.txt (task 7, went ahead).** `asml.wd3.myworkdayjobs.com/robots.txt` disallows
  `/ASMLEXT1/` (the board's web pages). The pipeline reads only the JSON API at
  `/wday/cxs/asml/ASMLEXT1/...`, which is not disallowed, as with the other 22 Workday boards.
  Say if you read the rule as a refusal and want ASML held.
- **ADR-0009 sign-off (task 7).** New source kinds `jibe` (Booking.com) and `getnoticed`
  (ABN AMRO). Both ask for Netherlands jobs only, so "fetched" means Dutch listings, the same
  open question as ADR-0008.
- **ADR-0010 sign-off (task 8).** Four new source kinds: `lever_eu` (TomTom), `eightfold` (HSBC,
  DSM-Firmenich), `phenom` (AkzoNobel), `heineken` (its own site, read as HTML). Same open
  "fetched = Dutch listings" question as ADR-0008/0009.
- **Ahold Delhaize includes its brands (task 8).** `careers.aholddelhaize.com` also lists Albert
  Heijn, Etos and Gall & Gall jobs (75 of 145 are Albert Heijn); they appear under "Ahold
  Delhaize". The site's brand filter returns a server error, so they can't be split cheaply.
  Albert Heijn's own row stays `none`. Say if that's not fine.
- **Heineken jobs have no description (task 8).** Descriptions sit on each job page, and the
  site's 5-second crawl delay would add about 3.7 minutes per run (about 44 jobs x 5 s). Without them, Heineken jobs are
  judged on title and location only, so Dutch-language or 5+-years jobs may slip through.
  Suggest deciding after task 9 shows how much of the 15 minutes is left.
- **FYI: "NLD" is spelled out (task 8).** Ahold Delhaize and AkzoNobel give locations like
  "Zaandam, NLD", which the location filter rejects. The fetchers now write "Netherlands" for
  "NLD"; `filters.py` is untouched. Without this nearly all their Dutch jobs would be dropped.
- **Task 9 blocked on Rabobank.** Full run on 2026-11-10: completed in 291 s (P6 passes, limit
  900), 284 jobs added, 188 boards, 4 failed. 10 of the 11 big employers fetched at least one job;
  Rabobank is missing because it is blocked (see above). P9 passes once you decide on Rabobank.
  HSBC fetched only 1, so it may show 0 on some days. Other failures, none a big employer: NXP
  (422, known), and Payconiq, 50five and Leiden University, whose Recruitee boards now answer 404.
- **Task 10: phone check (W7).** Built, reviewed and committed; only your phone check is left.
  Run `powershell -ExecutionPolicy Bypass -File .\start.ps1` in the repo folder, open the green
  "On a phone" address it prints (today `http://192.168.178.28:5173`) on a phone on the same
  Wi-Fi, and check the job list loads. If it doesn't, run once in an administrator PowerShell:
  `New-NetFirewallRule -DisplayName "Job pipeline web app (5173)" -Direction Inbound -Protocol TCP -LocalPort 5173 -Action Allow -Profile Private,Public`
  (or set the home Wi-Fi to Private in Windows and use `-Profile Private` only). Then tick task 10.
