# 0011. What counts as a "new" job

Date: 2026-11-10

Status: proposed. Younes can overrule any point below.

## Context

W3 asks that the jobs added by the most recent run are visibly marked as new, and that
after a run that adds jobs, exactly those jobs carry the marker. Section 6 confirms that
"new" means added by the most recent run, not "new since you last looked". `data/jobs.csv`
has no column saying which run added a row.

## Decision

**New = the last `jobs_added` rows of `data/jobs.csv`.** `/api/jobs` reads `jobs_added`
from `data/last_run.json` (ADR 0007) and sets `is_new: true` on the last that many rows,
`false` on all others. The job card shows an amber "New" badge for those jobs.

This relies on two things, and future changes must keep both:

1. `jobs.csv` stays append-only: `output.write_csv` only appends, and nothing reorders,
   rewrites or deletes rows.
2. `main.py` sets `summary["jobs_added"]` to the number of rows it just appended, right
   after `write_csv`, and `last_run.json` is rewritten on every run.

## Rejected alternatives

- **Match on `date_found` = the last run's date.** Two runs on the same day would mark the
  jobs from both runs, which breaks "exactly those jobs".
- **Add a run-id column to `jobs.csv`.** Exact, but it changes the CSV format (and
  `output.py`) for a check the row count already answers. Worth revisiting if the CSV ever
  stops being append-only.

## Edge cases

- No summary file, or one that cannot be read or is not a JSON object: nothing is marked.
- `jobs_added` missing, not a whole number (a string, a boolean, a fraction) or negative:
  nothing is marked.
- The last run added nothing (`jobs_added: 0`): nothing is marked. Jobs from earlier runs
  are not "new" any more.
- A crashed run: its jobs are marked if and only if it got as far as setting `jobs_added`
  (that is, after writing the CSV).
- `jobs_added` larger than the number of rows (e.g. the CSV was replaced by hand): nothing
  is marked rather than guessing.
- A page loaded while a run is writing may be briefly off (the CSV already has the new
  rows but the summary still has the old count). Reloading after the run fixes it.
