# 0003. Start job discovery from the IND sponsor register

Date: 2026-08-19

Status: accepted

## Context

Discovery currently runs aggregator-first. `scrapers/indeed.py` fetches RemoteOK and
Arbeitnow, `scrapers/company_pages.py` fetches two hardcoded Greenhouse boards, and
`ind_checker.py` then tags each result with sponsor status.

This caps recall at whatever the aggregators list. Every job the pipeline can ever find
must already appear on RemoteOK, Arbeitnow, or one of those two boards. A recognised
sponsor that posts only to its own careers board is invisible to the pipeline permanently
— running it daily for a year will not surface it. That is a structural ceiling, not a
tuning problem, and it cannot be fixed by adding keywords or locations to `config.py`.

Sponsor status is also inferred rather than known. `is_ind_sponsor` matches company names
against the register by substring in both directions, so short register entries generate
false positives. With the four-character sponsors `ems` and `kpn` in the register,
"Open Systems International", "Chemsafe" and "Kpnetworks" all return "Yes". Eighteen
register entries are four characters or fewer.

Two arguments that appear to support inverting were tested and do not hold:

- The register is already cached. `load_sponsors()` downloads only when the file is
  missing. The real defect is the opposite — there is no TTL, so it never refreshes.
- The cross-reference is not a cost. Measured at 16.7 ms for 16 jobs against all 12,788
  sponsors.

Recall is the reason to invert. Neither of those is.

## Decision

Start from the IND recognised sponsor register, resolve each sponsor to a job board, and
fetch its openings.

Two phases, deliberately at different cadences:

- **Resolution** — sponsor name to ATS board token. Slow, incremental, cached to disk
  including negative results so a name is never re-probed. Never runs in full on the daily
  schedule.
- **Fetch** — read the resolved mapping, hit each board's public JSON API, apply
  `passes_all`, emit jobs in the dict shape already used by `company_pages.py`. Daily.

Two constraints on scope:

- **ATS resolution is the filter.** There is no company-classification step. A sponsor that
  resolves to a known ATS board is in scope; one that does not is out. The cached register
  has a single `name` column — no sector, no domain — so there is nothing to classify on,
  and `passes_all` already decides whether an individual job is wanted.
- **Added alongside, not in place of, the existing sources.** The aggregator scrapers and
  `ind_checker` stay. Jobs from the new source are sponsor-verified by construction and
  skip the fuzzy matcher entirely.

Resolution targets ATS platforms rather than arbitrary company websites. Most companies
rent their careers page rather than build it, and the major vendors expose public,
unauthenticated JSON on a uniform schema — Greenhouse (already proven in this repo), Lever,
Ashby, Workable, SmartRecruiters, Personio, and the two that matter most for Dutch
mid-size employers, Recruitee and Homerun. That turns what would be ~12,788 bespoke
scrapers into about seven fetchers.

## Alternatives considered

**Keep the aggregator-first design.** No new work, and the cross-reference genuinely is
cheap. But it leaves the recall ceiling in place, and this repo's own history argues
against depending on aggregators: Werkzoeken.nl went JS-rendered and had to be dropped,
the Picnic and bol.com APIs started returning 404, and the IND xlsx URL died. The
Greenhouse API is the only source that has never broken.

**Resolve sponsors to their own websites and scrape those.** Maximum coverage in principle.
In practice it needs name to domain (no free reliable source), domain to careers page, then
a bespoke parser per site. The two hand-rolled HTML scrapers already in `company_pages.py`
are the least reliable code in the repo; multiplying them by thousands is not viable.

**Enrich the register with sector and domain data first, then filter.** Real filtering
power, but it adds an external and probably paid dependency plus a new failure mode before
the core idea has been shown to work at all.

## Consequences

**Coverage becomes partial, and the gap is silent.** Only sponsors whose names resolve to
an ATS board are ever polled, and the pipeline cannot distinguish a sponsor it failed to
resolve from one with no open roles. This is the main cost of the decision and the thing
most likely to make it wrong. If sponsor-first never surfaces a job the aggregators
missed, the added complexity has not earned its place.

**Resolution is new long-lived state.** The mapping file must persist negative results, so
it needs the same GitHub Actions cache treatment `seen_jobs.json` already has — including
the same caveat that caches untouched for seven days are evicted.

**Name normalisation becomes a real problem.** Register entries carry legal-entity noise
and one company spans several rows: `adyen n.v.` alongside `adyen netherlands b.v. i.o.`,
five separate `tomtom` entities, three `backbase` ones. Substring matching on names fails
in the other direction too — `gradyent b.v.` contains "adyen".

**Request volume needs a budget.** 12,788 names across seven vendors is roughly 90,000
probes. Resolution has to run incrementally with rate limiting and a descriptive
User-Agent, converging over weeks while fetch works on whatever has resolved so far.

**Dedup carries more weight.** A third source means more volume, and `deduplicate()` keys
on URL alone, so the same posting arriving from both an aggregator and a company board
survives twice. This is already observable in the current data.
