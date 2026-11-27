# 0016. Oracle Recruiting reader

Date: 2026-11-27

Status: accepted for tasks C-4 to C-6 of `docs/tasks-coverage.md`. Younes chose Oracle
Recruiting as the second phase C system (2026-11-27). Younes can overrule any point.

## Context

The phase A scan found 14 companies whose careers site runs on Oracle Recruiting Cloud
("Candidate Experience", report section 6): Euroclear, J.P. Morgan, Chubb, Ipsos, Diebold
Nixdorf, Honeywell, Nokia, Zensar, BDO, Grant Thornton, DP World, ITV Studios, Oracle and
Akamai. None is fetched today. Each has a site at
`https://<host>.oraclecloud.com/hcmUI/CandidateExperience/<lang>/sites/<site>`, where
`<host>` and `<site>` (e.g. `CX_1001`) differ per company.

## The four checks of C2 (done 2026-11-27)

1. **Public listing, no login.** The careers site loads its jobs from a public JSON endpoint
   on the same host:
   `/hcmRestApi/resources/latest/recruitingCEJobRequisitions?onlyData=true&expand=requisitionList.secondaryLocations&finder=findReqs;siteNumber=<site>,location=Netherlands,limit=<n>,offset=<n>`.
   Checked live on all 13 rows with an address, plus Oracle's own site
   (`eeho.fa.us2.oraclecloud.com`, `CX_45001`): every one answered 200 with no login.
2. **robots.txt and terms.** `robots.txt` cannot be read: Oracle's firewall ("W4S-402:
   Blocked by WAF4SaaS") answers 403 to every client tried (browser-like and plain). The
   same firewall lets the jobs endpoint through, and it is the endpoint the company's own
   careers page calls from every visitor's browser. One listing request per board per day
   plus one request per job that passes the title and location filters, as for Workday
   (ADR-0008), stays well within normal visitor use.
3. **Asking by country.** Yes: `location=Netherlands` in the finder. On 2026-11-27 it cut
   J.P. Morgan from 6,739 jobs to 4. It also matches jobs whose *secondary* location is the
   Netherlands (all 5 Euroclear matches name Poland or Belgium first), so the reader joins
   the primary and secondary locations. A town name (`location=Amsterdam`) is ignored by the
   endpoint, so the country is used.
4. **Description.** Not in the listing (`ShortDescriptionStr` is empty). It takes one
   request per job: `/hcmRestApi/resources/latest/recruitingCEJobRequisitionDetails?expand=all&onlyData=true&finder=ById;Id="<id>",siteNumber=<site>`,
   which returns `ExternalDescriptionStr`, `ExternalResponsibilitiesStr` and
   `ExternalQualificationsStr` (HTML). So the reader gets a `DESCRIPTION_FETCHERS` entry,
   called only for jobs that pass the title and location filters.

All four pass (2 with the note above): the reader is built.

NL jobs on 2026-11-27 (country filter, before the pipeline's filters): DP World 30,
Honeywell 24, Euroclear 5, J.P. Morgan 4, Chubb 4, Ipsos 3, Diebold Nixdorf 1, Oracle 1;
Nokia, Zensar, BDO, Grant Thornton and ITV Studios 0.

## Decision

- **Source** `oracle`. **Token** = the site address without trailing path, e.g.
  `https://jpmc.fa.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1001`. The reader
  takes the host and site number from it.
- **Listing.** Ask with `location=Netherlands`, paging by `offset` until `TotalJobsCount`
  jobs are read.
- **Fields.** title = `Title`; url = `<token>/job/<Id>`; description = "" (fetched later);
  location = `PrimaryLocation` and each `secondaryLocations[].Name`, joined by `"; "`. As
  with Workday's country filter (ADR-0008), every job returned is in the Netherlands, so if
  none of those names an NL place, `"; Netherlands"` is appended (`"Netherlands"` if empty).
- **Description** = `ExternalDescriptionStr`, `ExternalResponsibilitiesStr` and
  `ExternalQualificationsStr` joined; "" on failure, like the other description fetchers.
- **Filling rows (C-6)** follows ADR-0014 and ADR-0006: token from `ats_evidence` or
  `careers_url`, one fetch, `auto` if a listing names an NL place, otherwise `review`.

## Consequences

Up to 14 more companies, 8 of them with Dutch jobs today. One listing request per board,
plus one per job that passes the title and location filters, so the run time (T1) grows by
well under a minute. Akamai's site address was not found by the scan; C-6 looks for it.
