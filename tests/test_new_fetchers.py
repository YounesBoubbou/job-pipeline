"""Booking.com (iCIMS Jibe) and ABN AMRO (GetNoticed) fetchers (P9, ADR-0009).
No network: requests.get is replaced with a fake."""

from scrapers import targets

JIBE = "https://jobs.example.com"
GN = "https://www.werkenbijexample.nl"


class Response:
    def __init__(self, data=None, content=b""):
        self.data, self.content = data, content

    def raise_for_status(self):
        if isinstance(self.data, Exception):
            raise self.data

    def json(self):
        return self.data


def _fake_get(monkeypatch, answer):
    """Answers each GET with answer(url, params) and records (url, params, headers)."""
    calls = []

    def get(url, params=None, headers=None, **kwargs):
        calls.append((url, dict(params or {}), headers or {}))
        return answer(url, params or {})

    monkeypatch.setattr(targets.requests, "get", get)
    return calls


def _jibe_job(n):
    return {"data": {"title": f"Data Engineer {n}", "full_location": "Amsterdam, Netherlands",
                     "meta_data": {"canonical_url": f"{JIBE}/jobs/{n}"}, "description": f"<p>Job {n}</p>"}}


def test_jibe_asks_for_netherlands_and_maps_fields(monkeypatch):
    calls = _fake_get(monkeypatch, lambda url, params: Response({"jobs": [_jibe_job(1)], "totalCount": 1}))

    jobs = list(targets._jibe(JIBE + "/"))

    assert jobs == [("Data Engineer 1", "Amsterdam, Netherlands", f"{JIBE}/jobs/1", "<p>Job 1</p>")]
    assert calls[0][0] == f"{JIBE}/api/jobs"
    assert calls[0][1] == {"page": 1, "limit": 100, "country": "Netherlands"}


def test_jibe_pages_until_total_and_waits_between_pages(monkeypatch):
    pages = {1: [_jibe_job(n) for n in range(100)], 2: [_jibe_job(n) for n in range(100, 150)]}
    calls = _fake_get(monkeypatch, lambda url, params: Response({"jobs": pages[params["page"]], "totalCount": 150}))
    sleeps = []
    monkeypatch.setattr(targets.time, "sleep", sleeps.append)

    jobs = list(targets._jibe(JIBE))

    assert len(jobs) == 150
    assert [c[1]["page"] for c in calls] == [1, 2]
    assert sleeps == [5]


def _vacancy(n, city="Amsterdam", country="Netherlands"):
    return {"id": n, "slug": f"job-{n}", "title": f"Engineer {n}", "city": city, "country": country}


def _rss(items):
    body = "".join(f"<item><title>t</title><link>{GN}/vacature/{i}/job-{i}</link>"
                   f"<description>{d}</description></item>" for i, d in items)
    return f"<?xml version='1.0'?><rss><channel>{body}</channel></rss>".encode()


def _getnoticed_answer(pages, facets, rss=b"<rss><channel/></rss>"):
    """pages maps (pageNumber, filtered?) to a list of vacancies."""
    def answer(url, params):
        if url.endswith("/feeds/rss"):
            return Response(rss) if isinstance(rss, Exception) else Response(content=rss)
        filtered = any(k.startswith("filters[") for k in params)
        vacancies = pages[(params["pageNumber"], filtered)]
        total = max(n for n, f in pages if f == filtered)
        return Response({"vacancies": vacancies, "facets": facets, "meta": {"totalPageCount": total}})
    return answer


def test_getnoticed_uses_netherlands_facet_and_pages(monkeypatch):
    facets = [{"slug": "vakgebied", "values": [{"slug": "data"}]},
              {"slug": "land", "values": [{"slug": "belgie"}, {"slug": "nederland"}]}]
    pages = {(1, False): [_vacancy(9)], (1, True): [_vacancy(1)], (2, True): [_vacancy(2)]}
    calls = _fake_get(monkeypatch, _getnoticed_answer(pages, facets))

    jobs = list(targets._getnoticed(GN))

    assert [j[0] for j in jobs] == ["Engineer 1", "Engineer 2"]
    api = [c for c in calls if c[0] == f"{GN}/api/vacancy/"]
    assert [c[1] for c in api] == [{"pageNumber": 1},
                                   {"pageNumber": 1, "filters[land][]": "nederland"},
                                   {"pageNumber": 2, "filters[land][]": "nederland"}]
    assert all(c[2].get("X-Requested-With") == "XMLHttpRequest" for c in api)


def test_getnoticed_without_country_facet_reads_all_pages(monkeypatch):
    facets = [{"slug": "vakgebied", "values": [{"slug": "data"}]}]
    pages = {(1, False): [_vacancy(1)], (2, False): [_vacancy(2)]}
    calls = _fake_get(monkeypatch, _getnoticed_answer(pages, facets))

    jobs = list(targets._getnoticed(GN))

    assert [j[0] for j in jobs] == ["Engineer 1", "Engineer 2"]
    assert [c[1] for c in calls if c[0] == f"{GN}/api/vacancy/"] == [{"pageNumber": 1}, {"pageNumber": 2}]


def test_getnoticed_maps_location_url_and_rss_description(monkeypatch):
    pages = {(1, False): [_vacancy(7), _vacancy(8, city="", country="Belgium")]}
    rss = _rss([(7, "Full text of seven")])
    _fake_get(monkeypatch, _getnoticed_answer(pages, [], rss))

    jobs = list(targets._getnoticed(GN + "/"))

    assert jobs == [("Engineer 7", "Amsterdam, Netherlands", f"{GN}/vacature/7/job-7", "Full text of seven"),
                    ("Engineer 8", "Belgium", f"{GN}/vacature/8/job-8", "")]


def test_getnoticed_rss_failure_leaves_description_empty(monkeypatch):
    pages = {(1, False): [_vacancy(7)]}
    _fake_get(monkeypatch, _getnoticed_answer(pages, [], RuntimeError("500 Server Error")))

    jobs = list(targets._getnoticed(GN))

    assert jobs == [("Engineer 7", "Amsterdam, Netherlands", f"{GN}/vacature/7/job-7", "")]


def test_new_kinds_are_fetched_from_targets(monkeypatch):
    rows = [{"company": "Booking", "source": "jibe", "token": JIBE, "board_status": "hand"},
            {"company": "Bank", "source": "getnoticed", "token": GN, "board_status": "hand"}]
    monkeypatch.setattr(targets, "load_targets", lambda: rows)
    getnoticed = _getnoticed_answer({(1, False): [_vacancy(1), _vacancy(2)]}, [])
    _fake_get(monkeypatch, lambda url, params: (
        Response({"jobs": [_jibe_job(1)], "totalCount": 1}) if url.startswith(JIBE) else getnoticed(url, params)))

    jobs, boards, failed = targets.fetch_target_jobs()

    assert failed == []
    assert [(b["name"], b["source"], b["fetched"]) for b in boards] == [
        ("Booking", "target:jibe", 1), ("Bank", "target:getnoticed", 2)]
