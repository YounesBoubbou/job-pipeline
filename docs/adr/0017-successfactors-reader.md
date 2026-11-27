# 0017. SAP SuccessFactors reader

Date: 2026-11-27

Status: accepted for tasks C-7 to C-9 of `docs/tasks-coverage.md`. Younes chose SAP
SuccessFactors as the third phase C system and the "hybrid" way of reading it below
(2026-11-27). Younes can overrule any point.

## Context

The phase A scan found 22 companies on SAP SuccessFactors (report section 6; a 23rd match,
Deloitte, is a Workday row and is not part of this). Two kinds of site:

- **Career Site Builder** sites on the company's own domain (`careers.triodos.com`,
  `jobs.volvogroup.com`, `careers.tudelft.nl`, ...): Optimizely, Worldline, Triodos Bank,
  Canon Production Printing, Seagate, Wipro, Birlasoft, NTT DATA, msg global solutions,
  Under Armour, MediaMarktSaturn, Athlon, Port of Rotterdam, Alstom, Volvo, TU Delft.
- **Old `career<N>.successfactors.eu` pages**: Swiss Re, YASH Technologies, TUI, Sonova,
  Novo Nordisk. Not read (see Consequences). ASICS has no address.

## The four checks of C2 (done 2026-11-27)

1. **Public listing, no login.** Every Career Site Builder site serves `/sitemap.xml`, a
   public list of every job page (`<site>/job/<slug>/<id>/`). Checked live on 16 sites: 14
   list jobs (11 at Triodos to 6,615 at Wipro); Alstom and Optimizely list none.
2. **robots.txt.** The same on every site checked: `User-agent: *` with `Disallow:` for
   `/services/`, `/applybutton/`, `/talentcommunity/`, `/preapply/` and a few others; no
   crawl delay. `/sitemap.xml` and `/job/` are allowed. The sites' RSS feed
   (`/services/rss/job/`) and the search page's data both sit under `/services/` and are
   **not used**. The search page (`/search/`) is allowed but builds its results from
   `/services/` in the browser, so its HTML has no jobs.
3. **Asking by country.** Not possible through allowed paths: the sitemap lists addresses
   only. A job's address (its slug) usually starts with the town and often ends with a
   postcode (`/job/Rotterdam-Product-Owner-Data-Platforms-ZH-3072-AP/1367862157/`), but
   judging the country from it misses towns not in `LOCATIONS` (Triodos's Driebergen,
   Canon's Venlo) and can match wrongly ("St John's ... NL", Newfoundland). Hence the hybrid
   in the Decision.
4. **Title, location, description.** On the job page. The title is in `itemprop="title"` on
   every site checked. Location and description differ per company:
   - location: schema.org `itemprop` address fields on some (TU Delft "Delft, NL, 2628 CD",
     Volvo, MediaMarktSaturn, msg, Athlon, Under Armour); a labelled `.joblayouttoken` on
     others ("Job Location (Short): LA Driebergen-Rijsenburg, NLD", "Job Location: Germany -
     Frankfurt", "Location: ..."); none found on NTT DATA and Port of Rotterdam.
   - description: `itemprop="description"` on most; elsewhere on Triodos, Port of
     Rotterdam, Canon, Seagate (a "Job Description:" token).

Amended the same day after the C-8 live check: the title, `streetAddress` and description
fallbacks in the Decision were added for NTT DATA, Seagate, TU Delft, Triodos and Port of
Rotterdam.

Checks 1, 2 and 4 pass; 3 fails, which costs one request per job page read. Younes accepted
that with the hybrid below.

## Decision

- **Source** `successfactors`. **Token** = the career site's base address without path,
  e.g. `https://careers.triodos.com`.
- **Which pages are read.** One request for `<token>/sitemap.xml`, keeping `<loc>`s that
  contain `/job/` (with `&amp;` unescaped).
  - **Small site** (150 job addresses or fewer): every job page is read.
  - **Big site** (more than 150): only pages whose slug, with `-` and `/` read as spaces,
    names an NL place (`names_nl_place`), says `NLD`, `Netherlands` or `Nederland`, or ends
    in a Dutch postcode (`\d{4}-[A-Z]{2}` just before the id). False matches are harmless:
    the page's own location decides.
- **Fields from each page.**
  - A page whose final address (after redirects) has no `/job/` in it is skipped: expired
    jobs redirect away from the job page.
  - title = text of `itemprop="title"`; else the `content` of `<meta property="og:title">`
    (NTT DATA and Seagate have no `itemprop`; their `og:title` is the bare job title, as on
    every site checked). A page with neither is skipped.
  - location, first that is found: the schema.org address fields (`streetAddress`, which
    TU Delft, Volvo and Athlon fill with the whole "Delft, NL, 2628 CD", then
    `addressLocality`, `addressRegion`, `postalCode`, `addressCountry`) joined by `", "`; else the value of the
    first `.joblayouttoken` whose label contains "location" (any case), plus one whose label
    contains "country"; else the slug's text. If the result contains the code `NLD` or
    `NL` as a separate word and names no NL place, `", Netherlands"` is appended.
  - description = HTML of every non-empty `itemprop="description"` element, joined
    (Triodos has three, the first empty; Worldline splits its text over three); else the
    value of a `.joblayouttoken` whose label contains "description"; else the HTML of the
    `.jobDisplay` block (the whole job panel; Port of Rotterdam has nothing else) with its
    `<script>` and `<style>` blocks removed; else "".
  - url = the sitemap address (not the redirect target).
  So the reader returns description already filled; no `DESCRIPTION_FETCHERS` entry.
- **Politeness.** Requests one after another (no parallelism), with the shared `HEADERS`
  and `TIMEOUT`. No delay is required by `robots.txt`.
- **A page that fails** (network error, 404) is skipped, not the whole board; a failing
  sitemap fails the board, as for every other reader.
- **Filling rows (C-9)** follows ADR-0014 and ADR-0006: token = the site's base address
  from `careers_url`/`ats_evidence`, one fetch, `auto` if a listing names an NL place,
  otherwise `review`. Alstom and Optimizely (empty sitemaps), the five old-style sites and
  ASICS stay `none` with a note.

## Consequences

Around 14 more companies. Request count on 2026-11-27, from the sitemaps: about 260 pages
for the small sites (11 + 73 + 81 + 25 + 8 + 7 + ... ) and about 210 slug matches on the big
ones (MediaMarktSaturn 154, Under Armour 18, NTT DATA 17, Wipro 10, Worldline 5, Volvo 4,
Birlasoft 1), so a few minutes more per run (T1 allows 30). The layout differs per company,
so the C-9 live check reads at least one page per board and reports any board whose pages
give no title or no location; such a board is set to `review` with the reason in its note.
Jobs on big sites whose address names no Dutch town, code or postcode are missed.

Not read: Swiss Re, YASH, TUI, Sonova and Novo Nordisk (old `career<N>.successfactors.eu`
pages, a different system), Alstom and Optimizely (no jobs in the sitemap), ASICS (no
address). Leiden University (task 26 of the MVP) uses SuccessFactors too and could be added
the same way later.
