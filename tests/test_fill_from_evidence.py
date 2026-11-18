"""ats_resolver.fill_from_evidence: board addresses from the careers-page scan (B-1,
ADR-0014). No network: the fetchers are fakes, sleep is a no-op, targets.csv is a temp file."""

import csv
import json

import pytest

import ats_resolver as ar
import coverage_scan as cs
from filters import names_nl_place
from scrapers.targets import FETCHERS

FIELDS = ["company", "ind_registered_name", "other_ind_entities", "category", "already_applied",
          "source", "token", "board_status", "website", "careers_url", "ats_seen", "ats_evidence",
          "scan_note"]
PROTECTED = ["company", "ind_registered_name", "other_ind_entities", "category", "already_applied"]


def job(title, location):
    return (title, location, f"https://example.com/{title}", "")


# token -> postings, or an exception to raise
BOARDS = {
    "nlboard": [job("Data Engineer", "Amsterdam, Netherlands"), job("Analyst", "Berlin")],
    "berlinonly": [job("Data Engineer", "Berlin, Germany")],
    "empty": [],
    "samples": [job("Engineer (Sample)", "Amsterdam")],
    "https://acme.wd3.myworkdayjobs.com/careers": [job("Engineer", "Eindhoven")],
}


class Fetcher:
    """Fake board reader that records each token it was asked for."""

    def __init__(self, boards):
        self.boards, self.calls = boards, []

    def __call__(self, token):
        self.calls.append(token)
        result = self.boards[token]
        if isinstance(result, Exception):
            raise result
        yield from result


def lazy_failure(token):
    yield job("Engineer", "Amsterdam")
    raise ValueError("page 2; broke\nhalfway")


def make_row(company, status="none", source="", token="", ats_seen="", evidence="", note="requests=4"):
    return {"company": company, "ind_registered_name": f"{company} B.V.", "other_ind_entities": "",
            "category": "Dutch tech & scale-ups", "already_applied": "", "source": source, "token": token,
            "board_status": status, "website": "", "careers_url": "", "ats_seen": ats_seen,
            "ats_evidence": evidence, "scan_note": note}


def write_csv(path, rows):
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def read_rows(path):
    with open(path, encoding="utf-8", newline="") as f:
        return {r["company"]: r for r in csv.DictReader(f)}


@pytest.fixture
def fake(monkeypatch):
    fetcher = Fetcher(BOARDS)
    for kind in ("ashby", "greenhouse", "workday", "recruitee", "phenom"):
        monkeypatch.setitem(FETCHERS, kind, fetcher)
    monkeypatch.setitem(FETCHERS, "lever", lazy_failure)
    monkeypatch.setattr(ar.time, "sleep", lambda s: None)
    return fetcher


def run(tmp_path, rows, **kw):
    path = tmp_path / "targets.csv"
    write_csv(path, rows)
    summary = ar.fill_from_evidence(str(path), summary_path=str(tmp_path / "fill_summary.json"), **kw)
    return path, read_rows(path), summary


def test_board_with_nl_job_is_auto(tmp_path, fake):
    _, rows, summary = run(tmp_path, [make_row("Acme", ats_seen="ashby", evidence="https://jobs.ashbyhq.com/nlboard")])
    r = rows["Acme"]
    assert (r["source"], r["token"], r["board_status"]) == ("ashby", "nlboard", "auto")
    assert r["scan_note"] == "requests=4; fill: auto, 2 listings"
    assert summary["new_auto"] == [{"name": "Acme", "source": "ashby:nlboard", "fetched": 2}]
    assert fake.calls == ["nlboard"]


def test_workday_token_is_the_board_address(tmp_path, fake):
    ev = "https://acme.wd3.myworkdayjobs.com/en-US/careers/job/123"
    _, rows, _ = run(tmp_path, [make_row("Acme", ats_seen="workday", evidence=ev)])
    assert rows["Acme"]["token"] == "https://acme.wd3.myworkdayjobs.com/careers"
    assert rows["Acme"]["board_status"] == "auto"


@pytest.mark.parametrize("token, note", [
    ("berlinonly", "fill: review, no NL place in 1 listings"),
    ("empty", "fill: review, 0 listings"),
    ("samples", 'fill: review, "(Sample)" job in 1 listings'),
])
def test_board_without_nl_job_is_review(tmp_path, fake, token, note):
    _, rows, summary = run(tmp_path, [make_row("Acme", ats_seen="ashby", evidence=f"https://jobs.ashbyhq.com/{token}")])
    r = rows["Acme"]
    assert (r["source"], r["token"], r["board_status"]) == ("ashby", token, "review")
    assert r["scan_note"].endswith(note)
    assert summary["new_auto"] == []


def test_failed_fetch_leaves_none_row_out(tmp_path, fake):
    _, rows, summary = run(tmp_path, [make_row("Acme", ats_seen="lever", evidence="https://jobs.lever.co/acme")])
    r = rows["Acme"]
    assert (r["source"], r["token"], r["board_status"]) == ("", "", "none")
    assert r["scan_note"] == "requests=4; fill: left out, fetch failed ValueError: page 2 broke halfway"
    assert summary["failed"] == [{"name": "Acme", "source": "lever:acme", "reason": "ValueError: page 2 broke halfway"}]


def test_failed_fetch_restores_review_row(tmp_path, fake):
    row = make_row("Acme", status="review", source="recruitee", token="acmeold",
                   ats_seen="lever", evidence="https://jobs.lever.co/acme")
    _, rows, _ = run(tmp_path, [row])
    r = rows["Acme"]
    assert (r["source"], r["token"], r["board_status"]) == ("recruitee", "acmeold", "review")
    assert "fill: left out, fetch failed ValueError" in r["scan_note"]


def test_long_error_is_cut(tmp_path, fake):
    BOARDS["huge"] = RuntimeError("x" * 500)
    try:
        _, rows, _ = run(tmp_path, [make_row("Acme", ats_seen="ashby", evidence="https://jobs.ashbyhq.com/huge")])
    finally:
        del BOARDS["huge"]
    assert len(rows["Acme"]["scan_note"].split("fetch failed ")[1]) == 150


def test_no_token_in_evidence_is_left_out_without_fetch(tmp_path, fake):
    ev = "https://careers.example.com | https://cdn.phenompeople.com/CareerConnectResources/x.js"
    _, rows, summary = run(tmp_path, [make_row("Acme", ats_seen="phenom", evidence=ev)])
    r = rows["Acme"]
    assert (r["source"], r["token"], r["board_status"]) == ("", "", "none")
    assert r["scan_note"].endswith("fill: left out, no token in evidence")
    assert summary["left_out"] == [{"name": "Acme", "reason": "no token in evidence"}]
    assert fake.calls == []


def test_same_board_as_old_auto_row_is_left_out(tmp_path, fake):
    rows_in = [make_row("Prosus", status="auto", source="ashby", token="NLboard/"),
               make_row("MIH Fintech", ats_seen="ashby", evidence="https://jobs.ashbyhq.com/nlboard")]
    _, rows, _ = run(tmp_path, rows_in)
    r = rows["MIH Fintech"]
    assert (r["source"], r["token"], r["board_status"]) == ("", "", "none")
    assert r["scan_note"].endswith("fill: left out, same board as Prosus (auto)")
    assert fake.calls == []


def test_two_new_rows_on_one_board_are_both_review(tmp_path, fake):
    ev = "https://acme.wd3.myworkdayjobs.com/careers"
    _, rows, summary = run(tmp_path, [make_row("Cloud Group", ats_seen="workday", evidence=ev),
                                      make_row("Cloud++", ats_seen="workday", evidence=ev + "/")])
    assert rows["Cloud Group"]["board_status"] == rows["Cloud++"]["board_status"] == "review"
    assert rows["Cloud Group"]["token"] == ev
    assert rows["Cloud Group"]["scan_note"].endswith("fill: review, same board as Cloud++")
    assert rows["Cloud++"]["scan_note"].endswith("fill: review, same board as Cloud Group")
    assert fake.calls == [] and summary["boards"] == []


def test_review_row_gets_evidence_token_and_old_one_in_note(tmp_path, fake):
    row = make_row("Eye", status="review", source="recruitee", token="eyesecurity",
                   ats_seen="ashby", evidence="https://jobs.ashbyhq.com/nlboard")
    _, rows, _ = run(tmp_path, [row])
    r = rows["Eye"]
    assert (r["source"], r["token"], r["board_status"]) == ("ashby", "nlboard", "auto")
    assert r["scan_note"] == "requests=4; fill: auto, 2 listings, was recruitee:eyesecurity"


def test_rerun_replaces_fill_note(tmp_path, fake):
    row = make_row("Acme", ats_seen="ashby", evidence="https://jobs.ashbyhq.com/empty",
                   note="also: lever; requests=4; fill: left out, fetch failed X: y")
    _, rows, _ = run(tmp_path, [row])
    assert rows["Acme"]["scan_note"] == "also: lever; requests=4; fill: review, 0 listings"


def test_company_option_and_selection(tmp_path, fake):
    rows_in = [make_row("Acme", ats_seen="ashby", evidence="https://jobs.ashbyhq.com/nlboard"),
               make_row("Other", ats_seen="ashby", evidence="https://jobs.ashbyhq.com/empty"),
               make_row("Teamtailor co", ats_seen="Teamtailor", evidence="https://x.teamtailor.com"),
               make_row("Hand", status="hand", source="ashby", token="handboard", ats_seen="ashby",
                        evidence="https://jobs.ashbyhq.com/berlinonly")]
    _, rows, _ = run(tmp_path, rows_in, companies=["Acme"])
    assert fake.calls == ["nlboard"]
    assert rows["Other"]["scan_note"] == rows["Teamtailor co"]["scan_note"] == "requests=4"


def test_old_rows_and_file_format_untouched(tmp_path, fake):
    """B5: auto/hand lines byte-identical; LF, no BOM; protected columns and order kept."""
    rows_in = [make_row("Old Auto", status="auto", source="greenhouse", token="old", ats_seen="ashby",
                        evidence="https://jobs.ashbyhq.com/nlboard", note='a "quoted", note'),
               make_row("Acme", ats_seen="ashby", evidence="https://jobs.ashbyhq.com/nlboard"),
               make_row("Old Hand", status="hand", source="lever", token="h", ats_seen="lever",
                        evidence="https://jobs.lever.co/acme"),
               make_row("Fail", ats_seen="lever", evidence="https://jobs.lever.co/acme"),
               make_row("Nothing", ats_seen="custom")]
    path = tmp_path / "targets.csv"
    write_csv(path, rows_in)
    before = path.read_bytes().split(b"\n")
    ar.fill_from_evidence(str(path), summary_path=str(tmp_path / "s.json"))
    raw = path.read_bytes()
    after = raw.split(b"\n")
    assert b"\r" not in raw and not raw.startswith(b"\xef\xbb\xbf")
    assert after[0] == before[0]  # header
    for i in (1, 3, 5):  # Old Auto, Old Hand, Nothing
        assert after[i] == before[i]
    rows = list(read_rows(path).values())
    assert [r["company"] for r in rows] == [r["company"] for r in rows_in]
    for new, old in zip(rows, rows_in):
        assert {c: new[c] for c in PROTECTED} == {c: old[c] for c in PROTECTED}


def test_summary_file(tmp_path, fake):
    rows_in = [make_row("Acme", ats_seen="ashby", evidence="https://jobs.ashbyhq.com/nlboard"),
               make_row("Fail", ats_seen="lever", evidence="https://jobs.lever.co/acme"),
               make_row("NoToken", ats_seen="phenom", evidence="https://cdn.phenompeople.com/CareerConnectResources/x")]
    run(tmp_path, rows_in)
    summary = json.loads((tmp_path / "fill_summary.json").read_text(encoding="utf-8"))
    assert summary["boards"] == [{"name": "Acme", "source": "ashby:nlboard", "fetched": 2, "status": "auto"}]
    assert [e["name"] for e in summary["failed"]] == ["Fail"]
    assert summary["left_out"] == [{"name": "NoToken", "reason": "no token in evidence"}]
    assert [e["name"] for e in summary["new_auto"]] == ["Acme"]


# ---------------------------------------------------------------- refactor and fixes

def _old_has_nl_job(postings):
    """_has_nl_job as it was before status_from_postings."""
    if any("(sample)" in title.lower() for title, _, _, _ in postings):
        return False
    return any(names_nl_place(loc) for _, loc, _, _ in postings)


@pytest.mark.parametrize("postings", [
    [], [job("A", "Amsterdam")], [job("A", "Berlin")], [job("A", "Remote")],
    [job("A (Sample)", "Amsterdam")], [job("A", "Utrecht"), job("B (sample)", "Berlin")],
    [job("A", "Berlin"), job("B", "Rotterdam, NL")],
])
def test_status_from_postings_matches_old_rule(monkeypatch, postings):
    assert (ar.status_from_postings(postings) == "auto") == _old_has_nl_job(postings)
    monkeypatch.setitem(FETCHERS, "ashby", lambda token: iter(postings))
    assert ar._has_nl_job("ashby", "x") == _old_has_nl_job(postings)


def test_save_targets_writes_lf(tmp_path, monkeypatch):
    path = tmp_path / "targets.csv"
    monkeypatch.setattr(ar, "TARGETS_PATH", str(path))
    ar._save_targets([make_row("Acme"), make_row("Beta")], FIELDS)
    raw = path.read_bytes()
    assert b"\r" not in raw and raw.count(b"\n") == 3


def test_recruitee_analytics_subdomain_is_not_a_board():
    ev = ("https://careers-analytics.recruitee.com&quot;,&quot;appEnv&quot;:&quot;production&quot;,"
          "&quot;atsHost&quot;:&quot;recruitee.com&quot;")
    assert cs.token_from_evidence("recruitee", ev) == ""
    assert "recruitee" not in cs.detect("https://jobs.example.com", f'<script src="{ev}"></script>')
    assert cs.token_from_evidence("recruitee", "https://acme.recruitee.com/o/engineer") == "acme"
