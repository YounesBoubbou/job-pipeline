# 0006. Resolve target-list boards automatically, with an NL-job check

Date: 2026-10-29

Status: accepted. Amends the "board is confirmed by hand" rule of
[0005](0005-target-list-as-primary-source.md).

## Context

ADR-0005 made a hand-maintained target list the primary source and required every board to
be confirmed by hand when added. The list then grew from 27 to 1,045 companies (generated
from the IND register, each row carrying its exact `ind_registered_name`; all verified
against a fresh register download). Confirming 1,045 boards by hand is days of work.

## Decision

**`python ats_resolver.py targets` fills `source`, `token` and `board_status` in
`targets.csv`.** It guesses tokens from the company name and the registered name, probes
the five vendors of ADR-0004, then fetches the found board:

| `board_status` | Meaning | Fetched daily |
|---|---|---|
| `auto` | Board lists at least one job naming an NL place | yes |
| `hand` | Checked by hand: right company, though no NL job when checked | yes |
| `review` | Board found but not confirmed (no NL job, often empty) | no |
| `none` | No board found, or a found board was the wrong company | no |
| blank | Probe failed; retried on the next run | no |

The NL check uses `names_nl_place`, which ignores bare work modes: "Remote" says nothing
about who owns a board. A board with any "(Sample)" job is never accepted — Recruitee demo
accounts (`accenture`, `ey`, `adecco`) carry sample jobs set in Amsterdam.

Recruitee answers 403 for some unused subdomains; that counts as no board, not an error.

## Results (first full run)

| Status | Count |
|---|---|
| auto | 115 |
| hand | 40 |
| review | 21 (all empty boards) |
| none | 866 |
| not probed | 3 |

Hand review of every `auto` and `review` row found:

- **Wrong `auto`**: Accenture and EY (demo accounts), Google (a Recruitee subdomain that no
  longer exists). The NL check let these through; the "(Sample)" rule now catches the first two.
- **Wrong `review`**: test boards (Personio, LinkedIn, Disney, Uber), same-name companies
  (Lightspeed, Allego, Check, Cosine, Action, SAS), and foreign member firms that never post
  NL jobs (Grant Thornton FR, Forvis Mazars DE, Protiviti DE, ASICS AU). Cleared to `none`.
- **Genuine `review`** (Jane Street, Bitvavo — whose locations read "Headquarters" —
  Spotify, Airbnb, Cloudflare, …): marked `hand`, so they are fetched once they post NL jobs.

A full fetch of the 155 `auto` + `hand` boards takes about a minute and kept 147 jobs.

## Consequences

**Most `none` rows are large employers on Workday or their own sites** — ING, ABN AMRO,
Rabobank, ASML, Philips, Booking.com. Name guessing cannot find these; their Workday board
URLs must be added by hand.

**`auto` is precise but not airtight.** One wrong board in ~118 slipped through after the
"(Sample)" rule (Google, now cleared). New `auto` rows from later runs should get a glance.

**Empty `review` boards are unverifiable.** They stay unfetched; most are probably accounts
the company no longer uses.
