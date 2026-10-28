# 0005. Use a hand-maintained target list as the primary sponsor source

Date: 2026-10-28

Status: accepted. Supersedes the "ATS resolution is the filter" constraint of
[0003](0003-sponsor-first-discovery.md) and the resolution plan in section 3 of
[0004](0004-sponsor-name-matching-and-ats-resolution.md).

## Context

[ADR-0003](0003-sponsor-first-discovery.md) decided to start discovery from the IND sponsor
register and to let ATS resolution decide which sponsors are in scope, with no
classification step. [ADR-0004](0004-sponsor-name-matching-and-ats-resolution.md) set the
resolution rules and accepted name collisions until the first batch's hits had been
checked by hand.

The first two full batches have now run. 200 of 12,715 names were probed and 8 resolved,
about 4%, matching the pilot. Each hit was checked by hand against the board's company
name, locations and job titles:

| Sponsor | Board | Finding |
|---|---|---|
| 247tailorsteel | SmartRecruiters | Genuine; NL jobs (Varsseveld) |
| 5ca | Greenhouse | Genuine; all 15 openings remote outside the NL |
| abbvie | SmartRecruiters | Genuine; 1,914 openings, mostly US/FR/DE |
| abt | Lever | **Collision**: a New York firm hiring HR and physical therapists |
| accenture | Recruitee | **Collision**: a test account ("Senior Marketer (Sample)") |
| acomo | Recruitee | Genuine; warehouse and production roles |
| act commodities | Greenhouse | Genuine but an internal-only board, 2 openings |
| active theory | Lever | Probably genuine; all openings in the Americas |

Two of eight hits are collisions, so ADR-0004's "collisions are accepted for now" fails
its own test. Of the six genuine hits, only 247TailorSteel posts jobs that are both in the
Netherlands and plausibly relevant. The rest are correct mappings that produce only noise
for `passes_all` to discard.

The register itself is the underlying problem. Most of it is small Dutch firms outside
tech, which are out of scope regardless of their ATS. The employers that are wanted — big
tech, banks, and SMEs that hire in tech — are either already known by name, or (banks and
many large corporates) use Workday or their own sites, which name-guessing cannot resolve
at all. Probing the whole register would take about 35 hours at one request per second, to
produce a map that is mostly misses, partly wrong, and blind to the banks.

## Decision

**A hand-maintained target list is the primary sponsor source.**

- One entry per company: display name, source type (`greenhouse`, `recruitee`, `lever`,
  `ashby`, `smartrecruiters`, `workday`, or `url`), and the board token or URL.
- The list lives in the repository, not under `data/`, because `data/` is gitignored and
  the list is curated content that must be versioned and available to CI.
- Each entry is checked against the IND register when it is added, using
  `is_ind_sponsor`. Where exact matching misses a genuine sponsor (`ING` vs
  `ing bank n.v.`), the entry records that it was confirmed by hand rather than loosening
  the matcher.
- The board is confirmed by hand when the entry is added — company name and locations
  on the board — so collisions cannot enter the list.
- Step 3's daily fetcher reads the target list, not `data/ats_map.json`.

**Register-wide resolution is on hold.** `ats_resolver.py` and `data/ats_map.json` stay.
If resolution resumes, it runs only over register names that look like tech companies
(keyword-filtered), and its hits are suggestions to review into the target list, never
fetched automatically.

Unchanged: ADR-0004's name normalisation and exact matching (sections 1 and 2), and
ADR-0003's decision to keep the aggregator sources alongside.

## Alternatives considered

**Resolve the whole register as planned.** About 85 manual batches or 35 hours unattended.
Rejected on the measured precision above, and because it still cannot reach the Workday
and own-site employers that matter most.

**Keep resolving but add an automatic name check against the board.** Would catch the
`abt` collision, but not `accenture` (the test account carries the right name), and does
nothing about genuine-but-irrelevant boards. Hand review of a short list is cheaper and
more accurate than automating it.

**Classify the register by sector first.** Already rejected in ADR-0003: the register has
only a name column, and sector data means a paid external dependency. Keyword filtering
on names is the cheap version, kept for the optional discovery use above.

## Consequences

**Recall is bounded by what is on the list.** This gives up ADR-0003's central argument:
a sponsor that posts only to its own board, and that is not already known, will not be
found. The aggregator sources and the optional keyword-filtered resolver are the only
remaining routes to unknown employers.

**The list needs maintenance.** Companies change ATS vendors and board tokens; a board
that starts returning 404 should be reported by the fetcher rather than skipped silently.

**Workday becomes a required fetcher**, not later work, since the banks are among the
main targets.

**Location filtering carries more weight.** Genuine boards are often mostly non-NL (5CA,
AbbVie), so `passes_location` must be correct. It currently accepts "Finland" and
"Greenland" via the `"nl"` substring, and everything with an empty location.
