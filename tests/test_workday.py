"""Workday boards are asked for their Netherlands jobs only (P6, ADR-0008).
No network: requests.post and requests.get are replaced with fakes."""

from scrapers import targets

TOKEN = "https://acme.wd3.myworkdayjobs.com/External"
API = "https://acme.wd3.myworkdayjobs.com/wday/cxs/acme/External/jobs"


def _job(n, location="Amsterdam"):
    return {"title": f"Data Engineer {n}", "locationsText": location, "externalPath": f"/job/{n}"}


def _fake_post(monkeypatch, pages):
    """Answers each POST with the next page in `pages` and records the request bodies."""
    calls = []

    class Response:
        def __init__(self, data):
            self.data = data

        def raise_for_status(self):
            pass

        def json(self):
            return self.data

    def post(url, json, **kwargs):
        assert url == API
        calls.append(json)
        return Response(pages[len(calls) - 1])

    monkeypatch.setattr(targets.requests, "post", post)
    return calls


def test_country_facet_is_found_by_name_not_parameter():
    facets = [
        {"facetParameter": "jobFamilyGroup", "values": [{"descriptor": "Engineering", "id": "eng"}]},
        {"facetParameter": "locationMainGroup", "values": [
            {"facetParameter": "a", "descriptor": "Country", "values": [
                {"descriptor": "Germany", "id": "de-id"},
                {"descriptor": "Netherlands", "id": "nl-id"},
            ]},
        ]},
    ]
    assert targets._workday_nl_facets(facets) == {"a": ["nl-id"]}


def test_locations_fallback_picks_dutch_offices():
    facets = [{"facetParameter": "locations", "values": [
        {"descriptor": "ACT (Amsterdam - Acanthus)", "id": "ams"},
        {"descriptor": "London", "id": "lon"},
        {"descriptor": "Eindhoven, Noord-Brabant", "id": "ehv"},
        {"descriptor": "Remote", "id": "remote"},
    ]}]
    assert targets._workday_nl_facets(facets) == {"locations": ["ams", "ehv"]}


def test_board_with_no_dutch_value_returns_nothing(monkeypatch):
    first = {"total": 40, "jobPostings": [_job(1, "Berlin")], "facets": [
        {"facetParameter": "Location_Country", "values": [{"descriptor": "Germany", "id": "de-id"}]},
    ]}
    calls = _fake_post(monkeypatch, [first])
    assert list(targets._workday(TOKEN)) == []
    assert len(calls) == 1


def test_filtered_paging_sends_facet_and_reads_total_once(monkeypatch):
    facets = [{"facetParameter": "Location_Country", "values": [
        {"descriptor": "Netherlands", "id": "nl-id"}, {"descriptor": "France", "id": "fr-id"}]}]
    calls = _fake_post(monkeypatch, [
        {"total": 900, "jobPostings": [_job(0, "Paris")], "facets": facets},
        {"total": 25, "jobPostings": [_job(n) for n in range(20)], "facets": facets},
        {"total": 0, "jobPostings": [_job(n) for n in range(20, 25)], "facets": facets},
    ])
    jobs = list(targets._workday(TOKEN))
    assert len(jobs) == 25
    assert jobs[0] == ("Data Engineer 0", "Amsterdam", TOKEN + "/job/0", "")
    assert len(calls) == 3
    assert calls[0]["appliedFacets"] == {}
    assert [c["offset"] for c in calls[1:]] == [0, 20]
    assert all(c["appliedFacets"] == {"Location_Country": ["nl-id"]} for c in calls[1:])


def test_no_location_facet_falls_back_to_full_download(monkeypatch):
    calls = _fake_post(monkeypatch, [
        {"total": 22, "jobPostings": [_job(n, "Paris") for n in range(20)], "facets": []},
        {"total": 0, "jobPostings": [_job(n, "Paris") for n in range(20, 22)]},
    ])
    jobs = list(targets._workday(TOKEN))
    assert len(jobs) == 22
    assert [(c["offset"], c["appliedFacets"]) for c in calls] == [(0, {}), (20, {})]


def test_multi_location_job_still_resolved(monkeypatch):
    facets = [{"facetParameter": "locationCountry", "values": [{"descriptor": "Netherlands", "id": "nl-id"}]}]
    _fake_post(monkeypatch, [
        {"total": 1, "jobPostings": [_job(1, "Berlin")], "facets": facets},
        {"total": 1, "jobPostings": [_job(1, "2 Locations"), {"title": "stub"}], "facets": facets},
    ])
    details = []

    class Detail:
        def raise_for_status(self):
            pass

        def json(self):
            return {"jobPostingInfo": {"location": "Amsterdam", "additionalLocations": ["Berlin"]}}

    def get(url, **kwargs):
        details.append(url)
        return Detail()

    monkeypatch.setattr(targets.requests, "get", get)
    jobs = list(targets._workday(TOKEN))
    assert jobs == [("Data Engineer 1", "Amsterdam; Berlin", TOKEN + "/job/1", "")]
    assert details == ["https://acme.wd3.myworkdayjobs.com/wday/cxs/acme/External/job/1"]
