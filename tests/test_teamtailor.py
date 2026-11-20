"""Teamtailor reader: each careers site's /jobs.rss feed (C3, ADR-0015).
No network: requests.get is replaced with a fake."""

from scrapers import targets

TT = "https://jobs.parcels.example"
TT2 = "https://other.teamtailor.example"


class Response:
    def __init__(self, content=b"", status_code=200):
        self.content, self.status_code = content, status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"{self.status_code} Server Error")


def _fake_get(monkeypatch, answer):
    """Answers each GET with answer(url) and records the url."""
    calls = []

    def get(url, params=None, headers=None, **kwargs):
        calls.append(url)
        return answer(url)

    monkeypatch.setattr(targets.requests, "get", get)
    return calls


def _location(city, country):
    return (f"<tt:location><tt:name>{city} office</tt:name><tt:address>Street 1</tt:address>"
            f"<tt:zip>1234 AB</tt:zip><tt:city>{city}</tt:city><tt:country>{country}</tt:country>"
            f"</tt:location>")


def _item(title, slug, locations=(), remote="hybrid", description="&lt;p&gt;About the job&lt;/p&gt;"):
    offices = "".join(_location(c, n) for c, n in locations)
    return (f"<item><title>{title}</title><description>{description}</description>"
            f"<pubDate>Mon, 16 Nov 2026 09:00:00 +0100</pubDate><link>{TT}/jobs/{slug}</link>"
            f"<remoteStatus>{remote}</remoteStatus><guid>{slug}</guid>"
            f"<tt:locations>{offices}</tt:locations>"
            f"<tt:department>Engineering</tt:department><tt:role>Engineer</tt:role></item>")


def _feed(*items):
    return (f'<?xml version="1.0" encoding="UTF-8"?>'
            f'<rss version="2.0" xmlns:tt="https://teamtailor.com/locations"><channel>'
            f"<title>Careers</title><link>{TT}</link>{''.join(items)}</channel></rss>").encode()


def test_teamtailor_reads_listing_from_rss(monkeypatch):
    feed = _feed(_item("Data Engineer", "1-data-engineer", [("Eindhoven", "Netherlands")]),
                 _item("Account Executive", "2-account-executive",
                       [("Eindhoven", "Netherlands"), ("Barcelona", "Spain")]))
    calls = _fake_get(monkeypatch, lambda url: Response(feed))

    jobs = list(targets._teamtailor(TT))

    assert jobs == [
        ("Data Engineer", "Eindhoven, Netherlands", f"{TT}/jobs/1-data-engineer", "<p>About the job</p>"),
        ("Account Executive", "Eindhoven, Netherlands; Barcelona, Spain",
         f"{TT}/jobs/2-account-executive", "<p>About the job</p>")]
    assert calls == [f"{TT}/jobs.rss"]

    list(targets.FETCHERS["teamtailor"](TT + "/"))
    assert calls[-1] == f"{TT}/jobs.rss"


def test_teamtailor_description_html_comes_through(monkeypatch):
    html = "&lt;h2&gt;What you do&lt;/h2&gt;&lt;ul&gt;&lt;li&gt;Python &amp;amp; SQL&lt;/li&gt;&lt;/ul&gt;"
    _fake_get(monkeypatch, lambda url: Response(_feed(_item("Analyst", "3-analyst",
                                                              [("Amsterdam", "Netherlands")], description=html))))

    [(_, _, _, description)] = targets._teamtailor(TT)

    assert description == "<h2>What you do</h2><ul><li>Python &amp; SQL</li></ul>"
    assert "teamtailor" not in targets.DESCRIPTION_FETCHERS


def test_teamtailor_remote_and_missing_locations(monkeypatch):
    feed = _feed(_item("Remote Engineer", "4-remote", remote="fully"),
                 _item("Mystery Engineer", "5-mystery", remote="none"),
                 _item("City Only", "6-city", [("Utrecht", "")]))
    _fake_get(monkeypatch, lambda url: Response(feed))

    assert [(t, loc) for t, loc, _, _ in targets._teamtailor(TT)] == [
        ("Remote Engineer", "Remote"), ("Mystery Engineer", ""), ("City Only", "Utrecht")]


def test_teamtailor_empty_board_yields_nothing(monkeypatch):
    _fake_get(monkeypatch, lambda url: Response(_feed()))

    assert list(targets._teamtailor(TT)) == []


def test_teamtailor_failing_board_is_reported_and_others_continue(monkeypatch):
    monkeypatch.setattr(targets, "load_targets", lambda: [
        {"company": "Broken", "source": "teamtailor", "token": TT2, "board_status": "auto"},
        {"company": "Parcels", "source": "teamtailor", "token": TT, "board_status": "auto"}])
    feed = _feed(_item("Junior Data Engineer", "7-junior", [("Amsterdam", "Netherlands")]))
    _fake_get(monkeypatch, lambda url: Response(feed) if url.startswith(TT) else Response(status_code=500))

    jobs, boards, failed = targets.fetch_target_jobs()

    assert [(f["name"], f["source"]) for f in failed] == [("Broken", "target:teamtailor")]
    assert "500" in failed[0]["reason"]
    assert boards == [{"name": "Parcels", "source": "target:teamtailor", "fetched": 1, "kept": 1}]
    assert [(j["title"], j["location"], j["source"]) for j in jobs] == [
        ("Junior Data Engineer", "Amsterdam, Netherlands", "Target (teamtailor)")]
