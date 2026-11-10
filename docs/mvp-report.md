# MVP report

Written 2026-11-10 for task 19 of `docs/tasks.md`. It checks every requirement in
`docs/requirements.md` against its **check** (the test that proves it is met).

Results: **PASS** = the check passed. **FAIL** = it did not. **WAITING** = the work is done
but the check (or a decision) can only be done by Younes.

## Summary

| Result | Count | Requirements |
|---|---|---|
| PASS | 18 | P1-P7, W1-W6, W8, Q1-Q3, Q5 |
| FAIL | 0 | |
| WAITING | 4 | P8, P9, W7, Q4 |

**State of the MVP.** The pipeline (the Python program that collects jobs) runs end to end
on this PC in about 5 minutes (329 s in the latest run, limit 15 minutes), tries 192
boards (188 answered, 4 failed), writes jobs to `data/jobs.csv` only, and writes a run summary to
`data/last_run.json` that lists every board and every failure. Ten of the eleven big
employers are fetched; Rabobank blocks programs, so it needs Younes's decision. The web app
starts with one command, shows the jobs with sponsors-only on by default, marks new jobs,
shows the last run, tracks applications in the Google Sheet, and fits a phone screen. All
104 tests pass. What is left is four things only Younes can do: decide on Rabobank, check
the app on his phone, register the daily Windows task, and push `mvp` so GitHub runs the
tests. The five new design records (ADR-0007 to ADR-0011) are still "proposed" and wait
for his sign-off.

### What Younes needs to do, in order

Decisions (no typing needed, just an answer):

1. **Rabobank (P9).** Every Rabobank careers site answers "403 forbidden" from an Akamai
   bot wall (a service that blocks programs). Choose: drop Rabobank from P9, give another
   route to its jobs, or accept it as not fetched. P9 passes once you decide.
2. **"Fetched" means Dutch listings (ADR-0008, 0009, 0010).** Workday, Booking.com, ABN
   AMRO and several of the new fetchers ask the site for Netherlands jobs only. Confirm that
   this country filter on the site's side does not count as "filtering" for P9.
3. **Sign off ADR-0007 to ADR-0011** (all in `docs/adr/`, status "proposed"): run summary
   file, Workday Netherlands filter, Jibe/GetNoticed fetchers, fetchers for the other seven
   employers, and what counts as "new".
4. **ASML robots.txt.** It disallows the board's web pages; the pipeline reads only the
   JSON API (the data address the page itself uses), which is not disallowed. Say if you
   read this as a refusal.
5. **Smaller choices, any time:** relabel old `No` rows when a target list later finds the
   same job (cross-run labels); look up NXP's new board; Ahold Delhaize listing also Albert
   Heijn, Etos and Gall & Gall jobs; Heineken descriptions (about +3.7 minutes per run);
   the tracker's UTC date fix and a "remove application" option; clean up code/doc
   leftovers (see the last section).

Actions (things to run or look at):

1. **Phone check (W7).** Run `powershell -ExecutionPolicy Bypass -File .\start.ps1`, open
   the green "On a phone" address on a phone on the same Wi-Fi, confirm the job list loads.
   If it does not, add the firewall rule given in `docs/tasks.md`. Then tick task 10.
2. **Register the daily task (P8).** Paste the command under "Task 17" in `docs/tasks.md`
   into a normal PowerShell window. The next weekday after 08:00, check that
   `data\last_run.json` has that morning's `started_at` and a new `logs\run_<date>_HHmm.log`
   ends in `exit code 0`. Then move the command into the README (task 18 note).
3. **Push `mvp` (Q4)** and check the "Tests" workflow goes green on GitHub's Actions tab.
   Optional: delete the unused Sheets secrets and old caches there.
4. **Merge `mvp` into `master`** when you are happy (section 5: only you merge).

## Requirements

Evidence for the latest real run is `data/last_run.json`: started 2026-11-10 16:43:29,
finished 16:48:58, status `completed`, 329 s, 192 boards tried (188 answered, 4 failed), 8 jobs added (run
through `run_daily.ps1`, log `logs/run_2026-11-10_1643.log` ends `exit code 0`). The test
suite was re-run for this report: `venv\Scripts\python.exe -m pytest -q` gives
**104 passed** (2 warnings, see last section).

### Finding jobs (the pipeline)

Checks, quoted word for word from `docs/requirements.md`:

- **P1.** *Check:* the run log names every board it tried, with the number of jobs fetched and kept.
- **P2.** *Check:* `python -m pytest` passes, including the existing filter tests.
- **P3.** *Check:* running the pipeline twice in a row adds zero rows the second time.
- **P4.** *Check:* a test with one job present in both sources ends with one row, labelled `Yes`.
  (This fixes the known Stream case.)
- **P5.** *Check:* a test with one board forced to fail still completes, and the summary lists that
  board. (Valtech's board, currently "not found", must either be fixed or show up here.)
- **P6.** *Check:* the summary file from a full run shows 15 minutes or less.
- **P7.** *Check:* a full run makes no Google Sheets request.
- **P8.** *Check:* the task exists, and a summary file dated that morning appears without a manual run.
- **P9.** *Check:* the summary file of a full run lists each of the eleven with at least one job
  fetched (counted before filtering). If an employer's site cannot be read by a program
  (it blocks automated access, or its terms forbid it), the builder stops and reports that
  employer to Younes, who decides. The MVP is not done until all eleven are either fetched
  or decided by him.

| ID | Requirement | Result | Evidence |
|---|---|---|---|
| P1 | One run fetches every `auto`/`hand` row of `targets.csv`, plus RemoteOK, Arbeitnow and `company_pages.py` | PASS | Commit 4c4feb8. Latest `last_run.json` lists the 188 boards that answered, each with `fetched` and `kept`, and the 4 that failed under `failed` with the reason: 192 tried. Reading "run log" = console output plus that list is ADR-0007, still awaiting sign-off. |
| P2 | Keep a job only if it passes the four existing rules in `filters.py`; rules unchanged | PASS | 104 passed today, including 24 tests in `tests/test_filters.py`. `filters.py` not changed on `mvp` (the "NLD" spelling fix is in the fetchers). |
| P3 | A job seen in an earlier run is not added again (same link, or same company and title from another source) | PASS | Commit a2a7612; `test_second_run_with_same_jobs_adds_zero_rows`, `test_second_run_same_posting_from_another_source_adds_nothing`, `test_dedup_drops_posting_seen_in_earlier_run`. Proven with a test on fake data, not two back-to-back live runs (live sites change between runs: the 16:43 run added 8 genuinely new jobs). |
| P4 | Every job labelled `Yes`/`No`; target-list copy wins a duplicate | PASS | Commit aecdcef; `test_dedup_keeps_target_copy_labelled_yes_in_either_order`, `test_sponsor_status_prefers_registered_name`. `jobs.csv` today: 395 rows, all labelled (361 `Yes`, 34 `No`). Only within one run; see the cross-run note below. |
| P5 | A failing board does not stop the run; summary has start/end time, jobs added, failed boards with reason | PASS | Commit 4c4feb8; `test_failed_board_still_completes_and_is_in_summary`, `test_whole_source_crash_does_not_stop_run`, `test_summary_written_when_run_crashes`, four tests in `test_sources.py`. Live: 4 failures listed with reasons (NXP 422, Payconiq/50five/Leiden University 404). Valtech works again (task 5, commit 22cc856). |
| P6 | Full run in 15 minutes or less | PASS | Task 9 run: 291 s (commit 1a612de). Latest run: `duration_seconds` 329. Limit 900. Workday change (commit 269f6de) cut the 22 Workday boards from 2950 s to 88 s. |
| P7 | Pipeline writes no jobs to the Google Sheet | PASS | Commit 18dce3a; `test_run_makes_no_google_sheets_request`, `test_pipeline_has_no_sheet_writer`. Grep today: no `gspread` in `main.py`, `output.py` or `scrapers/`; only the tracker in `api.py` uses the Sheet. |
| P8 | A Windows scheduled task starts the pipeline every weekday morning | WAITING | `run_daily.ps1` built and tested (commit edfb9f2, 7 tests in `test_run_daily.py`). `Get-ScheduledTask -TaskName 'Job Pipeline daily'` today: not found, so not registered. **Younes:** register it with the command in `docs/tasks.md`, then check the next weekday morning. |
| P9 | The eleven big employers are fetched in every run | WAITING | Commits 6891378, 892db7c. Latest run, fetched (kept): ASML 137 (68), Booking.com 59 (6) via Jibe plus 19 (0) via its careers page, ABN AMRO 130 (14), Heineken 58 (44), Signify 16 (4), TomTom 26 (4), Ahold Delhaize 85 (2), HSBC 1 (0), DSM-Firmenich 9 (0), AkzoNobel 15 (2). Rabobank: blocked. **Younes:** decide on Rabobank, and confirm "fetched = Dutch listings" (ADR-0008/9/10). |

### The web app

Checks, quoted word for word from `docs/requirements.md`:

- **W1.** *Check:* from a fresh terminal, that one command leads to a working page at the printed address.
- **W2.** *Check:* the count on the page equals the number of rows in the file with all filters off.
- **W3.** *Check:* after a run that adds jobs, exactly those jobs carry the marker.
- **W4.** *Check:* on first load, no job labelled `No` is visible; switching the filter off shows them.
- **W5.** *Check:* mark a job, reload the page: it is on the tracker page and gone from the job list.
- **W6.** *Check:* both pages checked in a browser at 375 pixels wide, with screenshots.
- **W7.** *Check:* Younes opens the printed address on his phone and sees the job list.
- **W8.** *Check:* the time shown matches the latest summary file.

| ID | Requirement | Result | Evidence |
|---|---|---|---|
| W1 | One command starts both halves of the app | PASS | Commit 1627b84: `start.ps1` starts the API and the Vite dev server (the program that serves the React pages), prints the addresses, stops both on exit. Checked by the builder and reviewer in task 10; task 10 is open only for the phone check (W7). Not re-run for this report. |
| W2 | Job list shows every job, newest first, with title, company, location, date found, sponsor label, link | PASS | Commit 13ff434 (task 13, reviewed): card shows every field. The page's total is `jobs.length` (`frontend/src/pages/JobBrowser.jsx` line 128, "{filtered.length} of {jobs.length} jobs"), and `/api/jobs` returns every row of `jobs.csv` unfiltered. `docs/screenshots/jobs-1280.png` (taken 15:01, after the 14:40 run) shows "354 of 387 jobs". `jobs.csv` has 395 rows today; the 16:43 run added 8 (`jobs_added` 8; the file is append-only), so it had 395 - 8 = 387 rows when the screenshot was taken: the page total equals the file's rows. Task 13's live check with all filters off showed 386 of 387; the 1 hidden was a job marked applied, which W5 requires to leave the job list (the screenshot's "3 applied hidden" is the same rule). Not re-checked in a browser after the 16:43 run. |
| W3 | Jobs added by the latest run are marked new | PASS | Commit e59e038, ADR-0011; `test_jobs_marks_last_run_rows_new`, `test_jobs_two_runs_same_day_marks_only_latest`, and 13 more edge-case tests in `test_api.py` (`pytest --collect-only` collects 15 `test_jobs_*` tests, counting each parameter case of `test_jobs_unreadable_summary`). |
| W4 | The five filters stay; Sponsors only on by default | PASS | Commit 13ff434; `frontend/src/constants/filters.js` line 29 `indSponsor: true`. 34 `No` rows exist to show when switched off. |
| W5 | Mark as applied moves a job to the tracker; status can change; stored in the Sheet's "Applications" tab with browser-storage fallback | PASS | Commit 6d1c0a0: checked live on the real Sheet in two browser profiles, test row then removed. Tests `test_tracker_mark_applied_then_reload`, `test_tracker_status_change_updates_only_that_row`, `test_tracker_sheet_unreachable_returns_503`. |
| W6 | Usable at 375 px wide: no sideways scroll, filters reachable, buttons tappable | PASS | Commit de27111; `docs/screenshots/jobs-375.png`, `jobs-375-filters.png`, `tracker-375.png`, plus `jobs-1280.png` (desktop). |
| W7 | App opens on a phone on the same Wi-Fi | WAITING | Commit 1627b84: Vite listens on the network (`host: true` in `frontend/vite.config.js`). **Younes:** do the phone check (actions list, step 1). |
| W8 | App shows when the pipeline last ran and how many boards failed | PASS | Commit aa7c9eb; `test_last_run_returns_summary`, `test_last_run_is_read_at_request_time` (file read on every request, so it always shows the newest run), plus missing/broken-file tests. |

### Quality

These have no separate check; each requirement is its own check. Quoted word for word from
`docs/requirements.md`:

- **Q1.** `python -m pytest` passes before every commit.
- **Q2.** Every new pipeline rule or bug fix comes with a test.
- **Q3.** Tests never call the real Google Sheet or real job boards.
- **Q4.** The GitHub job no longer runs the pipeline; it runs the tests whenever code is pushed.
- **Q5.** `README.md` and the "Project" section of `CLAUDE.md` describe the app as it
  actually works when the MVP is done.

| ID | Requirement | Result | Evidence |
|---|---|---|---|
| Q1 | `python -m pytest` passes before every commit | PASS | Each task ran the tests before the coordinator committed; today 104 passed. |
| Q2 | Every new pipeline rule or bug fix has a test | PASS | Each `mvp` code commit has tests: summary/failures (`test_main.py`, `test_sources.py`), dedup (`test_output.py`), Workday (`test_workday.py`), new fetchers (`test_new_fetchers.py`, `test_more_fetchers.py`), API (`test_api.py`), daily script (`test_run_daily.py`). Task 5 and 15 needed no code fix. |
| Q3 | Tests never call the real Sheet or real job boards | PASS | Network calls are replaced with fakes (`monkeypatch` of `requests.get` and the fetchers, e.g. `tests/test_sources.py` line 2); the tracker tests fake the Sheet. The GitHub job has no Sheets secrets. |
| Q4 | GitHub job runs the tests on push, not the pipeline | WAITING | Commit eab2bf7: `.github/workflows/daily.yml` is now "Tests", `on: push`, runs `python -m pytest -q` only. **Younes:** push `mvp` and see it go green; nothing has been pushed yet. |
| Q5 | `README.md` and CLAUDE.md "Project" describe the app as it works | PASS | Commit d4f48a0. Note: the README points to `docs/tasks.md` for the scheduled-task command until P8 is registered. |

## Known limitations and follow-ups

None of these block the MVP; most are already listed under "Waiting for Younes".

- **Rabobank** not fetched (bot wall). See P9.
- **HSBC near zero.** It fetched 1 Dutch listing (0 kept) in both full runs, so some days it
  will show 0 and P9's "every run" can fail for HSBC through no fault of the code.
- **Heineken has no descriptions.** Jobs are judged on title and location only, so
  Dutch-language or 5+-years jobs can slip through (44 of 58 kept in the latest run, a much
  higher share than other employers). Fetching descriptions adds about 3.7 minutes per run;
  there is room inside the 15 minutes.
- **Dead boards.** NXP's Workday board answers 422 (its careers page 500). Payconiq, 50five
  and Leiden University's Recruitee boards answer 404. All show under `failed`, as P5 wants;
  fixing them means editing `targets.csv`.
- **Ahold Delhaize** includes Albert Heijn, Etos and Gall & Gall jobs under its own name.
- **Cross-run sponsor labels.** A job saved earlier from a job board keeps its `No` label if a
  target list finds it later, because P3 forbids adding it again.
- **"Fetched" counts Dutch listings** for boards that filter by country on the site side
  (ADR-0008/9/10, awaiting sign-off).
- **Tracker date bug.** A job marked applied between 00:00 and 01:00 Dutch time (02:00 in
  summer) gets yesterday's date, because `TrackerContext.jsx` line 72 uses the UTC date (UTC
  = world standard time, one or two hours behind the Netherlands). One-line fix.
- **No way to remove an application** from the tracker, in the app or the API.
- **Starlette deprecation warning.** The test run warns that using `httpx` with Starlette's
  TestClient (the fake browser the API tests use) is deprecated; a future release may need
  `requirements.txt` updated.
- **Code/doc leftovers:** unused `IND_REGISTER_URL` and stale comments in `config.py`;
  `main.py` line 55 prints "Fetching jobs from Indeed RSS..." but fetches RemoteOK and
  Arbeitnow; ADR-0005 mentions a `url` source kind that does not exist; two `targets.csv`
  rows (Ncardia, Tech Rise People) have a blank status.
- **GitHub clean-up:** unused Sheets secrets and old `seen-jobs-*` / `ind-register-*` caches.
- **After the MVP (section 4):** morning email summary, CV/cover-letter generation, phone
  use away from home, the `review` rows in `targets.csv` (section 4 says 19; the file has 21
  today).
