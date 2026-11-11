# 0008. Ask Workday boards for their Netherlands jobs only

Date: 2026-11-10

Status: accepted by Younes, 2026-11-11. Amends the meaning of `fetched` in
[0007](0007-run-summary-file.md) for Workday boards. Younes can overrule any point below.

## Context

P6 asks for a full run in 15 minutes or less. A run took about 55 minutes, nearly all of it
on the 22 Workday boards: the fetcher downloaded every listing worldwide (about 17,000, 20
per request) only for the location filter to throw almost all of them away.

Workday's listing API takes `appliedFacets`, the same search filters a visitor clicks on the
careers site. With a filter set, `total` and the listings cover only the matching jobs. Each
board lists its filters ("facets") in the answer to the first request, but the filter's name
differs per board: `locationCountry`, `Location_Country`, `Country`,
`Country_and_Jurisdiction`, `Country___Territory`, `locationHierarchy1`, or even `a`. Some
boards nest the country filter inside `locationMainGroup`. Seven boards have no country
filter, only `locations`, a list of offices such as "ACT (Amsterdam - Acanthus)". A filter
only lists values that currently have jobs.

## Decision

**The first request stays as before** (offset 0, no filter). Its facets decide what follows:

1. A filter other than `locations` with a value called exactly "Netherlands" (ignoring case
   and spaces): ask for that value. Found by the value's name, not the filter's name.
2. Otherwise, the `locations` filter: ask for every office whose name passes
   `names_nl_place` (the same NL place check as ADR-0006).
3. Otherwise, if the board has a `locations` filter or a filter whose name contains
   "country": the board has no Dutch jobs right now, and nothing more is requested.
4. Otherwise (no location filter found): download every listing as before, reusing the
   first page.

The filtered listings then go through the same steps as before: stubs skipped, "3
Locations" looked up on the job's page, and the usual filters in `fetch_target_jobs`.

**No caching.** The filter ids are read fresh on every run. It costs nothing (the first
request was made anyway) and a board that renames its filters keeps working.

**`fetched` changes meaning for Workday boards.** It is now "listings the board returned for
its Netherlands query, before our filters", not "every listing on the board".

## Consequences

- A Workday board costs one request plus one per 20 Dutch jobs, instead of one per 20 jobs
  worldwide.
- A job whose location is only "Remote", with no country, used to pass the location filter
  and now is not asked for on boards that have a country filter. Such jobs are rare on
  Workday boards (they are usually tied to a country, such as "Remote, Netherlands").
- If a board changes its filters so that none is recognised, it falls back to the full
  download: slower, but nothing is lost.
