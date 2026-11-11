# Phase B report: boards on systems we already read (2026-11-11)

Started before A-4 to A-7 by Younes's decision ("lets add the 74 companies"). Branch
`coverage`, worktree `C:\Users\Younes\Desktop\job-pipeline-coverage`. Not merged, not pushed.

## Result

- Companies the daily run reads: **183 → 248** (149 `auto`, 99 `hand`; 254 boards).
- Full run in the worktree: **784 s (13 min)**, status `completed`, 254 boards, 0 failed
  (T1: 30 minutes or less). 66 jobs new against a copy of today's seen-jobs record, most of
  them from new companies (Vanderlande 32, Kyndryl 18, Marel 16, QuantWare 14, Mammoet 3).
- Tests: 246 pass.

## What was done

| Task | Outcome |
|---|---|
| B-1 fill and fetch (ADR-0014) | 74 rows: 38 auto, 26 review, 10 left out (6 no token, 2 scan bug `careers-analytics`, MIH Fintech = Prosus's board, A10 Networks HTTP 422) |
| B-2 settle | 83 rows checked (all review, blank and new auto): 28 hand, 37 auto kept, 18 none. Fox-IT dropped (board was Foxit Software) |
| B-3 timing | first run crashed at the end on a Mammoet job without a link; fixed (Jibe builds the link, a missing link can't crash the run); second run clean |

The 183 rows that were `auto`/`hand` before are byte-identical (B5). Every `none` row has a
blank source and token. Every changed row says why in `scan_note` (`fill:` and `settle:`).

## For Younes

1. **Spot-check** the 15 new `hand` rows listed in the chat (B3). Open.
2. **Merge** `coverage` into `mvp` when happy; the 08:00 run picks the new boards up from then.
3. Known gaps, not fixed here:
   - Dutch towns the location filter doesn't know: Capelle aan den IJssel (AIG),
     Veenendaal (Elekta), Baarle-Nassau (Novartis); Siemens Healthineers shows site codes.
     Their NL jobs are dropped by the filter (section 5: filters are out of scope).
   - Novartis uses its "acquired entities" Workday site; `Novartis_Careers` is probably
     the main one.
   - fonQ's board may be dead (it redirects to a site that no longer resolves). It fetched
     without error, so it stays for now.
   - Left out but recoverable: 5 Phenom sites with `/global/en` or `/benelux/nl` paths
     (Just Eat Takeaway.com, ABB, Kuehne + Nagel, Disney, Activision Blizzard), Vinted,
     Code d'Azur and VX Company (rescan), Finom (real board is Lever EU `pnlfin`).
   - Fox-IT's `website` column still says foxit.com.
4. Phase A is still open: A-4 (websites by web search) to A-7; the scan scored 45/183 on
   known rows against the 80% target.
