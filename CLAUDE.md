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

Daily job discovery pipeline. Starts from the IND recognised sponsor register, resolves
sponsors to their job boards, and fetches openings. Aggregator scrapers (RemoteOK,
Arbeitnow, Greenhouse) run alongside as a secondary source.

Current: 6 Python files, CSV + Google Sheets output, pytest tests in `tests/` (run `python -m pytest`), GitHub Actions daily.
Target: hardened extraction, CI gates, orchestration.

# Conventions

Python. pytest for tests. Decisions recorded in `docs/adr/` — read those before proposing
architecture changes.
