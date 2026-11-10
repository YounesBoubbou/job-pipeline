# Tasks: MVP

The ordered work list for `docs/requirements.md`. Work top to bottom. A task is ticked
only after the reviewer has passed it and it is committed on the `mvp` branch.

Marks: `[ ]` to do, `[x]` done, `[!]` blocked (reason goes under "Waiting for Younes").
**plan** means the planner agent writes a step plan first. **Younes** means the task
cannot be finished without him.

## Pipeline

- [x] **1. Stop writing job rows to the Sheet** (P7).
  Files: `main.py`, `output.py`, `config.py`. The tracker's use of the Sheet in `api.py` stays.
- [ ] **2. Run summary file** (P1, P5). **plan**
  Write `data/last_run.json` after every run: start and end time, jobs added, and per
  board the number fetched and kept, plus failed boards with the reason. A failing source
  never stops the run. `fetch_target_jobs` in `scrapers/targets.py` already collects
  `failed`; the job-board and company-page scrapers must report the same way.
- [ ] **3. Target-list copy wins a duplicate** (P4).
  Files: `output.py` (`deduplicate`, `_posting_key`). Test: one job from both sources ends
  as one row labelled `Yes`.
- [ ] **4. Test: a second run adds nothing** (P3). Files: `tests/test_output.py`.
- [ ] **5. Valtech board** (P5). Its Greenhouse token returns "not found". Find the right
  board and fix the row in `targets.csv`, or leave it failing and visible in the summary.
- [ ] **6. Workday speed** (P6). **plan**
  Files: `scrapers/targets.py` (`_workday`). Ask each Workday board for Netherlands jobs
  only instead of downloading every listing. Check each of the 22 boards still returns its
  Dutch jobs afterwards.
- [ ] **7. Big employers, first four** (P9). **plan**
  ASML, Booking.com, ABN AMRO, Rabobank. For each: find where its jobs are published, add
  a fetcher if it is not one of the six supported kinds, add the `targets.csv` row as
  `hand`. If a site refuses automated access, stop on that employer and list it below.
- [ ] **8. Big employers, other seven** (P9). **plan**
  Heineken, Signify, TomTom, Ahold Delhaize, HSBC, DSM (dsm-firmenich), AkzoNobel. Same rules.
- [ ] **9. Full timed run** (P6, P9). Run the whole pipeline once. The summary must show
  15 minutes or less and at least one job fetched from each of the eleven big employers.

## Web app

- [ ] **10. One command to start, reachable on home Wi-Fi** (W1, W7). **Younes** (phone check)
  New `start.ps1`; `frontend/vite.config.js` (listen on the network, not only this PC);
  `api.py` if needed. The script prints the address to open on the phone.
- [ ] **11. Last run status** (W8). Files: `api.py`, `frontend/src/App.jsx`.
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

Nothing yet.
