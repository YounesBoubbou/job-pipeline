# 0014. Fill board addresses from the careers-page scan's evidence

Date: 2026-11-11

Status: proposed, for task B-1 of `docs/tasks-coverage.md`. Younes can overrule any point.

## Context

The careers-page scan (ADR-0013) found 74 rows that are not `auto`/`hand` but whose
`ats_seen` is one of the 12 kinds the pipeline reads: 70 `none` rows and 4 `review` rows.
Their `ats_evidence` holds the board address the scan saw. Those rows still have no
`source`/`token` (or, for the `review` rows, a guessed one), so they are not fetched daily.

## Decision

`python ats_resolver.py evidence [--company NAME]...` fills these rows. It lives in
`ats_resolver.py` because it reuses the NL-job check of ADR-0006.

**Rows.** `board_status` not `auto`/`hand`, and `ats_seen` in `FETCHERS`. Old `auto`/`hand`
rows are never written (B5).

**Token.** `coverage_scan.token_from_evidence(ats_seen, ats_evidence)`, the same rule the
scan used to choose its evidence. For a `review` row the evidence token replaces the guessed
one; the note keeps the old one as `was <source>:<token>`. Recruitee's own analytics
subdomain, `careers-analytics`, sits on every Recruitee-hosted careers page and names no
board; the scan and the token rule now ignore it.

**Duplicates.** Tokens are compared case-insensitively, ignoring a trailing `/`.

- Same board as an existing `auto`/`hand` row: left out, not fetched. The board is already
  fetched once under the other company.
- Same board as another row filled in this run (Cloud Software Group and Cloud++): both get
  `source`/`token` and `review`, not fetched. B-2 decides which company owns the board.

**Status.** One fetch, `list(FETCHERS[kind](token))`, no descriptions, then ADR-0006:
`auto` if a listing names an NL place and none is a "(Sample)" job, otherwise `review`
(also for a board with 0 listings).

**Left out.** No token in the evidence, a duplicate of an `auto`/`hand` board, or a fetch
that raised. The row keeps its `board_status`; `source`/`token` are blank (a `review` row
whose token was missing or whose fetch raised gets its old values back; a duplicate of an
`auto`/`hand` board is blanked in every case). A `none` row must not keep a token: the daily run fetches every
row with a source and token unless it says `review`.

**`scan_note`.** `; fill: <outcome>` is appended; a rerun replaces the old `fill:` part.
Outcomes: `auto, 14 listings`; `review, 0 listings`; `review, no NL place in 9 listings`;
`review, "(Sample)" job in 3 listings`; `review, same board as Cloud++`;
`left out, same board as Prosus (auto)`; `left out, no token in evidence`;
`left out, fetch failed <Error>: <message>` (message without `;` or newlines, about 150
characters at most). Any `was <source>:<token>` follows the outcome.

**Politeness.** Boards one at a time, `REQUEST_DELAY` after each, no retries. The run prints
the left-out, failed and new `auto` rows and writes `data/fill_summary.json`.

## Consequences

- New `auto` rows are fetched daily straight away. Some evidence points at a parent or
  same-name company's board (Fox-IT, Xebia APAC, NIO USA, Bullhorn for Textkernel, ...),
  and the NL check does not always catch that. B-2 checks every new `auto` row by hand,
  as ADR-0006 already advised.
- Rows left out stay as they were and are listed for B-2; nothing is guessed for them.
