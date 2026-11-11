# Tasks: more companies covered

The ordered work list for `docs/requirements-coverage.md`. Work top to bottom, in the
worktree `C:\Users\Younes\Desktop\job-pipeline-coverage` on branch `coverage` (section 6).
A task is ticked only after the reviewer has passed it and it is committed on `coverage`.

Marks: `[ ]` to do, `[x]` done, `[!]` blocked (reason goes under "Waiting for Younes").
**plan** means the planner agent writes a step plan first. **Younes** means the task
cannot be finished without him.

## Phase A: the scan

- [x] **A-1. ADR for the scan** (Q4). `docs/adr/0013-careers-page-scan.md`: the new
  `targets.csv` columns (`website`, `careers_url`, `ats_seen`, `ats_evidence`, `scan_note`),
  the `ats_seen` values of A4, the politeness rules of A6, and how the scan resumes (A9).
- [x] **A-2. Scan script** (A2 step 1, A3, A4, A5, A6, A9). **plan** New `coverage_scan.py`
  at the repo root (same style as `ats_resolver.py`). Guess-and-verify websites, find the
  careers page, detect the system from links, frames, scripts and redirects, note
  `JobPosting` data, obey robots.txt and the request limits, save after every company and
  resume. Detection patterns for each system in A4 are confirmed on a real page before use.
  Tests with fake sites only.
- [x] **A-3. Run the scan** (A1). All 1,045 rows, in the background, worktree `data/` only.
  Read the log's failure list before trusting the result.
- [ ] **A-4. Websites by web search** (A2 step 2). Agent batches for rows with no website:
  address plus one line of evidence each. Then rerun the scan on just those rows.
- [ ] **A-5. Accuracy on known answers** (A7). Compare `ats_seen` with `source` on the 183
  `auto`/`hand` rows; at least 80% right where a website was found, at most 5 wrong
  board-reading kinds. Below that: fix the script, rerun, compare again.
- [ ] **A-6. Accuracy by hand** (A8). The reviewer checks 40 random rows in a browser
  (record the random pick); 36 or more must be right.
- [ ] **A-7. Scan report** (A10). `docs/coverage-scan-report.md`, plus README/CLAUDE.md (Q5).
  Then stop: phase B starts after Younes reads it.

## Phase B: boards on systems already read

Started early, before A-4 to A-7, by Younes's decision on 2026-11-11: the scan found 74
rows on systems we already read, and scored 45/183 on known rows against the 80% of A7
("lets add the 74 companies. thats still ok tbh"). A7 stays open; A-4 to A-7 follow.

- [x] **B-1. Fill and fetch the new boards** (B1, B2, B4, B5). **plan** For each row that is
  not `auto`/`hand` and whose `ats_seen` is one of the 12 kinds: token from `ats_evidence`
  (`token_from_evidence`), written to `source`/`token`; one fetch through `FETCHERS`;
  status by ADR-0006 (reuse `ats_resolver.py` logic); no token or a failed fetch leaves the
  row out with the reason in `scan_note`. Old `auto`/`hand` rows untouched (B5). Tests with
  fake boards. Run it in the worktree; attach the summary of that fetch.
- [x] **B-2. Settle review rows** (B3). Agent settles every `review` and blank row with
  evidence in `scan_note`; list 15 new `hand` rows for Younes to spot-check.
- [ ] **B-3. Full run timing** (T1). A full pipeline run in the worktree (its own `data/`,
  no Google Sheets write) in 30 minutes or less; parallel fetches across sites if needed.
- [ ] **B-4. Phase B report** for Younes, who merges `coverage` into `mvp`.

## Phase C: new readers

Written after Younes confirms the order from the phase A report (C1).

## Phase D: what is left

One task: `docs/coverage-final-report.md` (D1).

## Waiting for Younes

(nothing yet)
