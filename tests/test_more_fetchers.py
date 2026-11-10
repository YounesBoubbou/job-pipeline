"""Fetchers for the other seven big employers: Lever EU, GetNoticed by display name,
Eightfold, Phenom and Heineken's own site (P9, ADR-0010).
No network: requests.get and requests.post are replaced with fakes."""

import pytest

from scrapers import targets

EF = "https://jobs.example.com"
EF_TOKEN = f"{EF}/careers?domain=example.com"
PH = "https://careers.example.com"
PH_TOKEN = f"{PH}/gb/en"
HK = "https://careers.brewer.example"
GN = "https://careers.grocer.example"


class Response:
    def __init__(self, data=None, status_code=200, text=""):
        self.data, self.status_code, self.text = data, status_code, text

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"{self.status_code} Error")

    def json(self):
        return self.data


def _fake_get(monkeypatch, answer):
    """Answers each GET with answer(url, params) and records (url, params)."""
    calls = []

    def get(url, params=None, headers=None, **kwargs):
        calls.append((url, dict(params or {})))
        return answer(url, params or {})

    monkeypatch.setattr(targets.requests, "get", get)
    return calls


def _fake_post(monkeypatch, answer):
    """Answers each POST with answer(url, json) and records (url, json)."""
    calls = []

    def post(url, json=None, headers=None, **kwargs):
        calls.append((url, json))
        return answer(url, json)

    monkeypatch.setattr(targets.requests, "post", post)
    return calls


@pytest.fixture
def sleeps(monkeypatch):
    calls = []
    monkeypatch.setattr(targets.time, "sleep", calls.append)
    return calls


# Lever EU

def test_lever_eu_uses_eu_api_and_plain_lever_does_not(monkeypatch):
    job = {"text": "Engineer", "categories": {"location": "Amsterdam"}, "hostedUrl": "u", "descriptionPlain": "d"}
    calls = _fake_get(monkeypatch, lambda url, params: Response([job]))

    assert list(targets.FETCHERS["lever_eu"]("tomtom")) == [("Engineer", "Amsterdam", "u", "d")]
    list(targets.FETCHERS["lever"]("acme"))

    assert [c[0] for c in calls] == ["https://api.eu.lever.co/v0/postings/tomtom?mode=json",
                                     "https://api.lever.co/v0/postings/acme?mode=json"]


# GetNoticed: display-name facet and "NLD"

def _getnoticed_answer(facets, vacancies):
    def answer(url, params):
        if url.endswith("/feeds/rss"):
            return Response(status_code=500)
        return Response({"vacancies": vacancies, "facets": facets, "meta": {"totalPageCount": 1}})
    return answer


def test_getnoticed_filters_on_display_name_of_dutch_value(monkeypatch):
    facets = [{"slug": "country", "values": [{"slug": "bel", "value": "Belgium"},
                                             {"slug": "nld", "value": "The Netherlands"}]}]
    vacancy = {"id": 1, "slug": "job-1", "title": "Engineer", "city": "Zaandam", "country": "NLD"}
    calls = _fake_get(monkeypatch, _getnoticed_answer(facets, [vacancy]))

    jobs = list(targets._getnoticed(GN))

    api = [c[1] for c in calls if c[0] == f"{GN}/api/vacancy/"]
    assert api == [{"pageNumber": 1}, {"pageNumber": 1, "filters[country][]": "The Netherlands"}]
    assert jobs == [("Engineer", "Zaandam, Netherlands", f"{GN}/vacature/1/job-1", "")]


def test_spell_nl_replaces_whole_word_only():
    assert targets._spell_nl("Zaandam, NLD") == "Zaandam, Netherlands"
    assert targets._spell_nl("NLDX, Amsterdam") == "NLDX, Amsterdam"


# Eightfold

def _ef_position(n):
    return {"id": n, "name": f"Analyst {n}", "locations": ["Delft, Netherlands", "Barcelona, Spain"],
            "positionUrl": f"/careers/job/{n}"}


def test_eightfold_newer_api_pages_until_count(monkeypatch, sleeps):
    pages = {0: [_ef_position(n) for n in range(10)], 10: [_ef_position(n) for n in range(10, 13)]}
    calls = _fake_get(monkeypatch, lambda url, params: Response(
        {"data": {"positions": pages[params["start"]], "count": 13}}))

    jobs = list(targets._eightfold(EF_TOKEN))

    assert len(jobs) == 13
    assert jobs[0] == ("Analyst 0", "Delft, Netherlands; Barcelona, Spain", f"{EF}/careers/job/0", "")
    assert [c[0] for c in calls] == [f"{EF}/api/pcsx/search"] * 2
    assert calls[0][1] == {"domain": "example.com", "query": "", "location": "Netherlands", "start": 0}
    assert calls[1][1]["start"] == 10
    assert sleeps == [1]


def test_eightfold_falls_back_to_older_api_on_403(monkeypatch, sleeps):
    position = {"id": 5, "name": "Banker", "location": "Amsterdam, Netherlands", "locations": [],
                "canonicalPositionUrl": f"{EF}/careers/job/5", "job_description": "<p>Text</p>"}

    def answer(url, params):
        if url.endswith("/api/pcsx/search"):
            return Response({"message": "PCSX is not enabled for this user."}, status_code=403)
        return Response({"positions": [position], "count": 1})
    calls = _fake_get(monkeypatch, answer)

    jobs = list(targets._eightfold(EF_TOKEN))

    assert jobs == [("Banker", "Amsterdam, Netherlands", f"{EF}/careers/job/5", "<p>Text</p>")]
    assert calls[1] == (f"{EF}/api/apply/v2/jobs",
                        {"domain": "example.com", "start": 0, "num": 10, "location": "Netherlands"})
    assert sleeps == []


def test_eightfold_description(monkeypatch):
    calls = _fake_get(monkeypatch, lambda url, params: Response({"job_description": "Full text"}))

    assert targets._eightfold_description(EF_TOKEN, f"{EF}/careers/job/42") == "Full text"
    assert calls == [(f"{EF}/api/apply/v2/jobs/42", {"domain": "example.com"})]

    _fake_get(monkeypatch, lambda url, params: Response(status_code=500))
    assert targets._eightfold_description(EF_TOKEN, f"{EF}/careers/job/42") == ""


# Phenom

def _ph_job(n):
    return {"title": f"Chemist {n}", "location": "Sassenheim, NLD", "multi_location": ["Sassenheim, NLD"],
            "jobSeqNo": f"SEQ{n}"}


def _ph_answer(aggregations, jobs_by_from, total):
    def answer(url, body):
        jobs = jobs_by_from[body["from"]] if body["selected_fields"] else [_ph_job(999)]
        return Response({"refineSearch": {"totalHits": total if body["selected_fields"] else 500,
                                          "data": {"jobs": jobs, "aggregations": aggregations}}})
    return answer


def test_phenom_asks_for_dutch_country_and_pages(monkeypatch):
    aggregations = [{"field": "country", "value": {"USA": 51, "NLD": 150}}]
    pages = {0: [_ph_job(n) for n in range(100)], 100: [_ph_job(n) for n in range(100, 150)]}
    calls = _fake_post(monkeypatch, _ph_answer(aggregations, pages, 150))

    jobs = list(targets._phenom(PH_TOKEN))

    assert len(jobs) == 150
    assert jobs[0] == ("Chemist 0", "Sassenheim, Netherlands", f"{PH_TOKEN}/job/SEQ0", "")
    assert all(c[0] == f"{PH}/widgets" for c in calls)
    assert [(c[1]["from"], c[1]["selected_fields"]) for c in calls] == [
        (0, {}), (0, {"country": ["NLD"]}), (100, {"country": ["NLD"]})]
    first = calls[0][1]
    assert (first["ddoKey"], first["lang"], first["country"], first["size"]) == ("refineSearch", "en_gb", "gb", 100)


def test_phenom_without_dutch_country_returns_nothing(monkeypatch):
    aggregations = [{"field": "country", "value": {"USA": 51, "GBR": 30}}]
    calls = _fake_post(monkeypatch, _ph_answer(aggregations, {}, 0))

    assert list(targets._phenom(PH_TOKEN)) == []
    assert len(calls) == 1


def test_phenom_description(monkeypatch):
    calls = _fake_post(monkeypatch, lambda url, body: Response(
        {"jobDetail": {"data": {"job": {"description": "Full text"}}}}))

    assert targets._phenom_description(PH_TOKEN, f"{PH_TOKEN}/job/SEQ7") == "Full text"
    assert calls[0][0] == f"{PH}/widgets"
    assert (calls[0][1]["ddoKey"], calls[0][1]["jobSeqNo"], calls[0][1]["lang"]) == ("jobDetail", "SEQ7", "en_gb")

    _fake_post(monkeypatch, lambda url, body: Response(status_code=500))
    assert targets._phenom_description(PH_TOKEN, f"{PH_TOKEN}/job/SEQ7") == ""


# Heineken

def _hk_item(slug, title, place):
    return (f'<div class="job-list-item"><div class="job-title"><p><a href="/job/{slug}">{title}</a></p></div>'
            f'<div class="job-location"><div class="nation">{place}</div></div></div>')


def _hk_page(items, more):
    link = '<a rel="next" href="?page=next">Show more</a>' if more else ""
    return f"<html><body>{''.join(items)}{link}</body></html>"


def test_heineken_reads_html_pages(monkeypatch, sleeps):
    pages = {"0,0,0": _hk_page([_hk_item("a", "Data Analyst", "Amsterdam, Netherlands"),
                                _hk_item("b", "Brewer", "Zoeterwoude, Netherlands")], more=True),
             "0,0,1": _hk_page([_hk_item("b", "Brewer", "Zoeterwoude, Netherlands"),
                                _hk_item("c", "Engineer", "Den Bosch, Netherlands")], more=False)}
    calls = _fake_get(monkeypatch, lambda url, params: Response(text=pages[params["page"]]))

    jobs = list(targets._heineken(HK + "/"))

    assert jobs == [("Data Analyst", "Amsterdam, Netherlands", f"{HK}/job/a", ""),
                    ("Brewer", "Zoeterwoude, Netherlands", f"{HK}/job/b", ""),
                    ("Engineer", "Den Bosch, Netherlands", f"{HK}/job/c", "")]
    assert calls == [(f"{HK}/Job-Listing", {"field_location_country_code_1[]": "NL", "page": "0,0,0"}),
                     (f"{HK}/Job-Listing", {"field_location_country_code_1[]": "NL", "page": "0,0,1"})]
    assert sleeps == [5]


def test_heineken_stops_on_empty_page(monkeypatch, sleeps):
    calls = _fake_get(monkeypatch, lambda url, params: Response(text=_hk_page([], more=True)))

    assert list(targets._heineken(HK)) == []
    assert len(calls) == 1


# Through fetch_target_jobs

def test_new_kinds_are_fetched_from_targets(monkeypatch, sleeps):
    rows = [{"company": "Eight", "source": "eightfold", "token": EF_TOKEN, "board_status": "hand"},
            {"company": "Paint", "source": "phenom", "token": PH_TOKEN, "board_status": "hand"},
            {"company": "Beer", "source": "heineken", "token": HK, "board_status": "hand"},
            {"company": "Maps", "source": "lever_eu", "token": "maps", "board_status": "hand"}]
    monkeypatch.setattr(targets, "load_targets", lambda: rows)
    lever_job = {"text": "Engineer", "categories": {"location": "Amsterdam"}, "hostedUrl": "u"}

    def get(url, params):
        if url.startswith(EF):
            return Response({"data": {"positions": [_ef_position(1)], "count": 1}})
        if url.startswith(HK):
            return Response(text=_hk_page([_hk_item("a", "Brewer", "Amsterdam, Netherlands")], more=False))
        return Response([lever_job])
    _fake_get(monkeypatch, get)
    _fake_post(monkeypatch, _ph_answer([{"field": "country", "value": {"NLD": 1}}], {0: [_ph_job(1)]}, 1))

    jobs, boards, failed = targets.fetch_target_jobs()

    assert failed == []
    assert [(b["name"], b["source"], b["fetched"]) for b in boards] == [
        ("Eight", "target:eightfold", 1), ("Paint", "target:phenom", 1),
        ("Beer", "target:heineken", 1), ("Maps", "target:lever_eu", 1)]
