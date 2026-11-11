"""
ats_resolver.py — Resolve IND sponsors to their ATS careers board (ADR-0003, step 2).

For each normalised sponsor name, guess two board tokens and ask each vendor's public
API whether that board exists. Results go to data/ats_map.json, misses included (null),
so a name is never probed twice. Run by hand; each run handles the next batch:

    python ats_resolver.py          # next ATS_BATCH_SIZE names
    python ats_resolver.py 20       # next 20 names
    python ats_resolver.py targets  # fill source/token in targets.csv instead (ADR-0006)
    python ats_resolver.py evidence [--company NAME]...  # from the careers-page scan (ADR-0014)
"""

import csv
import json
import os
import re
import sys
import time

import requests

from config import ATS_MAP_PATH, ATS_BATCH_SIZE
from filters import names_nl_place
from ind_checker import load_sponsors, normalise_name
from scrapers.targets import FETCHERS, TARGETS_PATH, load_targets

HEADERS = {
    "User-Agent": "job-pipeline/1.0 (personal job search; github.com/YounesBoubbou/job-pipeline)"
}
REQUEST_DELAY = 1.0  # seconds between requests

# vendor -> (URL template, test on a 200 response).
# SmartRecruiters returns 200 for any token, so only a board with at least one job
# counts as a hit. Workable is left out — see ADR-0004.
VENDORS = {
    "greenhouse":      ("https://boards-api.greenhouse.io/v1/boards/{t}", lambda r: True),
    "recruitee":       ("https://{t}.recruitee.com/api/offers/", lambda r: True),
    "lever":           ("https://api.lever.co/v0/postings/{t}?mode=json", lambda r: True),
    "ashby":           ("https://api.ashbyhq.com/posting-api/job-board/{t}", lambda r: True),
    "smartrecruiters": ("https://api.smartrecruiters.com/v1/companies/{t}/postings",
                        lambda r: r.json().get("totalFound", 0) > 0),
}


def board_tokens(name: str) -> list:
    """'flow traders' -> ['flowtraders', 'flow-traders'];  'adyen' -> ['adyen']."""
    words = re.findall(r"[a-z0-9]+", name)
    return list(dict.fromkeys(["".join(words), "-".join(words)]))


def _probe(vendor: str, token: str):
    """True = board found, False = no board, None = request failed (try again next run)."""
    url, is_hit = VENDORS[vendor]
    if vendor == "recruitee" and len(token) > 63:  # longer than a DNS label allows
        return False
    try:
        r = requests.get(url.format(t=token), headers=HEADERS, timeout=10,
                         allow_redirects=False)
    except requests.RequestException:
        return None
    finally:
        time.sleep(REQUEST_DELAY)
    if r.status_code == 200:
        try:
            return is_hit(r)
        except ValueError:  # 200 but not JSON
            return False
    # Recruitee answers 403 for some subdomains that have no board (e.g. amazon, factset).
    if r.status_code in (403, 404, 301, 302):
        return False
    return None  # 429 / 5xx — don't record a miss


def resolve(name: str):
    """
    Returns {'vendor': ..., 'token': ...} on the first hit, None if every probe
    said no, or 'error' if nothing was found but at least one probe failed.
    """
    failed = False
    for token in board_tokens(name):
        if not token:
            continue
        for vendor in VENDORS:
            result = _probe(vendor, token)
            if result:
                return {"vendor": vendor, "token": token}
            if result is None:
                failed = True
    return "error" if failed else None


def load_map() -> dict:
    if not os.path.exists(ATS_MAP_PATH):
        return {}
    with open(ATS_MAP_PATH, encoding="utf-8") as f:
        return json.load(f)


def save_map(ats_map: dict):
    os.makedirs(os.path.dirname(ATS_MAP_PATH), exist_ok=True)
    tmp = ATS_MAP_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(ats_map, f, indent=1, sort_keys=True)
    os.replace(tmp, ATS_MAP_PATH)


def status_from_postings(postings) -> str:
    """
    A found board counts ('auto') only if it lists at least one job in the Netherlands
    (ADR-0006); otherwise it is 'review'. A bare "Remote" doesn't count here: it says
    nothing about which company owns the board. Recruitee demo accounts (accenture, ey)
    carry "(Sample)" jobs set in Amsterdam, so a board with one is never accepted.
    """
    if any("(sample)" in title.lower() for title, _, _, _ in postings):
        return "review"
    return "auto" if any(names_nl_place(loc) for _, loc, _, _ in postings) else "review"


def _has_nl_job(vendor: str, token: str) -> bool:
    return status_from_postings(list(FETCHERS[vendor](token))) == "auto"


def resolve_targets(limit: int = None):
    """
    Fill source/token/board_status in targets.csv for rows not probed yet.
    board_status: 'auto' = board with NL jobs, 'review' = board without NL jobs
    (possibly another company with the same name), 'none' = no board found.
    Rows whose probes failed are left blank and retried next run.
    """
    rows = load_targets()
    fields = list(rows[0].keys())
    for col in ("source", "token", "board_status"):
        if col not in fields:
            fields.append(col)
    pending = [r for r in rows if not r.get("board_status")]
    todo = pending[:limit]
    print(f"  {len(rows) - len(pending)}/{len(rows)} targets already probed — probing {len(todo)}...")

    for i, row in enumerate(todo, 1):
        names = [normalise_name(row["company"]), normalise_name(row["ind_registered_name"])]
        result, failed = None, False
        for name in dict.fromkeys(n for n in names if n):
            result = resolve(name)
            if result == "error":
                failed, result = True, None
            elif result:
                break
        if result is None and failed:
            print(f"  [{i}/{len(todo)}] {row['company']}: request failed, will retry")
            continue
        if result is None:
            row["board_status"] = "none"
        else:
            row["source"], row["token"] = result["vendor"], result["token"]
            try:
                nl = _has_nl_job(result["vendor"], result["token"])
            except Exception as e:
                print(f"  [{i}/{len(todo)}] {row['company']}: board fetch failed ({e}), will retry")
                row["source"] = row["token"] = ""
                continue
            row["board_status"] = "auto" if nl else "review"
            print(f"  [{i}/{len(todo)}] {row['company']}: {result['vendor']}:{result['token']} {row['board_status']}")
        _save_targets(rows, fields)  # after every row, so an interrupted run loses nothing

    counts = {s: sum(1 for r in rows if r.get("board_status") == s) for s in ("auto", "review", "none")}
    print(f"\n  Overall: {counts}, {sum(1 for r in rows if not r.get('board_status'))} not probed yet")


def _save_targets(rows: list, fields: list):
    tmp = TARGETS_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")  # the file is kept LF
        w.writeheader()
        w.writerows(rows)
    os.replace(tmp, TARGETS_PATH)


# ---------------------------------------------------------------- scan evidence (ADR-0014)

FILL_SUMMARY_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "fill_summary.json")


def _same_board(token: str) -> str:
    return token.strip().rstrip("/").lower()


def _set_fill_note(row: dict, outcome: str):
    """Append '; fill: <outcome>' to scan_note, replacing the one an earlier run wrote."""
    parts = [p for p in row["scan_note"].split("; ") if p and not p.startswith("fill: ")]
    row["scan_note"] = "; ".join(parts + [f"fill: {outcome}"])


def _reason(e: Exception) -> str:
    """A fetch error as one short scan_note part: no ';' or line breaks, ~150 characters."""
    return re.sub(r"\s*[;\r\n]+\s*", " ", f"{type(e).__name__}: {e}").strip()[:150]


def fill_from_evidence(path: str = TARGETS_PATH, companies=(), summary_path: str = FILL_SUMMARY_PATH) -> dict:
    """
    Fill source/token/board_status from the careers-page scan (ADR-0014): every row that
    is not auto/hand and whose ats_seen is a kind we read. Old auto/hand rows are never
    written. One fetch per board, no retries; status as in ADR-0006.
    """
    from coverage_scan import save_targets, token_from_evidence

    rows = load_targets(path)
    fields = list(rows[0].keys())
    todo = [r for r in rows if r["board_status"] not in ("auto", "hand") and r["ats_seen"] in FETCHERS
            and (not companies or r["company"] in companies)]
    kept = {_same_board(r["token"]): r["company"] for r in rows
            if r["board_status"] in ("auto", "hand") and r["token"]}
    # Every token first, so two new rows on one board are both known before any fetch.
    tokens = [token_from_evidence(r["ats_seen"], r["ats_evidence"]) for r in todo]
    owners = {}
    for r, token in zip(todo, tokens):
        if token:
            owners.setdefault(_same_board(token), []).append(r["company"])
    print(f"  Filling {len(todo)} rows from the careers-page scan's evidence...")

    summary = {"boards": [], "failed": [], "left_out": [], "new_auto": []}
    for i, (row, token) in enumerate(zip(todo, tokens), 1):
        kind, old = row["ats_seen"], (row["source"], row["token"])
        was = f", was {old[0]}:{old[1]}" if row["board_status"] == "review" and old[1] else ""
        key = _same_board(token)
        others = [c for c in owners.get(key, []) if c != row["company"]]
        if not token:  # a none row stays blank, a review row keeps what it had
            if row["board_status"] != "review":
                row["source"] = row["token"] = ""
            outcome = "left out, no token in evidence"
            summary["left_out"].append({"name": row["company"], "reason": "no token in evidence"})
        elif key in kept:  # already fetched daily under another company
            row["source"] = row["token"] = ""
            outcome = f"left out, same board as {kept[key]} (auto)"
            summary["left_out"].append({"name": row["company"], "reason": f"same board as {kept[key]}"})
        elif others:  # B-2 decides which company owns the board
            row["source"], row["token"], row["board_status"] = kind, token, "review"
            outcome = f"review, same board as {', '.join(others)}{was}"
        else:
            try:
                postings = list(FETCHERS[kind](token))
            except Exception as e:  # one broken board must not stop the run; the row is left out
                if row["board_status"] != "review":
                    row["source"] = row["token"] = ""
                reason = _reason(e)
                outcome = f"left out, fetch failed {reason}"
                summary["failed"].append({"name": row["company"], "source": f"{kind}:{token}", "reason": reason})
            else:
                row["source"], row["token"] = kind, token
                row["board_status"] = status = status_from_postings(postings)
                n = len(postings)
                if status == "auto":
                    outcome = f"auto, {n} listings{was}"
                    summary["new_auto"].append({"name": row["company"], "source": f"{kind}:{token}", "fetched": n})
                elif any("(sample)" in title.lower() for title, _, _, _ in postings):
                    outcome = f'review, "(Sample)" job in {n} listings{was}'
                elif n == 0:
                    outcome = f"review, 0 listings{was}"
                else:
                    outcome = f"review, no NL place in {n} listings{was}"
                summary["boards"].append({"name": row["company"], "source": f"{kind}:{token}",
                                          "fetched": n, "status": status})
            time.sleep(REQUEST_DELAY)
        _set_fill_note(row, outcome)
        save_targets(rows, fields, path)  # after every row, so an interrupted run loses nothing
        print(f"  [{i}/{len(todo)}] {row['company']}: {outcome}")

    print(f"\n  Boards fetched: {len(summary['boards'])}, failed: {len(summary['failed'])}, "
          f"left out: {len(summary['left_out'])}")
    print("\n  Left out:")
    for e in summary["left_out"]:
        print(f"    {e['name']}: {e['reason']}")
    print("\n  Failed:")
    for e in summary["failed"]:
        print(f"    {e['name']} ({e['source']}): {e['reason']}")
    print("\n  New auto rows (checked by hand in B-2):")
    for e in summary["new_auto"]:
        print(f"    {e['name']}: {e['source']} ({e['fetched']} listings)")

    os.makedirs(os.path.dirname(summary_path), exist_ok=True)
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=1, ensure_ascii=False)
    return summary


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "evidence":
        args, companies = sys.argv[2:], []
        while args:
            if args[0] != "--company" or len(args) < 2:
                sys.exit("usage: python ats_resolver.py evidence [--company NAME]...")
            companies.append(args[1])
            args = args[2:]
        sys.stdout.reconfigure(errors="replace")  # a company name the console can't show must not stop the run
        return fill_from_evidence(companies=companies)
    if len(sys.argv) > 1 and sys.argv[1] == "targets":
        return resolve_targets(int(sys.argv[2]) if len(sys.argv) > 2 else None)
    batch_size = int(sys.argv[1]) if len(sys.argv) > 1 else ATS_BATCH_SIZE
    sponsors = sorted(load_sponsors())
    ats_map = load_map()
    todo = [n for n in sponsors if n not in ats_map][:batch_size]

    print(f"  {len(ats_map)}/{len(sponsors)} sponsors already probed — probing {len(todo)} more...")
    resolved = errors = 0
    for i, name in enumerate(todo, 1):
        result = resolve(name)
        if result == "error":
            errors += 1  # left out of the map, so it's retried next run
            print(f"  [{i}/{len(todo)}] {name}: request failed, will retry")
            continue
        ats_map[name] = result
        save_map(ats_map)  # after every name, so an interrupted run loses nothing
        if result:
            resolved += 1
            print(f"  [{i}/{len(todo)}] {name}: {result['vendor']}:{result['token']}")

    total_hits = sum(1 for v in ats_map.values() if v)
    print(f"\n  This run: {len(todo)} probed, {resolved} resolved, {errors} failed (retry next run)")
    print(f"  Overall:  {len(ats_map)}/{len(sponsors)} probed, {total_hits} resolved")


if __name__ == "__main__":
    main()
