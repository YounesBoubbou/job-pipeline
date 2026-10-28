"""
ats_resolver.py — Resolve IND sponsors to their ATS careers board (ADR-0003, step 2).

For each normalised sponsor name, guess two board tokens and ask each vendor's public
API whether that board exists. Results go to data/ats_map.json, misses included (null),
so a name is never probed twice. Run by hand; each run handles the next batch:

    python ats_resolver.py          # next ATS_BATCH_SIZE names
    python ats_resolver.py 20       # next 20 names
"""

import json
import os
import re
import sys
import time

import requests

from config import ATS_MAP_PATH, ATS_BATCH_SIZE
from ind_checker import load_sponsors

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
    if r.status_code in (404, 301, 302):
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


def main():
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
