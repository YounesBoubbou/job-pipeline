# Coverage scan report (phase A)

Date: 2026-11-18. Requirements: `docs/requirements-coverage.md` A1-A10. Scan: `coverage_scan.py`
(ADR-0013), with the 2026-11-18 changes: 12 requests per site (was 6) and one job page opened.

## 1. Summary

- **Companies fetched daily: 273 of 1,045** (183 before phase B, 248 after it).
  Added in phase A on 2026-11-18: 19 boards from the rescan, Netflix, IMC Trading, Booz Allen
  Hamilton, AstraZeneca, Sanoma Learning, Nexperia, Agilent.
- **Scan accuracy on known rows: 122 of 198 (62%)**, target 80%; **1 wrong board kind**
  (limit 5). The scan rarely names a wrong system; it misses. 80% is out of reach
  without a browser (A6): 34 of the 76 misses are pages that show jobs only after scripts run.
- **Website lookup by web search (A-4): trial of 50, then stopped.** 48 found, 1 clear gain
  (IMC Trading). The rest of the 266 rows without a website were not looked up.
- **Proposed phase C order:** Teamtailor, Oracle Recruiting, SAP SuccessFactors, Homerun,
  iCIMS (section 6).

## 2. Rows per `ats_seen` (all 1,045)

| `ats_seen` | Rows | | `ats_seen` | Rows |
|---|---|---|---|---|
| (no website) | 315 | | Oracle Recruiting | 14 |
| needs_browser | 203 | | phenom | 13 |
| custom | 155 | | iCIMS | 11 |
| no_careers_page | 100 | | Homerun | 8 |
| workday | 72 | | jibe | 6 |
| recruitee | 28 | | eightfold, lever | 5 each |
| SAP SuccessFactors | 22 | | BambooHR, Personio, smartrecruiters | 4 each |
| blocked | 21 | | Pinpoint | 3 |
| greenhouse | 18 | | JOIN, getnoticed, Workable, Breezy, Cornerstone | 1 each |
| ashby | 15 | | | |
| Teamtailor | 14 | | **Total** | **1,045** |

`ats_seen` describes what the scan saw; it is empty for rows whose `website` stayed empty.
For fetched rows `source` is what counts (section 4).

## 3. The three groups of section 2, among the 772 rows not fetched

| Group | Rows |
|---|---|
| 1. On a system we read, but not fetched | 36 |
| 2. On a system we can't read yet | 84 |
| 3. Company's own careers page (`custom`) | 127 |
| Unknown: needs a browser (173), no website (266), no careers page (68), blocked (18) | 525 |

Group 1, why not fetched: 8 `review` (the board lists no NL job today), 2 fetch failed
(ICE, MSCI: their Jibe sites answer 500/404 on the jobs API), and 26 with no usable board
address in the evidence or settled as the wrong company in phase B (Splunk, Snap, Ivanti,
American Express, Allianz, GE HealthCare, Roche, DeepL, Fox-IT, Xebia, ...). These can be
done by hand, like the 12 big names in section 5.

Only 4 `custom`/`needs_browser` pages carry schema.org `JobPosting` data (A5): a generic
reader for it (C4) would unlock almost nothing.

## 4. Per category

| Category | Rows | Fetched | Most common among the rest |
|---|---|---|---|
| IT services & consulting | 156 | 20 | custom 34, no website 33, needs_browser 28 |
| Hardware, semiconductors & deep tech | 123 | 32 | no website 28, needs_browser 23, custom 17 |
| Big tech & software | 117 | 51 | no website 21, needs_browser 14, no_careers_page 8 |
| Dutch tech & scale-ups | 90 | 22 | no website 23, needs_browser 15, custom 10 |
| Fintech & payments | 66 | 18 | no website 17, no_careers_page 7, custom 5 |
| Health & life sciences tech | 66 | 20 | no website 18, needs_browser 14, phenom 3 |
| Mobility, travel & logistics | 60 | 14 | no website 25, needs_browser 9, custom 5 |
| Data & AI | 47 | 13 | no website 18, needs_browser 9, no_careers_page 2 |
| Telecom, cloud & infra | 47 | 11 | no website 15, needs_browser 9, custom 4 |
| Gaming & media | 45 | 8 | no website 14, needs_browser 14, no_careers_page 4 |
| Corporates with tech teams | 43 | 16 | no website 10, custom 8, needs_browser 3 |
| E-commerce & retail | 38 | 5 | no website 12, needs_browser 7, custom 4 |
| Banks & insurance | 34 | 14 | custom 6, needs_browser 5, no website 3 |
| Energy & climate tech | 34 | 9 | no website 10, needs_browser 6, custom 4 |
| Cybersecurity | 28 | 12 | no website 5, needs_browser 5 |
| Research & universities | 24 | 1 | no website 9, custom 7, needs_browser 5 |
| IT staffing & recruitment | 17 | 0 | custom 9, needs_browser 3, no website 3 |
| Trading & quant | 10 | 7 | no website 2, custom 1 |

## 5. What was done on 2026-11-18

1. **Scan improved.** Known rows: 104 → 117 named exactly, 122 counting Phenom/Eightfold
   careers sites (front ends we also read). Rows out of requests: 35 → 0. Wrong kinds: still 1.
2. **Website trial (A-4).** 50 random rows without a website (seed `20261118`,
   `data/a4_sample.csv`), looked up by web search: 48 found, 2 not (BPC Software Labs,
   Reliance IT Services). Scanned: IMC Trading (greenhouse, 23 NL jobs) and Booz Allen Hamilton
   (workday, 1 NL job) added; Triple IT and Trengo matched boards that don't hold their jobs.
   12 big names refused the scan (robots.txt or 403).
3. **The 12 big names by hand.** On boards we read: AstraZeneca, Sanoma Learning, Nexperia
   (auto), Agilent (hand, no NL job today), Netflix (auto, after an HTTP 429 cleared); Ovid
   posts on Wolters Kluwer's board, already fetched. Not readable: SAS and Panasonic (iCIMS),
   ASICS (SAP SuccessFactors), Oracle and Akamai (Oracle Recruiting), A.S. Watson (Cornerstone).
4. **Rescan of the 748 rows not fetched** with the improved scan, on a copy, merged back
   keeping the phase B `settle:`/`fill:` notes. 36 rows newly on a readable system; filled
   through ADR-0014: **19 auto**, all with NL jobs, each board name checked against the
   company. Jobs passing the filters on the day: Sopra Steria 49, Nearfield Instruments 8,
   Robeco 2, Malvern Panalytical 1, Bose 1; the other 14 had NL jobs, none matching.

## 6. Proposed order for phase C (new readers)

Counts are rows not fetched today whose scan saw the system; how many have NL jobs is
unknown until a reader exists.

| # | System | Rows | Examples | Why this place |
|---|---|---|---|---|
| 1 | Teamtailor | 14 | Sendcloud, Visma, Templafy, BUX, Info Support, Incentro | Dutch tech companies; each company site has a public job feed (to confirm) |
| 2 | Oracle Recruiting | 14 | J.P. Morgan, Euroclear, Nokia, Honeywell, Oracle, Akamai, BDO | Big employers; public JSON jobs API seen on Oracle's own site |
| 3 | SAP SuccessFactors | 22 | Worldline, Triodos Bank, Swiss Re, Canon Production Printing, NTT DATA, ASICS | Most rows, but each company sets its site up differently: hardest |
| 4 | Homerun | 8 | Tiqets, Payt, Quantoz, Peaks, Maxem | Small Dutch start-ups |
| 5 | iCIMS | 11 | Atlassian, SAS, Mambu, HERE Technologies, Panasonic | Mostly HTML pages, no common API |

Below 3 rows each (BambooHR 4, Personio 4, Pinpoint 3, ...): not worth a reader (C rule:
at least 10 companies), except as a cheap add-on if one shares an API with a reader above.

## 7. Open

- **A7 not met:** 62% against 80% (section 8). Younes chose to improve the scan; the
  remaining misses need a browser, which A6 rules out. **Accepted by Younes (2026-11-18).**
- **A8 (40 random rows checked by hand in a browser): skipped by Younes (2026-11-18).**
- **Phase C order (section 6):** Younes decides later.
- **A-4 stopped after the trial of 50** (1 gain in 50); 266 rows still have no website.
- Group 1 rows without a board address (26) can be done by hand, a few minutes each.

## 8. A7: mismatches on the 198 known rows

Right: 117 exactly, plus 5 careers-site front ends = 122 (62%). Wrong board kind: 1 (Extreme
Networks). Every other row below is a miss, not a wrong answer.

| Company | We read | Scan saw | Cause |
|---|---|---|---|
| Aalberts | smartrecruiters | custom | jobs on own site; no job-system link, also not on the first job page |
| Adyen | greenhouse | needs_browser | careers page shows jobs only after scripts run |
| Ahold Delhaize | getnoticed | needs_browser | careers page shows jobs only after scripts run |
| Airbnb | greenhouse | needs_browser | careers page shows jobs only after scripts run |
| AkzoNobel | phenom | custom | jobs on own site; no job-system link, also not on the first job page |
| Anaplan | greenhouse | custom | jobs on own site; no job-system link, also not on the first job page |
| ASML | workday | custom | jobs on own site; no job-system link, also not on the first job page |
| Axians | smartrecruiters | custom | jobs on own site; no job-system link, also not on the first job page |
| Baker Tilly | recruitee | custom | jobs on own site; no job-system link, also not on the first job page |
| Bitpanda | greenhouse | needs_browser | careers page shows jobs only after scripts run |
| Bitvavo | ashby | needs_browser | careers page shows jobs only after scripts run |
| BlackRock | workday | needs_browser | careers page shows jobs only after scripts run |
| BLOXS | recruitee | custom | jobs on own site; no job-system link, also not on the first job page |
| Blueprint Automation | recruitee | needs_browser | careers page shows jobs only after scripts run |
| bol | greenhouse | no_careers_page | no careers link or fallback path found |
| Bosch | smartrecruiters | custom | jobs on own site; no job-system link, also not on the first job page |
| Boskalis | smartrecruiters | needs_browser | careers page shows jobs only after scripts run |
| BYD | greenhouse | no_careers_page | no careers link or fallback path found |
| Bynder | ashby | needs_browser | careers page shows jobs only after scripts run |
| Celonis | greenhouse | needs_browser | careers page shows jobs only after scripts run |
| Centric | recruitee | needs_browser | careers page shows jobs only after scripts run |
| ChargePoint | greenhouse | needs_browser | careers page shows jobs only after scripts run |
| Cloudflare | greenhouse | needs_browser | careers page shows jobs only after scripts run |
| CM.com | recruitee | needs_browser | careers page shows jobs only after scripts run |
| Databricks | greenhouse | custom | jobs on own site; no job-system link, also not on the first job page |
| Datadog | greenhouse | needs_browser | careers page shows jobs only after scripts run |
| Deeploy | ashby | no_careers_page | no careers link or fallback path found |
| Deliveroo | greenhouse | needs_browser | careers page shows jobs only after scripts run |
| Delta Electronics | smartrecruiters | no_careers_page | no careers link or fallback path found |
| Deutsche Bank | workday | no_careers_page | no careers link or fallback path found |
| Discord | greenhouse | needs_browser | careers page shows jobs only after scripts run |
| Eraneos | recruitee | needs_browser | careers page shows jobs only after scripts run |
| Esri | greenhouse | custom | jobs on own site; no job-system link, also not on the first job page |
| Extreme Networks | lever | workday | scan saw a Workday board; we read Lever (company may have moved) |
| Funda | recruitee | blocked | site refused or did not answer |
| GitLab | greenhouse | custom | jobs on own site; no job-system link, also not on the first job page |
| Greenchoice | recruitee | no_careers_page | no careers link or fallback path found |
| Guerrilla Games | greenhouse | needs_browser | careers page shows jobs only after scripts run |
| Heineken | heineken | no_careers_page | no careers link or fallback path found |
| HelloFresh | greenhouse | phenom | careers-site front end, also readable (counted right) |
| HSBC | eightfold | no_careers_page | no careers link or fallback path found |
| HSO | lever | custom | jobs on own site; no job-system link, also not on the first job page |
| Huisman | recruitee | custom | jobs on own site; no job-system link, also not on the first job page |
| Iquality | recruitee | blocked | site refused or did not answer |
| Keywords Studios | smartrecruiters | custom | jobs on own site; no job-system link, also not on the first job page |
| Kiwi.com | ashby | needs_browser | careers page shows jobs only after scripts run |
| KPN | smartrecruiters | needs_browser | careers page shows jobs only after scripts run |
| Lemonade | ashby | needs_browser | careers page shows jobs only after scripts run |
| LUMC | recruitee | needs_browser | careers page shows jobs only after scripts run |
| Lunatech | recruitee | no_careers_page | no careers link or fallback path found |
| Mews | greenhouse | needs_browser | careers page shows jobs only after scripts run |
| Miro | ashby | custom | jobs on own site; no job-system link, also not on the first job page |
| MongoDB | greenhouse | custom | jobs on own site; no job-system link, also not on the first job page |
| NN Group | workday | custom | jobs on own site; no job-system link, also not on the first job page |
| Northwave | recruitee | needs_browser | careers page shows jobs only after scripts run |
| NVIDIA | workday | custom | jobs on own site; no job-system link, also not on the first job page |
| Okta | greenhouse | custom | jobs on own site; no job-system link, also not on the first job page |
| OneTrust | greenhouse | custom | jobs on own site; no job-system link, also not on the first job page |
| Philips | workday | phenom | careers-site front end, also readable (counted right) |
| Picnic | smartrecruiters | needs_browser | careers page shows jobs only after scripts run |
| PVH (Tommy Hilfiger, Calvin Klein) | smartrecruiters | phenom | careers-site front end, also readable (counted right) |
| Roland Berger | smartrecruiters | needs_browser | careers page shows jobs only after scripts run |
| Snowflake | ashby | phenom | careers-site front end, also readable (counted right) |
| Sony Music | greenhouse | no_careers_page | no careers link or fallback path found |
| Spotify | lever | no_careers_page | no careers link or fallback path found |
| Squarespace | greenhouse | needs_browser | careers page shows jobs only after scripts run |
| Stream | ashby | no_careers_page | no careers link or fallback path found |
| Stripe | greenhouse | needs_browser | careers page shows jobs only after scripts run |
| SumUp | greenhouse | custom | jobs on own site; no job-system link, also not on the first job page |
| Sunweb | recruitee | needs_browser | careers page shows jobs only after scripts run |
| Synthesia | ashby | no_careers_page | no careers link or fallback path found |
| Sytac | greenhouse | needs_browser | careers page shows jobs only after scripts run |
| Thoughtworks | greenhouse | custom | jobs on own site; no job-system link, also not on the first job page |
| TomTom | lever_eu | custom | jobs on own site; no job-system link, also not on the first job page |
| Travix | greenhouse | custom | jobs on own site; no job-system link, also not on the first job page |
| Twilio | greenhouse | eightfold | careers-site front end, also readable (counted right) |
| Vattenfall | smartrecruiters | custom | jobs on own site; no job-system link, also not on the first job page |
| Weaviate | ashby | needs_browser | careers page shows jobs only after scripts run |
| Wehkamp | smartrecruiters | custom | jobs on own site; no job-system link, also not on the first job page |
| Wonderkind | recruitee | needs_browser | careers page shows jobs only after scripts run |
| WoodWing | recruitee | needs_browser | careers page shows jobs only after scripts run |
