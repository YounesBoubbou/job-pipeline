# 0007. Write a run summary file after every run

Date: 2026-11-10

Status: proposed. Younes can overrule any point below.

## Context

P1 asks that the run log names every board tried, with jobs fetched and kept. P5 asks that
a failing board never stops the run, and that each run writes a summary file with start and
end time, jobs added, and the failed boards with the reason. Before this, only the
target-list scraper collected failures; RemoteOK, Arbeitnow and the company pages printed a
warning and moved on, and nothing was written to disk.

## Decision

**Every source reports the same way.** `fetch_target_jobs`, `fetch_indeed_jobs` and
`fetch_company_jobs` each return `(jobs, boards, failed)`:

- `boards`: one entry per board that answered: `name`, `source`, `fetched`, `kept`.
- `failed`: one entry per board that raised: `name`, `source`, `reason`
  (`"<ErrorType>: <message>"`).

A board appears in exactly one of the two lists. `source` is `target:<vendor>` (e.g.
`target:greenhouse`), `aggregator` (RemoteOK, Arbeitnow), `careers:greenhouse` or
`careers:html`. If a whole source crashes, `main.py` records it as one failed entry with
source `source` (e.g. "Company pages") and carries on with the others.

**`fetched` and `kept` are per board.** `fetched` is the number of listings the board
returned before any filtering. `kept` is the number that passed the filters at that board,
*before* removing jobs already seen in earlier runs. The number actually added after that
check is run-wide: `jobs_added`.

**Partial failures.** A target board that errors partway counts as failed and none of its
jobs are kept. RemoteOK, Arbeitnow and company pages keep their old behaviour: jobs found
before the error are still used, but the board is listed as failed.

**The file.** `data/last_run.json` is rewritten at the end of every run, including runs that
find nothing new and runs that crash (`status: "crashed"`, with the error). It is written to
a temporary file first and then swapped in, so the web app never reads a half-written file.

```json
{"started_at": "2026-11-10T08:00:03+01:00", "finished_at": "2026-11-10T08:12:41+01:00",
 "duration_seconds": 758, "status": "completed", "error": null, "jobs_added": 12,
 "boards": [{"name": "Adyen", "source": "target:greenhouse", "fetched": 140, "kept": 3}],
 "failed": [{"name": "Valtech", "source": "target:greenhouse", "reason": "HTTPError: 404 ..."}]}
```

## Points Younes may want to change

- "kept" means "passed the filters at that board", not "added after removing repeats".
- P1's "run log" is taken to be the console output plus the `boards` list in the file.
- `duration_seconds` is not asked for by P5; it is there so P6's 15-minute check can be read
  straight from the file.
