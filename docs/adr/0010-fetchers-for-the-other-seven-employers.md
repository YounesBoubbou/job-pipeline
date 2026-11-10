# 0010. Fetchers for the other seven big employers

Date: 2026-11-10

Status: proposed. Younes can overrule any point below.

## Context

P9's second group is Heineken, Signify, TomTom, Ahold Delhaize, HSBC, DSM-Firmenich and
AkzoNobel. Each board was checked by hand and belongs to the right company:

- **Signify** uses Workday (`lighting.wd3.myworkdayjobs.com/jobs-and-careers`). The existing
  fetcher already finds its Netherlands filter (`locationHierarchy1`, ADR-0008).
- **Ahold Delhaize** (careers.aholddelhaize.com) runs on GetNoticed, like ABN AMRO. Its
  country filter value has slug `nld` and display name "The Netherlands", and the API
  matches a filter on the display name: `filters[country][]=The Netherlands` gives the
  Dutch jobs, while `nld` is silently ignored and returns every job.
- **TomTom** uses Lever, but on Lever's EU instance: `api.eu.lever.co` answers, the usual
  `api.lever.co` returns 404.
- **HSBC** and **DSM-Firmenich** run on Eightfold. Eightfold has two public listing APIs:
  the newer `/api/pcsx/search` and the older `/api/apply/v2/jobs`. Each site has only one of
  them switched on; the other answers 403 with a short JSON message. DSM-Firmenich has the
  newer one, HSBC the older one. Both take `location=Netherlands`. Descriptions come from
  `/api/apply/v2/jobs/{id}`, which works on both sites.
- **AkzoNobel** runs on Phenom. Its page loads jobs by POSTing to `/widgets` with
  `ddoKey: refineSearch`; the answer lists a country filter with three-letter codes
  (`NLD`), and asking with `selected_fields: {"country": ["NLD"]}` returns only Dutch jobs.
  Descriptions come from the same endpoint with `ddoKey: jobDetail`. robots.txt only
  disallows `*/px-widgets`.
- **Heineken** runs its own Drupal site. There is no JSON API; the job list
  (`/Job-Listing?field_location_country_code_1[]=NL&page=0,0,N`) is plain HTML, 10 jobs a
  page, with a "Show more" link (`rel=next`) to the next page. robots.txt asks for 5
  seconds between requests. The same job can appear on two pages because the order
  shifts slightly between requests. Descriptions are only on each job's own page.

Ahold Delhaize and AkzoNobel write locations as "Zaandam, NLD". The location filter
(`passes_location`, unchanged) does not know "NLD" and would drop every such job.

SAP SuccessFactors routes (`career5.successfactors.eu`) were also found for some of these
employers, but their robots.txt says `Disallow: /`, so they are not used. TomTom's own site
(careers.tomtom.com) timed out.

## Decision

**Four new kinds in `targets.csv`.**

| kind | token | used by |
|---|---|---|
| `lever_eu` | the Lever company name, e.g. `tomtom` | TomTom |
| `eightfold` | the public search page, e.g. `https://jobs.dsm-firmenich.com/careers?domain=dsm.com` | HSBC, DSM-Firmenich |
| `phenom` | the site with its country and language, e.g. `https://careers.akzonobel.com/gb/en` | AkzoNobel |
| `heineken` | the site, `https://careers.theheinekencompany.com` | Heineken |

Signify uses `workday` and Ahold Delhaize uses `getnoticed`; no new kind is needed.

**All ask for Netherlands jobs only**, as in ADR-0008 and ADR-0009, so `fetched` means
"listings the site returned for its Netherlands query, before our filters". Lever has no
such query; TomTom's board is small (about 22 jobs) and is read in full.

- **Eightfold** tries the newer API first; on 403 it switches to the older one. Pages of 10,
  a 1-second wait between pages. A job with several offices gets them joined by "; ".
  Descriptions are fetched per job only for jobs that pass the filters on title and
  location (as for Workday).
- **GetNoticed** now also accepts a country value whose display name is "Nederland",
  "Netherlands" or "The Netherlands", and sends the display name as the filter value. ABN
  AMRO's value is "Nederland", so it keeps working.
- **Phenom** asks once with no filter to read the country filter, then again with the Dutch
  value (`Netherlands`, `The Netherlands`, `NLD` or `NL`, any case). If the site has a
  country filter but no Dutch value, it has no Dutch jobs and nothing more is asked. If it
  has no country filter, every job is read. Pages of 100.
- **Heineken** reads the HTML listing (with BeautifulSoup, already a dependency), waits 5
  seconds before every page after the first, skips jobs already seen, and stops when a
  page has no jobs or no "Show more" link, or after 30 pages. **No descriptions**: reading
  each job page at 5 seconds apart would add minutes per run, so Heineken jobs are judged
  on title and location only.

**"NLD" is spelled out inside the fetchers.** GetNoticed and Phenom locations have the
whole word "NLD" replaced by "Netherlands" before they leave the fetcher. The filter rules
are not changed (section 4 of the requirements).

## Consequences

- About 20 extra requests per run, plus one per Eightfold or Phenom job that passes the
  first filter; Heineken adds about 30 seconds of waiting.
- Ahold Delhaize's listing also includes its brands (Albert Heijn, Etos, Gall & Gall);
  they appear under "Ahold Delhaize".
- Heineken depends on the page's HTML classes (`job-list-item`, `job-title`, `nation`). If
  the site is redesigned, the fetcher returns nothing or fails, and shows up in the run
  summary.
- Any other employer on Eightfold, Phenom or Lever EU can be added with a `targets.csv` row.
