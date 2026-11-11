# 0012. Heineken descriptions

Date: 2026-11-11

Status: accepted by Younes, 2026-11-11 (he approved the extra ~4 minutes per run).

## Context

ADR-0010 left Heineken without descriptions: they are only on each job's own page, and the
site's robots.txt asks for 5 seconds between requests (`Crawl-delay: 5`). Without a
description, the "3+ years" and Dutch rules (P2) cannot judge Heineken jobs, so postings
that ask for Dutch or several years of experience get through. Job pages are not
disallowed by robots.txt.

## Decision

**Fetch one job page per Heineken job that passes the title and location filters**, as for
Workday, Eightfold and Phenom. The fetcher waits 5 seconds before each request, reads the
text of the page's `.job-fields` block, and the job is filtered again with it. A failed
fetch returns an empty description: the job is kept on title and location, and the board
is not marked as failed.

This supersedes ADR-0010's "No descriptions" for Heineken.

## Consequences

- About 4 to 5 extra minutes per run (roughly 50 job pages at 5 seconds each), within P6's
  15-minute limit.
- Heineken jobs that ask for Dutch or 3+ years are now dropped.
- The description depends on the `.job-fields` class. If the site is redesigned, the
  description comes back empty and Heineken jobs are again judged on title and location
  only, without any error in the run summary.
