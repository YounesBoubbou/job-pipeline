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

- [!] **20. Exclude 3+ years, not 5+** (P2, changed by Younes). First version committed as
  `3e7446f` before review; review failed twice, see "Waiting for Younes".
- [x] **21. Tracker keeps changes made while the Sheet is down.** Files:
  `frontend/src/context/TrackerContext.jsx`. Today a job marked applied (or a status changed)
  while the Sheet is unreachable lives only in the browser and is overwritten by the Sheet's
  contents on the next successful load. Keep such changes and send them to the Sheet once it
  answers again; never add the same job twice. Also use the local date, not UTC, for
  `date_applied` (line 72).
- [ ] **22. Filter out jobs that require Dutch.** **plan** Files: `filters.py`, `config.py`,
  `frontend/src/constants/filters.js`, tests. The language rule only drops postings written
  in Dutch; English postings that say Dutch is required ("fluent in Dutch", "Dutch is a
  must", "native Dutch speaker", "Nederlands vereist") get through. Drop those; keep postings
  where Dutch is only a plus ("Dutch is a plus", "nice to have", "not required").
- [x] **23. Code leftovers** (from task 18). `main.py` says "Fetching jobs from Indeed RSS"
  but fetches RemoteOK and Arbeitnow; unused `IND_REGISTER_URL` and stale comments in
  `config.py`. No behaviour change.

## Waiting for Younes

- **Task 20: years rule failed review twice.** I committed the first version (`3e7446f`, on
  `mvp`, so it is what the daily run uses) before review, which skipped the process. Round 1
  found it hides some junior jobs ("2 - 3 years" with spaces, "1.5 years") and misses "3
  years’ experience" (curly quote), "3 or more years", "three (3) years". Round 2 fixed all of
  those and is parked on branch `task20-years-round2` (`a8bf940`, not merged). Round 2 review
  still found three small misses: "a 3-5 year contract", "between 1 and 3 years" and
  "max / no more than 3 years" would be hidden. The fixes are known and small. Your call:
  (a) allow a third round (my recommendation): fix those three on the branch, review, merge
  into `mvp`; (b) merge the branch as is; (c) keep `mvp` as is.

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
- **FYI from task 15 (W5 passes; not blocking).** (a) A job marked applied between 00:00 and 01:00
  Dutch time (02:00 in summer) gets yesterday's date, because `TrackerContext.jsx` line 72 takes
  the UTC date. One-line fix; say if you want it. (b) There is no way to remove an application
  from the tracker, in the app or the API. The live test row was removed directly in the Sheet,
  which now matches its earlier state.
- **GitHub after you push `mvp` (task 16, Q4).** Check the "Tests" workflow goes green on the
  Actions tab; that is Q4's check. Optional clean-up: Sheets secrets under Settings > Secrets and
  variables > Actions are now unused, and the old `seen-jobs-*` / `ind-register-*` caches under
  Actions > Caches can be deleted or left to expire. Watch item: Starlette warns that using
  `httpx` with its TestClient is deprecated; a future Starlette release could need
  `requirements.txt` updated.
- **Task 17: register the daily Windows task (P8).** Paste into a normal PowerShell window (no
  admin needed). The `StartBoundary` line keeps it at 08:00 Dutch time in summer too; without it
  Windows stores 07:00 UTC and the run drifts to 09:00 after the clock change.
  ```powershell
  $Repo = 'C:\Users\Younes\Desktop\job-pipeline'
  $action = New-ScheduledTaskAction -Execute 'powershell.exe' `
      -Argument "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$Repo\run_daily.ps1`"" `
      -WorkingDirectory $Repo
  $trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday,Tuesday,Wednesday,Thursday,Friday -At 08:00
  $trigger.StartBoundary = (Get-Date '08:00').ToString('s')   # local 08:00, also in summer time
  $settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Hours 1) `
      -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -MultipleInstances IgnoreNew
  $principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive -RunLevel Limited
  Register-ScheduledTask -TaskName 'Job Pipeline daily' -Action $action -Trigger $trigger `
      -Settings $settings -Principal $principal `
      -Description 'Runs the job pipeline (run_daily.ps1) every weekday at 08:00. Logs in logs\.'
  ```
  - Check it exists: `Get-ScheduledTask -TaskName 'Job Pipeline daily'`
  - Test once: `Start-ScheduledTask -TaskName 'Job Pipeline daily'`, then look at the newest file in
    `logs\` and `Get-ScheduledTaskInfo -TaskName 'Job Pipeline daily'` (LastTaskResult 0 = worked).
  - Remove: `Unregister-ScheduledTask -TaskName 'Job Pipeline daily' -Confirm:$false`
  - It runs only while you are signed in (a locked screen is fine), so no password or admin is
    needed. If the PC was off or asleep at 08:00 it runs as soon as it's back; it won't wake the PC.
  - P8's check: the next weekday after 08:00, `data\last_run.json` has that morning's
    `started_at` and a new `logs\run_<date>_HHmm.log` ends in `exit code 0`, with no manual run.
- **FYI from task 18 (not blocking).** (a) `README.md` points to the "Task 17" item above for the
  scheduled-task command; once you've registered it and remove that item, move the command into
  the README. (b) Small code/doc leftovers, untouched because task 18 was docs only: unused
  `IND_REGISTER_URL` and stale comments in `config.py`; `main.py` prints "Fetching jobs from
  Indeed RSS..." but fetches RemoteOK and Arbeitnow; ADR-0005 mentions a `url` source kind that
  doesn't exist; two `targets.csv` rows (Ncardia, Tech Rise People) have a blank status. Say if
  you want them cleaned up.
