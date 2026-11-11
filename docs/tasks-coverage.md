# Tasks: more companies covered

The ordered work list for `docs/requirements-coverage.md`. Work top to bottom, in the
worktree `C:\Users\Younes\Desktop\job-pipeline-coverage` on branch `coverage` (section 6).
A task is ticked only after the reviewer has passed it and it is committed on `coverage`.

Marks: `[ ]` to do, `[x]` done, `[!]` blocked (reason goes under "Waiting for Younes").
**plan** means the planner agent writes a step plan first. **Younes** means the task
cannot be finished without him.

## Phase A: the scan

- [ ] **A-1. ADR for the scan** (Q4). `docs/adr/0013-careers-page-scan.md`: the new
  `targets.csv` columns (`website`, `careers_url`, `ats_seen`, `ats_evidence`, `scan_note`),
  the `ats_seen` values of A4, the politeness rules of A6, and how the scan resumes (A9).
- [ ] **A-2. Scan script** (A2 step 1, A3, A4, A5, A6, A9). **plan** New `coverage_scan.py`
  at the repo root (same style as `ats_resolver.py`). Guess-and-verify websites, find the
  careers page, detect the system from links, frames, scripts and redirects, note
  `JobPosting` data, obey robots.txt and the request limits, save after every company and
  resume. Detection patterns for each system in A4 are confirmed on a real page before use.
  Tests with fake sites only.
- [ ] **A-3. Run the scan** (A1). All 1,045 rows, in the background, worktree `data/` only.
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

Written in full after the phase A report. Outline: B1-B2 fill and fetch, B3 settle every
`review` and blank row (Younes spot-checks 15), B4 fetch of the new boards, T1 timing.

## Phase C: new readers

Written after Younes confirms the order from the phase A report (C1).

## Phase D: what is left

One task: `docs/coverage-final-report.md` (D1).

## Waiting for Younes

(nothing yet)
