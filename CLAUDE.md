# Working agreement

I am learning this codebase and building data engineering skills. Do not write
implementations for me.

- Do not produce full files or functions unless I explicitly ask with "write this for me"
- When I'm stuck, ask me what I've tried and point at the relevant concept or line,
  don't fix it
- Review my diffs: tell me what's wrong and why, don't rewrite
- Push back on my design choices so I have to defend them
- If I can't explain a change I made, tell me to revert it

Design docs are exempt — ADRs, README, and comments you may write in full.

# Project

Daily job discovery pipeline. Starts from the IND recognised sponsor register, resolves
sponsors to their job boards, and fetches openings. Aggregator scrapers (RemoteOK,
Arbeitnow, Greenhouse) run alongside as a secondary source.

Current: 6 Python files, CSV + Google Sheets output, pytest tests in `tests/` (run `python -m pytest`), GitHub Actions daily.
Target: hardened extraction, CI gates, orchestration.

# Conventions

Python. pytest for tests. Decisions recorded in `docs/adr/` — read those before proposing
architecture changes.
