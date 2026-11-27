"""Oracle Recruiting reader: the careers site's recruitingCEJobRequisitions endpoint, and
one recruitingCEJobRequisitionDetails request per job for the description (C3, ADR-0016).
No network: requests.get is replaced with a fake."""

from scrapers import targets

HOST = "https://bank.fa.oraclecloud.example"
SITE = f"{HOST}/hcmUI/CandidateExperience/en/sites/CX_1001"
HOST2 = "https://broken.fa.oraclecloud.example"


class Response:
    def __init__(self, data=None, status_code=200):
        self.data, self.status_code = data, status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"{self.status_code} Server Error")

    def json(self):
        return self.data


def _fake_get(monkeypatch, answer):
    """Answers each GET with answer(url) and records the url."""
    calls = []

    def get(url, params=None, headers=None, **kwargs):
        calls.append(url)
        return answer(url)

    monkeypatch.setattr(targets.requests, "get", get)
    return calls


def _job(n, primary="Amsterdam, Noord-Holland, Netherlands", secondary=()):
    return {"Id": str(n), "Title": f"Data Engineer {n}", "PrimaryLocation": primary,
            "ShortDescriptionStr": None, "secondaryLocations": [{"Name": s} for s in secondary]}


def _listing(jobs, total):
    return Response({"items": [{"TotalJobsCount": total, "requisitionList": jobs}], "count": 1})


def _offset(url):
    return int(url.rsplit("offset=", 1)[1])


def test_oracle_reads_listing_over_two_pages(monkeypatch):
    pages = {0: [_job(n) for n in range(100)], 100: [_job(n) for n in range(100, 103)]}
    calls = _fake_get(monkeypatch, lambda url: _listing(pages[_offset(url)], 103))

    jobs = list(targets._oracle(SITE))

    assert len(jobs) == 103
    assert jobs[0] == ("Data Engineer 0", "Amsterdam, Noord-Holland, Netherlands", f"{SITE}/job/0", "")
    api = (f"{HOST}/hcmRestApi/resources/latest/recruitingCEJobRequisitions?onlyData=true"
           f"&expand=requisitionList.secondaryLocations"
           f"&finder=findReqs;siteNumber=CX_1001,location=Netherlands,limit=100,offset=")
    assert calls == [api + "0", api + "100"]


def test_oracle_token_with_extra_path_is_cleaned(monkeypatch):
    calls = _fake_get(monkeypatch, lambda url: _listing([_job(7)], 1))
    messy = f"{HOST}/hcmUI/CandidateExperience/nl/sites/CX_1001/job/23501?mode=location"

    [(_, _, url, _)] = targets.FETCHERS["oracle"](messy)

    assert url == f"{SITE}/job/7"
    assert "siteNumber=CX_1001," in calls[0]


def test_oracle_secondary_locations_joined(monkeypatch):
    _fake_get(monkeypatch, lambda url: _listing(
        [_job(1, "Warsaw, Poland", ["Brussels, Belgium", "Amsterdam, Netherlands"])], 1))

    [(_, location, _, _)] = targets._oracle(SITE)

    assert location == "Warsaw, Poland; Brussels, Belgium; Amsterdam, Netherlands"


def test_oracle_appends_netherlands_when_no_nl_place_named(monkeypatch):
    _fake_get(monkeypatch, lambda url: _listing(
        [_job(1, "Poland"), _job(2, None), _job(3, "UTRECHT, Netherlands")], 3))

    assert [loc for _, loc, _, _ in targets._oracle(SITE)] == [
        "Poland; Netherlands", "Netherlands", "UTRECHT, Netherlands"]


def test_oracle_description_joins_the_three_parts(monkeypatch):
    detail = {"items": [{"ExternalDescriptionStr": "<p>About</p>", "ExternalResponsibilitiesStr": None,
                         "ExternalQualificationsStr": "<ul><li>Python</li></ul>"}]}
    calls = _fake_get(monkeypatch, lambda url: Response(detail))

    description = targets.DESCRIPTION_FETCHERS["oracle"](SITE, f"{SITE}/job/23501")

    assert description == "<p>About</p> <ul><li>Python</li></ul>"
    assert calls == [f"{HOST}/hcmRestApi/resources/latest/recruitingCEJobRequisitionDetails"
                     f'?expand=all&onlyData=true&finder=ById;Id="23501",siteNumber=CX_1001']


def test_oracle_failing_description_returns_empty(monkeypatch):
    _fake_get(monkeypatch, lambda url: Response(status_code=500))
    assert targets._oracle_description(SITE, f"{SITE}/job/1") == ""

    _fake_get(monkeypatch, lambda url: Response({"items": []}))
    assert targets._oracle_description(SITE, f"{SITE}/job/1") == ""


def test_oracle_empty_board_yields_nothing(monkeypatch):
    calls = _fake_get(monkeypatch, lambda url: _listing([], 0))

    assert list(targets._oracle(SITE)) == []
    assert len(calls) == 1


def test_oracle_failing_board_is_reported_and_others_continue(monkeypatch):
    broken = f"{HOST2}/hcmUI/CandidateExperience/en/sites/CX_1"
    monkeypatch.setattr(targets, "load_targets", lambda: [
        {"company": "Broken", "source": "oracle", "token": broken, "board_status": "auto"},
        {"company": "Bank", "source": "oracle", "token": SITE, "board_status": "auto"}])
    detail = {"items": [{"ExternalDescriptionStr": "<p>Python and SQL</p>"}]}

    def answer(url):
        if url.startswith(HOST2):
            return Response(status_code=500)
        if "recruitingCEJobRequisitionDetails" in url:
            return Response(detail)
        return _listing([{"Id": "5", "Title": "Junior Data Engineer", "PrimaryLocation": "Amsterdam, Netherlands"}], 1)

    _fake_get(monkeypatch, answer)

    jobs, boards, failed = targets.fetch_target_jobs()

    assert [(f["name"], f["source"]) for f in failed] == [("Broken", "target:oracle")]
    assert "500" in failed[0]["reason"]
    assert boards == [{"name": "Bank", "source": "target:oracle", "fetched": 1, "kept": 1}]
    assert [(j["title"], j["location"], j["url"], j["source"]) for j in jobs] == [
        ("Junior Data Engineer", "Amsterdam, Netherlands", f"{SITE}/job/5", "Target (oracle)")]
    assert jobs[0]["description_snippet"] == "Python and SQL"
