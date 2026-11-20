# 0015. Teamtailor reader

Date: 2026-11-20

Status: accepted for tasks C-1 to C-3 of `docs/tasks-coverage.md`. Younes chose Teamtailor
as the first phase C system (2026-11-20). Younes can overrule any point.

## Context

The phase A scan found 14 companies whose careers site runs on Teamtailor (report section 6):
Sendcloud, Booking Experts, Leadinfo, Visma, Templafy, BUX, Hadrian Security, Hostnet, Info
Support, Incentro, iLionx, Emixa, Felyx, Tibber. None is fetched today. Most use their own
domain (`jobs.sendcloud.com`), some the Teamtailor one (`templafy.teamtailor.com`).

## The four checks of C2 (done 2026-11-20)

1. **Public listing, no login.** Every Teamtailor careers site serves `<site>/jobs.rss`, a
   public RSS feed of all listed jobs. Teamtailor's help centre documents it for sharing jobs
   with other channels ("RSS feed how-to guide",
   https://support.teamtailor.com/en/articles/11171756-rss-feed-how-to-guide). Checked live
   on Sendcloud (37 jobs), BUX, Visma Finland and Tibber: all answer 200 with no login.
2. **robots.txt and terms.** The career sites' `robots.txt` (Sendcloud's checked) disallows
   only `/app/`, `/messages/`, `/messenger/`, `/facebook/tab/` and `/jobs/internal/`;
   `/jobs.rss` is allowed for `*`. Teamtailor's own `robots.txt` allows everything. The
   feed is offered for reuse; one request per board per day is well within that use.
   Teamtailor's formal job-board partner feeds (XML, webhooks) need a partnership and are
   not used.
3. **Asking by country.** The feed has no country filter, but it is one request per board and
   each item lists its offices with `<tt:city>` and `<tt:country>`, so the existing location
   rules can filter it. No extra step needed.
4. **Description.** The full HTML description is in each item's `<description>`. No second
   request, so no `DESCRIPTION_FETCHERS` entry.

All four pass: the reader is built.

## Decision

- **Source** `teamtailor`. **Token** = the careers site's base address without path, e.g.
  `https://jobs.sendcloud.com` or `https://templafy.teamtailor.com`. The reader requests
  `<token>/jobs.rss`.
- **Fields.** title = `<title>`; url = `<link>`; description = `<description>`;
  location = each `<tt:location>` as `City, Country`, joined by `"; "` (as the Greenhouse
  reader does for offices). With no `<tt:location>` and `<remoteStatus>` `fully`, the location
  is `Remote`; with neither, it is empty and the job is dropped by the location rule, as for
  every other reader.
- **Filling rows (C-3)** follows ADR-0014 and ADR-0006: token from `careers_url` or
  `ats_evidence`, one fetch, `auto` if a listing names an NL place, otherwise `review`.
  Companies with several Teamtailor sites (Visma has one per country) get the site with
  Dutch jobs, checked by hand.

## Consequences

Up to 14 more companies fetched daily at one request each, so the run time (T1) barely
changes. The feed is not cut to one page: on 2026-11-20 Emixa's jobs page showed 25 jobs
and Sendcloud's 20 (the rest behind "show more"), while their feeds held all 47 and 37.

Not read: Info Support (its Teamtailor site redirects to a WordPress page; no public feed)
and Visma (its Dutch companies post on EasyCruit, not Teamtailor).
