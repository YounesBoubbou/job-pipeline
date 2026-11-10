# Working agreement

Claude owns the implementation of this project: design, write, test and fix the code
without waiting for me to write it first. The goal is a first MVP I can test.

- I step in by hand only when I want something done differently. Treat my manual edits
  as the intended direction: build on them, don't revert them
- Push back on my design choices when you disagree, then go with my call
- Explain each decision in plain words, and define jargon the first time it appears

# How work proceeds

`docs/requirements.md` is the single source of truth for the MVP; follow it to the letter.
`docs/tasks.md` is the ordered work list. The main session is the coordinator and uses the
three agents in `.claude/agents/`. For each task, in order:

1. Take the first task in `docs/tasks.md` marked `[ ]`.
2. If it is marked **plan**, give it to the `planner` agent.
3. Give the task (and the plan) to the `builder` agent.
4. Give the result to the `reviewer` agent.
5. On PASS: commit to the `mvp` branch, tick the task, go to the next one.
   On FAIL: send the defects back to the builder. After two failed rounds, mark the task
   `[!]`, write the reason under "Waiting for Younes", and take the next task that does
   not depend on it.

Stop when every task is ticked, or when only blocked and **Younes** tasks are left. Anything
Younes must decide or do goes under "Waiting for Younes" in `docs/tasks.md`.

Never push, never touch `master`, never register a Windows scheduled task: those are Younes's.

# Project

Daily job discovery pipeline plus a web app. The main source is `targets.csv`, a
hand-reviewed list of 1,045 IND recognised sponsors, 186 of them with a job board that is
fetched daily (ADR-0005, ADR-0006) by 12 source kinds in `scrapers/targets.py`. Job-board sites (RemoteOK,
Arbeitnow) and a few company pages (Adyen, Catawiki, Booking.com, SURF) run alongside.

Current: 13 Python modules (9 at the root, 4 in `scrapers/`; the CV and cover-letter
generators are outside the MVP) and 10 test files in `tests/` (run
`venv\Scripts\python.exe -m pytest`). Jobs go to `data/jobs.csv` only, with a run summary
in `data/last_run.json`; the Google Sheet holds only the application tracker. Runs on
Younes's PC each weekday at 08:00 via a Windows scheduled task (`run_daily.ps1`, logs in
`logs/`). Web app: FastAPI (`api.py`) + React/Vite (`frontend/`), started by `start.ps1`,
reachable from a phone on the home Wi-Fi. GitHub Actions runs the tests only.
Target: hardened extraction, CI gates, orchestration.

# Conventions

Python. pytest for tests. Decisions recorded in `docs/adr/` — read those before proposing
architecture changes.
