# 0002. Use dbt for transformations

Date: 2026-08-19

Status: superseded by [0003](0003-sponsor-first-discovery.md)

## Context

Filtering currently happens inline in the scrapers, mixed with fetching. There's no way to
test a filter rule in isolation or change one without touching request code. Output is a
flat CSV with no history, so I can't answer "what did this posting look like last week."

## Decision

Land raw scraped payloads in Postgres unmodified, then transform with dbt in
staging/intermediate/marts layers. Filtering and IND matching become dbt models, not
Python.

## Alternatives considered

Keep transformations in Python with pytest. Less new tooling, but no lineage graph, no
schema tests, and the logic stays coupled to fetching.

Pandas in a notebook. Faster to write, not reproducible, and nothing runs it on a schedule.

## Consequences

Postgres becomes a hard dependency, so local dev needs Docker Compose. I take on dbt as
something to learn. Python's job shrinks to extraction and loading only. Filter changes
become diffable SQL with tests, which is the main thing I wanted.

## Why this was superseded

Not because dbt is the wrong tool, but because this record bundled three separable
decisions and argued for the largest one from the evidence for the smallest two:

1. Land raw payloads with timestamps — what actually answers "what did this posting look
   like last week." Needs storage, not dbt.
2. Separate filtering from fetching — what actually makes filter rules testable. A pure
   Python refactor, needs neither dbt nor Postgres.
3. Express transformations as SQL with a lineage graph — the only part that needs dbt.

The Context above argues from (1) and (2) to justify (3). At roughly 16 rows a day, dbt is
not solving a data problem here; the honest driver is the one line in Consequences, "I take
on dbt as something to learn," which is a legitimate reason but a different one.

Superseded rather than deleted because the reasoning is worth keeping. If dbt is adopted
later it needs its own ADR with the real driver stated in its Context.
