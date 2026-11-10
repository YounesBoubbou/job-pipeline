"""Each source reports the boards it tried and the boards that failed (P1, P5).
No network: requests.get and the target fetchers are replaced with fakes."""

import requests

from scrapers import company_pages, indeed, targets


def _targets(*rows):
    return [{"company": name, "source": "greenhouse", "token": token, "board_status": status,
             "ind_registered_name": ""} for name, token, status in rows]


def _good_board():
    yield "Junior Data Engineer", "Amsterdam", "https://good/1", ""
    yield "Senior Data Engineer", "Amsterdam", "https://good/2", ""


def test_target_board_failure_is_reported_and_others_continue(monkeypatch):
    monkeypatch.setattr(targets, "load_targets", lambda: _targets(
        ("Good", "good", "auto"), ("Bad", "bad", "auto"), ("Rev", "rev", "review")))

    def fake(token):
        if token == "bad":
            raise requests.HTTPError("404 Client Error: Not Found")
        if token == "rev":
            raise AssertionError("review rows must not be fetched")
        return _good_board()
    monkeypatch.setitem(targets.FETCHERS, "greenhouse", fake)

    jobs, boards, failed = targets.fetch_target_jobs()

    assert boards == [{"name": "Good", "source": "target:greenhouse", "fetched": 2, "kept": 1}]
    assert [f["name"] for f in failed] == ["Bad"]
    assert failed[0]["source"] == "target:greenhouse"
    assert "404" in failed[0]["reason"]
    assert [j["title"] for j in jobs] == ["Junior Data Engineer"]


def test_target_error_while_filtering_marks_only_that_board_failed(monkeypatch):
    monkeypatch.setattr(targets, "load_targets", lambda: _targets(
        ("Good", "good", "auto"), ("Broken", "broken", "auto")))

    def fake(token):
        if token == "broken":
            def postings():
                yield "Junior Data Engineer", "Amsterdam", "https://broken/1", ""
                yield ("Junior ML Engineer",)  # malformed: fails while unpacking
            return postings()
        return _good_board()
    monkeypatch.setitem(targets.FETCHERS, "greenhouse", fake)

    jobs, boards, failed = targets.fetch_target_jobs()

    assert [b["name"] for b in boards] == ["Good"]
    assert [f["name"] for f in failed] == ["Broken"]
    assert all("broken" not in j["url"] for j in jobs)  # a failed board leaks no jobs


class _Response:
    def __init__(self, data=None, text=""):
        self._data, self.text = data, text

    def raise_for_status(self):
        pass

    def json(self):
        return self._data


def test_job_board_failure_is_reported(monkeypatch):
    def fake_get(url, **kwargs):
        if "remoteok" in url:
            return _Response([{"legal": "meta"},
                              {"position": "Junior Python Developer", "company": "X",
                               "location": "Remote", "url": "https://r/1", "description": ""}])
        raise requests.ConnectionError("network down")
    monkeypatch.setattr(indeed.requests, "get", fake_get)

    jobs, boards, failed = indeed.fetch_indeed_jobs()

    assert boards == [{"name": "RemoteOK", "source": "aggregator", "fetched": 1, "kept": 1}]
    assert [f["name"] for f in failed] == ["Arbeitnow"]
    assert "network down" in failed[0]["reason"]
    assert [j["url"] for j in jobs] == ["https://r/1"]


def test_company_page_failure_is_reported(monkeypatch):
    monkeypatch.setattr(company_pages, "GREENHOUSE_COMPANIES", {"Adyen": "adyen"})
    monkeypatch.setattr(company_pages, "COMPANY_PAGES",
                        [{"name": "SURF", "url": "https://werkenbij.example"}])

    def fake_get(url, **kwargs):
        if "greenhouse" in url:
            raise requests.Timeout("timed out")
        return _Response(text='<a href="/jobs/junior-data-engineer">Junior Data Engineer</a>'
                              '<a href="/jobs/senior-x">Senior X Lead</a>')
    monkeypatch.setattr(company_pages.requests, "get", fake_get)

    jobs, boards, failed = company_pages.fetch_company_jobs()

    assert [f["name"] for f in failed] == ["Adyen"]
    assert failed[0]["source"] == "careers:greenhouse"
    assert "Timeout" in failed[0]["reason"]
    assert boards == [{"name": "SURF", "source": "careers:html", "fetched": 2, "kept": 1}]
    assert [j["title"] for j in jobs] == ["Junior Data Engineer"]
