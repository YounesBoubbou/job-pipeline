# 0004. Sponsor name matching and ATS resolution rules

Date: 2026-10-28

Status: accepted; section 3 (ATS resolution) is superseded by [0005](0005-target-list-as-primary-source.md)

## Context

[ADR-0003](0003-sponsor-first-discovery.md) decided to start discovery from the IND sponsor
register and resolve each sponsor to an ATS board, but left the mechanics open. Two of its
stated consequences needed concrete answers before any code: register names carry
legal-entity noise and one company spans several rows, and resolution needs a request
budget. This ADR records how both were settled, and what a pilot run measured.

## Decision

### 1. Name normalisation (`normalise_name` in `ind_checker.py`)

- Lowercase, remove stray `"` characters (the cached register has broken CSV quoting, e.g.
  `"""""aa-dee"""" machinefabriek`), split on whitespace.
- Strip trailing tokens repeatedly, **end of name only, whole tokens only**, from a fixed
  list: Dutch and foreign legal forms (`b.v.`, `b.v`, `bv`, `n.v.`, `nv`, `i.o.`, `v.o.f.`,
  `vof`, `u.a.`, `c.v.`, `limited`, `ltd`, `ltd.`, `gmbh`, `inc.`, `llp`, `s.a.`, `se`) plus
  `holding`, `holdings`, `netherlands`, `nederland`.
- Never strip a name to nothing — the last token always survives.
- Keep punctuation, so `booking.com` stays `booking.com` and yields usable board tokens.

Result: 12,788 register rows become 12,715 distinct names. `adyen n.v.` and
`adyen netherlands b.v. i.o.` both become `adyen`; `booking.com`, `booking` (holdings) and
`booking experts` stay separate; `asml trading` stays separate from `asml`.

Words that are often part of a real company name — `branch`, `europe`, `foundation`,
`amsterdam`, `international`, `services`, `benelux`, `office`, `center` — are deliberately
not stripped.

### 2. Exact matching in `is_ind_sponsor`

Both the register and the posting's company name go through `normalise_name`; the check is
set membership. This replaces bidirectional substring matching and removes its false
positives (`kpn` → "Kpnetworks", `ems` → "Chemsafe", `adyen` → "Gradyent").

A false "No" is preferred over a false "Yes". Measured over the 25 rows in `data/jobs.csv`,
one label changed: Mirantis went Yes → No, because its only register entry is
`mirantis poland sp. z o.o.`. Known misses of the same kind: `ING` (register has
`ing bank n.v.`). If these accumulate, the fix is a small alias list, not looser matching.

### 3. ATS resolution (`ats_resolver.py`)

- **Vendors:** Greenhouse, Recruitee, Lever, Ashby, SmartRecruiters.
- **Board token guesses:** two per name — alphanumerics joined (`flowtraders`) and
  hyphenated (`flow-traders`).
- **Hit rule:** HTTP 200 from the vendor's public API. SmartRecruiters returns 200 for *any*
  token, so it counts only when the board has at least one job.
- **Budget:** one request per second, descriptive User-Agent, 150 names per run
  (`ATS_BATCH_SIZE`), run by hand — never on the daily schedule. Up to 10 requests per name,
  so a full batch is about 25 minutes and the whole register about 85 runs.
- **State:** `data/ats_map.json`, `{name: {"vendor", "token"} | null}`. `null` is a
  persisted miss and is never re-probed. Transient failures (timeouts, 429, 5xx) are not
  recorded, so those names are retried next run.
- **Name collisions are accepted for now.** A board token can belong to a different company
  with the same name. The first full batch's hits are checked by hand; a name check is added
  only if that shows collisions are common.

## Pilot results

Measured 2026-10-28 before writing the resolver.

- **22 well-known sponsors:** 10 resolved — Greenhouse (`adyen`, `catawiki`, `bolcom`,
  `databricks`, `optiver`, `flowtraders`), Recruitee (`bunq`), Ashby (`mollie`, `bitvavo`),
  SmartRecruiters (`coolblue`).
- **25 random sponsors:** 1 resolved (`zenchef`, Recruitee). About 4%, which would be roughly
  500 sponsors register-wide, but the sample is far too small to trust the number.

Most of the register is small Dutch firms that do not rent an ATS. Under ADR-0003's
"resolution is the filter", that is the intended behaviour.

## Alternatives considered

**Workable.** Dropped. A nonsense token returns 404, but 8 of 15 well-known sponsors had a
board with zero jobs, and the first real resolver hit (`1cube`) was an Athens-based account
named "Workable", not the Dutch sponsor. No genuine hit was observed.

**Personio, Homerun.** Not included. Personio had no hits in the pilot. Homerun redirects
(302) even for a nonsense token, so existence cannot be checked by a single request.

**Workday.** Not resolvable by guessing: a board URL is `{tenant}.wd{N}.myworkdayjobs.com/{site}`
with three unknowns, and there is no single existence check. Common among Dutch banks and
large corporates, so it is to be added later as a **hand-maintained list** of known boards.

**Company websites.** Rejected as a general strategy in ADR-0003 (one bespoke scraper per
site). For a few specific targets — banks, universities that only accept applications
through their own site — a hand-maintained list remains acceptable; `COMPANY_PAGES` in
`config.py` already covers that case. AcademicTransfer may be a single source for Dutch
universities; not yet checked.

**A third token guess using only the first word** (`picnic technologies` → `picnic`). Would
recover some misses, but turns names like `china carbon` and `fc` into generic tokens and
makes collisions much more likely. Not adopted.

## Consequences

**A board with no current openings is recorded as a miss** on SmartRecruiters, and that
miss is permanent. Re-checking old misses is future work.

**Sponsors whose posted name differs from their registered name are missed** by exact
matching (Mirantis, ING). This is a deliberate trade for removing false positives.

**Resolution takes weeks.** At 150 names per run, the map covers the register only after
about 85 manual runs. The fetch step can start working from whatever has resolved so far.
