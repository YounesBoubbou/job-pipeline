# 0009. Fetchers for iCIMS Jibe and GetNoticed careers sites

Date: 2026-11-10

Status: proposed. Younes can overrule any point below.

## Context

P9 asks for jobs from eleven big employers. The first four are ASML, Booking.com, ABN AMRO
and Rabobank. ASML uses Workday, which is already supported. Booking.com and ABN AMRO run
their own careers sites on vendors the pipeline did not know:

- **Booking.com** (jobs.booking.com) runs on iCIMS Jibe. Its page loads jobs from
  `/api/jobs`, a JSON API that takes `page`, `limit` (up to 100) and `country`, and returns
  each job with its full description. Its robots.txt allows everything but asks for 5
  seconds between requests (`Crawl-delay: 5`).
- **ABN AMRO** (werkenbijabnamro.nl) runs on GetNoticed. Its page loads vacancies from
  `/api/vacancy/`, which answers with JSON only when the request carries the header
  `X-Requested-With: XMLHttpRequest` (the header a page's own script sends). Pages hold 8
  vacancies and cannot be made bigger. The listings have no description, and the job
  detail endpoint returns errors, but the site's RSS feed (`/feeds/rss`) lists every
  vacancy with its full text. robots.txt allows `/api/`.

Rabobank's site answers every request, including robots.txt, with 403 Forbidden (Akamai bot
protection). It is not fetched; that is Younes's decision under P9.

## Decision

**Two new kinds in `targets.csv`: `jibe` and `getnoticed`.** The token is the careers
site's base URL, e.g. `https://jobs.booking.com`, the way Workday's token is the board URL.

**Both ask for Netherlands jobs only**, on the site's side, as Workday does since ADR-0008.
So `fetched` in the run summary means "listings the site returned for its Netherlands
query, before our filters".

- Jibe: `country=Netherlands`, 100 jobs per page, and a 5-second wait before each page
  after the first, to honour the crawl delay. Booking.com fits in one page today.
- GetNoticed: the first page's facets (the site's own search filters) are searched for a
  value whose slug is `nederland` or `netherlands`, and that filter is applied, e.g.
  `filters[land][]=nederland`. A site without such a value is read in full. Descriptions
  come from one request to the RSS feed, matched to vacancies by the id in each item's
  link (`/vacature/{id}/{slug}`). If the feed fails, descriptions stay empty and the
  filters judge on title and location only; the board is not counted as failed.

**ASML's robots.txt.** It disallows `/ASMLEXT1/`, which covers the careers site's web
pages. The pipeline reads only Workday's listing API under `/wday/cxs/`, which robots.txt
does not disallow, the same way every other Workday board is read.

## Consequences

- Booking.com costs one request per run; ABN AMRO about 19 (one unfiltered first page, 17 filtered pages of 8, and the feed).
- Any other employer on Jibe or GetNoticed can be added with just a `targets.csv` row.
- If either site changes its API, the board shows up under `failed` in the run summary.
