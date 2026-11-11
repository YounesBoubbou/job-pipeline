"""coverage_scan.py: website guess, careers page, system detection, politeness, resume
(A2-A6, A9; ADR-0013). No network: requests.get, DNS and the clock are fakes."""

import csv

import pytest
import requests

import coverage_scan as cs
from scrapers.targets import HEADERS


class Response:
    def __init__(self, status, headers, body):
        self.status_code, self.headers = status, {"Content-Type": "text/html; charset=utf-8", **headers}
        self.encoding = "utf-8"
        self._body = body.encode("utf-8")

    def iter_content(self, size):
        for i in range(0, len(self._body), size):
            yield self._body[i:i + size]

    def close(self):
        pass


class Site:
    """A fake web: {url: (status, headers, body)}; a body that is an exception is raised.
    robots.txt not listed answers 404 (allow all); any other unlisted url answers 404."""

    def __init__(self, monkeypatch, pages, resolves=None, fail_on=None):
        self.pages, self.calls, self.now = pages, [], [1000.0]
        self.fail_on = fail_on
        hosts = {cs._host(u) for u in pages}
        self.resolves = set(resolves) if resolves is not None else hosts
        monkeypatch.setattr(cs.requests, "get", self.get)
        monkeypatch.setattr(cs.time, "monotonic", lambda: self.now[0])
        monkeypatch.setattr(cs.time, "sleep", self.sleep)
        monkeypatch.setattr(cs.socket, "getaddrinfo", self.dns)

    def sleep(self, seconds):
        self.now[0] += seconds

    def dns(self, host, port):
        if host not in self.resolves:
            raise OSError("no such host")
        return [("fake",)]

    def get(self, url, headers=None, **kwargs):
        assert not cs.is_vendor_url(url), f"job-system host requested: {url}"
        if self.fail_on and self.fail_on in url:
            raise KeyboardInterrupt
        self.calls.append((self.now[0], url, headers))
        status, hdrs, body = self.pages.get(url, (404, {}, ""))
        if isinstance(body, Exception):
            raise body
        return Response(status, hdrs, body)

    def urls(self):
        return [u for _, u, _ in self.calls]


@pytest.fixture(autouse=True)
def fresh_state():
    cs._robots.clear()
    cs._last_request.clear()
    cs._crawl_delay.clear()


def html(title="", body="", h1=""):
    return f"<html><head><title>{title}</title></head><body>{f'<h1>{h1}</h1>' if h1 else ''}{body}</body></html>"


def row(company, registered="", **extra):
    r = {"company": company, "ind_registered_name": registered, "other_ind_entities": "", "category": "",
         "already_applied": "", "source": "", "token": "", "board_status": "none"}
    r.update({c: "" for c in cs.NEW_COLUMNS})
    r.update(extra)
    return r


def ok(body):
    return (200, {}, body)


def redirect(to):
    return (301, {"Location": to}, "")


# 1. Website guess accepted only when the page names the company; DNS misses cost nothing.
def test_guess_accepts_a_page_naming_the_company_and_skips_unresolved(monkeypatch):
    site = Site(monkeypatch, {
        "https://flowtraders.nl/": ok(html("Flow Traders | Home")),
    })
    website, page, notes = cs.find_website(row("Flow Traders"), cs.Scan())
    assert website == "https://flowtraders.nl"
    assert not any("flowtraders.com" in u for u in site.urls())  # .com does not resolve: no request


def test_guess_rejects_a_page_of_another_company(monkeypatch):
    Site(monkeypatch, {"https://acme.com/": ok(html("Domain for sale")),
                       "https://acme.nl/": ok(html("Acme Tools", h1="Something else"))})
    website, page, notes = cs.find_website(row("Acme"), cs.Scan())
    assert website == "https://acme.nl"
    Site(monkeypatch, {"https://zork.com/": ok(html("Welcome to nginx!"))})
    cs._robots.clear()
    website, page, notes = cs.find_website(row("Zork"), cs.Scan())
    assert website == "" and notes[0].startswith("no website: tried zork.com (does not name")


def test_short_names_need_a_whole_word():
    soup = cs._soup(html("Symbolic tools"))
    assert not cs.names_company(["bol"], soup)
    assert cs.names_company(["bol"], cs._soup(html("bol. | de winkel van ons allemaal")))
    assert cs.names_company(["klippa"], cs._soup(html("Doxis (formerly Klippa)")))


# 2. Redirect to a parent site: accepted only if that page names the company.
def test_redirect_to_parent_needs_the_name(monkeypatch):
    Site(monkeypatch, {"https://brandx.com/": redirect("https://parentcorp.com/"),
                       "https://parentcorp.com/": ok(html("ParentCorp Group"))})
    website, _, notes = cs.find_website(row("BrandX"), cs.Scan())
    assert website == "" and "brandx.com redirects to parentcorp.com, which does not name the company" in notes[0]

    cs._robots.clear()
    Site(monkeypatch, {"https://brandy.com/": redirect("https://www.parentco.com/brands"),
                       "https://www.parentco.com/brands": ok(html("Brandy by ParentCo"))})
    website, _, notes = cs.find_website(row("Brandy"), cs.Scan())
    assert website == "https://www.parentco.com" and notes == ["redirected from brandy.com"]


# 3. A Dutch "Werken bij" link, then exactly one "alle vacatures" hop.
def test_werken_bij_link_and_one_see_all_hop(monkeypatch):
    site = Site(monkeypatch, {
        "https://www.dutchco.nl/": ok(html("DutchCo", '<a href="/over-ons">Over ons</a><a href="/werken-bij">Werken bij</a>')),
        "https://www.dutchco.nl/werken-bij": ok(html("Werken bij DutchCo", '<a href="/werken-bij/vacatures">Alle vacatures</a>')),
        "https://www.dutchco.nl/werken-bij/vacatures": ok(html("Vacatures", '<a href="/werken-bij/vacatures/lijst">Bekijk alle vacatures</a>')),
    })
    out = cs.scan_row(row("DutchCo", website="https://www.dutchco.nl"))
    assert "https://www.dutchco.nl/werken-bij/vacatures" in site.urls()
    assert "https://www.dutchco.nl/werken-bij/vacatures/lijst" not in site.urls()
    assert out["careers_url"] == "https://www.dutchco.nl/werken-bij"
    assert out["ats_seen"] == "needs_browser"


# 4. Fallback paths, and a soft 404 does not count.
def test_fallback_paths_and_soft_404(monkeypatch):
    site = Site(monkeypatch, {
        "https://plain.com/": ok(html("Plain", '<a href="/about">About</a>')),
        "https://plain.com/careers": (404, {}, html("Not found")),
        "https://plain.com/jobs": ok(html("Jobs at Plain", '<a href="https://plain.recruitee.com/">Apply</a>')),
    })
    out = cs.scan_row(row("Plain", website="https://plain.com"))
    assert out["careers_url"] == "https://plain.com/jobs"
    assert out["ats_seen"] == "recruitee" and out["ats_evidence"] == "https://plain.recruitee.com/"
    assert "https://plain.com/vacatures" not in site.urls()

    cs._robots.clear()
    Site(monkeypatch, {
        "https://soft.com/": ok(html("Soft")),
        "https://soft.com/careers": ok(html("Page not found | Soft", '<a href="/a">menu</a>')),
        "https://soft.com/jobs": ok(html("404")),
        "https://soft.com/vacatures": ok(html("Soft", h1="Pagina niet gevonden")),
        "https://soft.com/werken-bij": (404, {}, ""),
    })
    out = cs.scan_row(row("Soft", website="https://soft.com"))
    assert out["ats_seen"] == "no_careers_page" and out["careers_url"] == ""


# 5. Detection table, from addresses seen on real pages. (page url, html, kind, token)
DETECT = [
    ("https://x.com/c", '<a href="https://job-boards.eu.greenhouse.io/fourthline/jobs/123">x</a>', "greenhouse", "fourthline"),
    ("https://x.com/c", '<a href="https://effectory.recruitee.com/o/data-engineer">x</a>', "recruitee", "effectory"),
    ("https://jobs.funda.nl/", '<div data-props="{&quot;atsHost&quot;:&quot;recruitee.com&quot;,&quot;subdomain&quot;:&quot;funda&quot;}"></div>',
     "recruitee", "funda"),
    ("https://x.com/c", '<a href="https://jobs.lever.co/palantir/abc">x</a>', "lever", "palantir"),
    ("https://x.com/c", '<a href="https://jobs.eu.lever.co/tomtom/abc">x</a>', "lever_eu", "tomtom"),
    ("https://x.com/c", '<a href="https://jobs.ashbyhq.com/mollie/9f1c">x</a>', "ashby", "mollie"),
    ("https://x.com/c", '<a href="https://jobs.smartrecruiters.com/SanaCommerce/123-dev">x</a>', "smartrecruiters", "sanacommerce"),
    ("https://x.com/c", '<a href="https://redhat.wd5.myworkdayjobs.com/en-US/jobs/introduceYourself">x</a>', "workday",
     "https://redhat.wd5.myworkdayjobs.com/jobs"),
    ("https://x.com/c", '<a href="https://nxp.myworkdayjobs.com/careers">x</a>', "workday", "https://nxp.myworkdayjobs.com/careers"),
    ("https://x.com/c", '<a href="https://extremenetworks.wd503.myworkdayjobs.com/Extreme_Networks">x</a>', "workday",
     "https://extremenetworks.wd503.myworkdayjobs.com/Extreme_Networks"),
    ("https://careers.akzonobel.com/gb/en", '<script src="https://cdn.phenompeople.com/CareerConnectResources/x.js"></script>',
     "phenom", "https://careers.akzonobel.com/gb/en"),
    ("https://jobs.booking.com/booking/jobs", '<script src="https://assets.jibecdn.com/a.js"></script>'
     '<a href="https://careers-booking.icims.com/jobs/login">x</a>', "jibe", "https://jobs.booking.com"),
    ("https://careers.theheinekencompany.com/Netherlands", '<a href="https://career5.successfactors.eu/x">x</a>', "heineken",
     "https://careers.theheinekencompany.com"),
    ("https://x.com/c", '<a href="https://ohpen.jobs.personio.de/">x</a>', "Personio", ""),
    ("https://jobs.sendcloud.com/", '<link href="https://teamtailor-cdn.com/assets/a.css">', "Teamtailor",
     "https://teamtailor-cdn.com/assets/a.css"),
    ("https://careers.universiteitleiden.nl/", '<script src="https://performancemanager5.successfactors.eu/x.js"></script>',
     "SAP SuccessFactors", ""),
]


@pytest.mark.parametrize("page_url,body,kind,token", DETECT)
def test_detection_table(page_url, body, kind, token):
    hits = cs.detect(page_url, body)
    chosen, evidence, _ = cs._choose(hits)
    assert chosen == kind
    assert cs.token_from_evidence(chosen, evidence) == token


def test_bare_word_afas_is_not_evidence():
    assert cs.detect("https://leadinfo.com/", html("Leadinfo", "<p>Our customers: AFAS, Exact</p>")) == {}


def test_unconfirmed_pattern_and_also_are_noted():
    kind, _, notes = cs._choose(cs.detect("https://x.com/c", '<a href="https://apply.workable.com/x/">a</a>'
                                                            '<a href="https://jobs.lever.co/x">b</a>'))
    assert kind == "lever" and notes == ["also: Workable"]
    kind, _, notes = cs._choose(cs.detect("https://x.com/c", '<a href="https://apply.workable.com/x/">a</a>'))
    assert kind == "Workable" and "pattern unconfirmed" in notes


# 6. A careers link that redirects to a job system: evidence, never requested.
def test_redirect_to_lever_is_evidence_not_fetched(monkeypatch):
    site = Site(monkeypatch, {
        "https://redir.com/": ok(html("Redir", '<a href="/careers">Careers</a>')),
        "https://redir.com/careers": (302, {"Location": "https://jobs.lever.co/redir"}, ""),
    })
    out = cs.scan_row(row("Redir", website="https://redir.com"))
    assert out["ats_seen"] == "lever" and out["ats_evidence"] == "https://jobs.lever.co/redir"
    assert out["careers_url"] == "https://redir.com/careers"
    assert not any("lever.co" in u for u in site.urls())


def test_homepage_link_to_job_system_is_not_loaded(monkeypatch):
    site = Site(monkeypatch, {"https://small.nl/": ok(html("Small", '<a href="https://small.recruitee.com/">Vacatures</a>'))})
    out = cs.scan_row(row("Small", website="https://small.nl"))
    assert out["ats_seen"] == "recruitee" and out["careers_url"] == "https://small.recruitee.com/"
    assert site.urls() == ["https://small.nl/robots.txt", "https://small.nl/"]


# 7. custom, needs_browser, no_careers_page, and the JobPosting note (A5).
def _careers_site(monkeypatch, careers_body):
    return Site(monkeypatch, {
        "https://own.com/": ok(html("Own", '<a href="/careers">Careers</a>')),
        "https://own.com/careers": ok(html("Careers at Own", careers_body)),
    })


def test_custom_from_job_links(monkeypatch):
    _careers_site(monkeypatch, '<a href="/careers/data-engineer-123">a</a><a href="/careers/ml-engineer-456">b</a>')
    out = cs.scan_row(row("Own", website="https://own.com"))
    assert out["ats_seen"] == "custom" and "jobposting=no" in out["scan_note"]


def test_custom_from_jobposting_only(monkeypatch):
    _careers_site(monkeypatch, '<script type="application/ld+json">{"@graph": [{"@type": ["JobPosting"]}]}</script>'
                               '<script type="application/ld+json">{broken</script>')
    out = cs.scan_row(row("Own", website="https://own.com"))
    assert out["ats_seen"] == "custom" and "jobposting=yes" in out["scan_note"]


def test_needs_browser_for_an_empty_script_shell(monkeypatch):
    _careers_site(monkeypatch, '<div id="app"></div><script src="/main.js"></script>')
    out = cs.scan_row(row("Own", website="https://own.com"))
    assert out["ats_seen"] == "needs_browser" and "jobposting=no" in out["scan_note"]
    assert out["careers_url"] == "https://own.com/careers"


def test_no_openings_is_custom(monkeypatch):
    _careers_site(monkeypatch, "<p>Er zijn momenteel geen openstaande vacatures.</p>")
    out = cs.scan_row(row("Own", website="https://own.com"))
    assert out["ats_seen"] == "custom" and "says no openings" in out["scan_note"]


def test_no_careers_page(monkeypatch):
    Site(monkeypatch, {"https://none.com/": ok(html("None", '<a href="/contact">Contact</a>'))})
    out = cs.scan_row(row("None", website="https://none.com"))
    assert out["ats_seen"] == "no_careers_page" and out["scan_note"].endswith("requests=6")


# 8. blocked: robots refused or disallowing, 403, bot wall, no answer.
@pytest.mark.parametrize("pages,note", [
    ({"https://b.com/robots.txt": (403, {}, "")}, "robots.txt refused (HTTP 403)"),
    ({"https://b.com/robots.txt": ok("User-agent: *\nDisallow: /")}, "robots.txt disallows /"),
    ({"https://b.com/": (403, {}, "Forbidden")}, "homepage: HTTP 403"),
    ({"https://b.com/": ok(html("Just a moment...", "<p>Checking your browser</p>"))}, "homepage: bot wall (just a moment)"),
    ({"https://b.com/": (0, {}, requests.ReadTimeout("slow"))}, "no answer: ReadTimeout on b.com"),
])
def test_blocked(monkeypatch, pages, note):
    Site(monkeypatch, pages)
    out = cs.scan_row(row("B", website="https://b.com"))
    assert out["ats_seen"] == "blocked" and out["scan_note"].startswith(note)


def test_robots_fetched_with_our_user_agent(monkeypatch):
    """A site refusing Python's default User-Agent on robots.txt still lets the scan in."""
    site = Site(monkeypatch, {"https://ua.com/": ok(html("UA", '<a href="https://ua.recruitee.com/">Jobs</a>'))})
    real_get = site.get

    def picky(url, headers=None, **kw):
        if url.endswith("/robots.txt") and "Python-urllib" in (headers or {}).get("User-Agent", "Python-urllib"):
            return Response(403, {}, "")
        return real_get(url, headers=headers, **kw)

    monkeypatch.setattr(cs.requests, "get", picky)
    out = cs.scan_row(row("UA", website="https://ua.com"))
    assert out["ats_seen"] == "recruitee"


# 9. Politeness (A6 check): 6 requests per site, 1 s apart (or the crawl delay), our headers.
def test_never_more_than_six_requests_per_site(monkeypatch):
    links = "".join(f'<a href="/careers{i}">Careers</a>' for i in range(10))
    site = Site(monkeypatch, {"https://busy.com/": ok(html("Busy", links))})
    out = cs.scan_row(row("Busy", website="https://busy.com"))
    assert len(site.calls) == 6
    assert "request limit reached" in out["scan_note"]


def test_spacing_and_crawl_delay(monkeypatch):
    site = Site(monkeypatch, {"https://slow.com/": ok(html("Slow", '<a href="/careers">Careers</a>'))})
    cs.scan_row(row("Slow", website="https://slow.com"))
    times = [t for t, _, _ in site.calls]
    assert len(times) >= 3 and all(b - a >= 1.0 for a, b in zip(times, times[1:]))

    cs._robots.clear()
    cs._last_request.clear()
    site = Site(monkeypatch, {"https://delay.com/robots.txt": ok("User-agent: *\nCrawl-delay: 3\n"),
                              "https://delay.com/": ok(html("Delay", '<a href="/careers">Careers</a>'))})
    cs.scan_row(row("Delay", website="https://delay.com"))
    times = [t for t, _, _ in site.calls]
    assert len(times) >= 3 and all(b - a >= 3.0 for a, b in zip(times, times[1:]))
    assert all(h == HEADERS for _, _, h in site.calls)


def test_site_key():
    assert cs.site_key("jobs.funda.nl") == cs.site_key("www.funda.nl") == "funda.nl"
    assert cs.site_key("www.bbc.co.uk") == "bbc.co.uk"


# 10. Resume (A9 check) and 11. write-back.
def _write_csv(path, rows):
    cols = ["company", "ind_registered_name", "other_ind_entities", "category", "already_applied",
            "source", "token", "board_status"]
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, lineterminator="\n")
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in cols})


FOUR = [{"company": "Alpha", "source": "lever", "token": "alpha", "board_status": "hand"},
        {"company": "Beta", "board_status": "none"},
        {"company": "Gamma", "board_status": "none"},
        {"company": "Delta", "source": "ashby", "token": "delta", "board_status": "auto"}]


def _four_sites():
    return {f"https://{n}.com/": ok(html(n.title(), f'<a href="https://jobs.lever.co/{n}">Jobs</a>'))
            for n in ("alpha", "beta", "gamma", "delta")}


def test_resume_after_interruption(monkeypatch, tmp_path):
    path = str(tmp_path / "targets.csv")
    _write_csv(path, FOUR)
    Site(monkeypatch, _four_sites(), fail_on="gamma.com/")
    with pytest.raises(KeyboardInterrupt):
        cs.run(path=path)
    rows = cs.load_targets(path)
    assert [bool(r["scan_note"]) for r in rows] == [True, True, False, False]

    site = Site(monkeypatch, _four_sites())
    cs.run(path=path)
    assert {cs._host(u) for u in site.urls()} == {"gamma.com", "delta.com"}
    rows = cs.load_targets(path)
    assert all(r["ats_seen"] == "lever" for r in rows)
    assert [(r["source"], r["token"], r["board_status"]) for r in rows] == [
        ("lever", "alpha", "hand"), ("", "", "none"), ("", "", "none"), ("ashby", "delta", "auto")]


def test_write_back_keeps_the_file_format(monkeypatch, tmp_path):
    path = tmp_path / "targets.csv"
    _write_csv(path, FOUR)
    before = path.read_bytes()
    Site(monkeypatch, _four_sites())
    cs.run(path=str(path))
    after = path.read_bytes()
    assert not after.startswith(b"\xef\xbb\xbf") and b"\r" not in after
    header = after.split(b"\n")[0].decode()
    assert header.endswith(",website,careers_url,ats_seen,ats_evidence,scan_note")
    old_lines = before.decode().splitlines()
    new_lines = after.decode().splitlines()
    assert all(n.startswith(o + ",") for o, n in zip(old_lines, new_lines))  # old columns byte for byte

    cs.run(path=str(path))  # nothing left to scan: the file does not change
    assert path.read_bytes() == after


# 12. CLI selection.
def test_selection_modes():
    rows = [row("A", website="https://a.com"), row("B", website="https://b.com", ats_seen="custom", scan_note="x"),
            row("C", scan_note="no answer: ReadTimeout on c.com; requests=2", ats_seen="blocked"), row("D")]
    assert [r["company"] for r in cs.select_rows(rows)] == ["A", "D"]
    assert [r["company"] for r in cs.select_rows(rows, known_websites=True)] == ["A"]
    assert [r["company"] for r in cs.select_rows(rows, retry_no_answer=True)] == ["C"]
    assert [r["company"] for r in cs.select_rows(rows, companies=["B"])] == ["B"]
    assert [r["company"] for r in cs.select_rows(rows, limit=1)] == ["A"]


def test_known_website_is_not_guessed_and_company_rescans_a_done_row(monkeypatch, tmp_path):
    path = str(tmp_path / "targets.csv")
    _write_csv(path, [{"company": "Known"}])
    site = Site(monkeypatch, {"https://real-known.org/": ok(html("Known", '<a href="https://jobs.lever.co/known">Jobs</a>'))},
                resolves={"real-known.org", "known.com", "known.nl"})
    rows = cs.load_targets(path)
    fields = list(rows[0]) + cs.NEW_COLUMNS
    rows[0].update(website="https://real-known.org", scan_note="no website: tried known.com")
    cs.save_targets(rows, fields, path)
    cs.run(known_websites=True, path=path)
    assert {cs._host(u) for u in site.urls()} == {"real-known.org"}  # no guessing requests
    assert cs.load_targets(path)[0]["ats_seen"] == "lever"

    site.calls.clear()
    cs.run(companies=["Known"], path=path)
    assert site.urls()  # done, but rescanned when named


# 13. token_from_evidence for every kind.
@pytest.mark.parametrize("kind,evidence,token", [
    ("greenhouse", "https://boards.greenhouse.io/embed/job_board?for=bloomreach", "bloomreach"),
    ("greenhouse", "https://boards-api.greenhouse.io/v1/boards/adyen/jobs", "adyen"),
    ("greenhouse", "https://www.bol.com/vacatures?gh_jid=123", ""),
    ("recruitee", "https://effectory.recruitee.com/o/x", "effectory"),
    ("recruitee", 'https://jobs.funda.nl/ | "subdomain":"funda"', "funda"),
    ("lever", "https://api.lever.co/v0/postings/palantir?mode=json", "palantir"),
    ("lever_eu", "https://jobs.eu.lever.co/tomtom/123", "tomtom"),
    ("ashby", "https://jobs.ashbyhq.com/mollie/9f1c", "mollie"),
    ("ashby", "https://api.ashbyhq.com/posting-api/job-board/${org}", ""),
    ("smartrecruiters", "https://careers.smartrecruiters.com/SanaCommerce", "sanacommerce"),
    ("workday", "https://adobe.wd5.myworkdayjobs.com/en-US/external_experienced/job/x", "https://adobe.wd5.myworkdayjobs.com/external_experienced"),
    ("workday", "https://x.wd3.myworkdayjobs.com/wday/cxs/x/y/jobs", ""),
    ("phenom", "https://careers.akzonobel.com/gb/en | https://cdn.phenompeople.com/CareerConnectResources/a.js", "https://careers.akzonobel.com/gb/en"),
    ("phenom", "https://careers.adobe.com/ | https://cdn.phenompeople.com/CareerConnectResources/a.js", ""),
    ("jibe", "https://jobs.booking.com/booking/jobs | https://assets.jibecdn.com/a.js", "https://jobs.booking.com"),
    ("getnoticed", "https://www.werkenbijabnamro.nl/vacatures | logo Getnoticed", "https://www.werkenbijabnamro.nl"),
    ("eightfold", "https://portal.careers.hsbc.com/careers?domain=hsbc.com&pid=1", "https://portal.careers.hsbc.com/careers?domain=hsbc.com"),
    ("eightfold", "https://jobs.dsm-firmenich.com/careers?pid=123", ""),
    ("heineken", "https://careers.theheinekencompany.com/Netherlands", "https://careers.theheinekencompany.com"),
    ("Teamtailor", "https://jobs.sendcloud.com/ | x", "https://jobs.sendcloud.com/ | x"),
    ("Personio", "https://ohpen.jobs.personio.de/", ""),
])
def test_token_from_evidence(kind, evidence, token):
    assert cs.token_from_evidence(kind, evidence) == token


def test_getnoticed_needs_logo_and_vacancy_links():
    body = '<img alt="logo Getnoticed"><a href="/vacature/123/data-engineer/">x</a>'
    assert "getnoticed" in cs.detect("https://www.werkenbijx.nl/", body)
    assert cs.detect("https://www.werkenbijx.nl/", '<img alt="logo Getnoticed">') == {}


def test_a_bot_wall_on_the_careers_page_ends_the_search(monkeypatch):
    site = Site(monkeypatch, {
        "https://uni.nl/": ok(html("Uni", '<a href="/search">Vacancies</a><a href="/working-at">Working at Uni</a>')),
        "https://uni.nl/search": ok(html("Toegang geblokkeerd / Access Blocked")),
    })
    out = cs.scan_row(row("Uni", website="https://uni.nl"))
    assert out["ats_seen"] == "blocked" and out["scan_note"].startswith("careers page: bot wall (access blocked)")
    assert "https://uni.nl/working-at" not in site.urls()


def test_redirected_robots_is_read_once(monkeypatch):
    """sendcloud.com/robots.txt redirects to www.: that answer also serves www., saving a request."""
    site = Site(monkeypatch, {
        "https://shipco.com/robots.txt": (308, {"Location": "https://www.shipco.com/robots.txt"}, ""),
        "https://www.shipco.com/robots.txt": ok("User-agent: *\nAllow: /"),
        "https://shipco.com/": (308, {"Location": "https://www.shipco.com/"}, ""),
        "https://www.shipco.com/": ok(html("Shipco", '<a href="https://jobs.shipco.com/">Careers</a>')),
        "https://jobs.shipco.com/": ok(html("Jobs", '<link href="https://assets.teamtailor-cdn.com/a.css">')),
    })
    out = cs.scan_row(row("Shipco"))
    assert out["ats_seen"] == "Teamtailor" and out["careers_url"] == "https://jobs.shipco.com/"
    assert site.urls().count("https://www.shipco.com/robots.txt") == 1
    assert len(site.calls) == 6


# Review round 1: parked domains, reCAPTCHA, word-aligned names, robots edge cases, tokens.
@pytest.mark.parametrize("title", ["flowtraders.com is for sale!", "Flowtraders.com - Domain te koop",
                                   "This domain is parked", "Buy this domain: flowtraders.com"])
def test_parked_domain_is_rejected(monkeypatch, title):
    Site(monkeypatch, {"https://flowtraders.com/": ok(html(title))}, resolves={"flowtraders.com"})
    website, _, notes = cs.find_website(row("Flow Traders"), cs.Scan())
    assert website == "" and "flowtraders.com (a parked domain)" in notes[0]


def test_parked_domain_via_redirect_is_rejected(monkeypatch):
    Site(monkeypatch, {"https://bol.io/": redirect("https://www.hugedomains.com/domain_profile.cfm?d=bol.io"),
                       "https://www.hugedomains.com/domain_profile.cfm?d=bol.io": ok(html("Bol.io is for sale | HugeDomains"))},
         resolves={"bol.io", "www.hugedomains.com"})
    website, _, notes = cs.find_website(row("bol"), cs.Scan())
    assert website == "" and "bol.io (redirects to www.hugedomains.com, a parked domain)" in notes[0]


def test_the_page_own_address_does_not_name_the_company():
    soup = cs._soup(html("flowtraders.com"))
    assert cs.names_company(["flow traders"], soup, ("flowtraders.com",)) == ""
    assert cs.names_company(["flow traders"], cs._soup(html("Flow Traders")), ("flowtraders.com",)) == "flow traders"


def test_compact_name_must_align_with_words():
    assert not cs.names_company(["bird"], cs._soup(html("Thunderbird mail")))
    assert not cs.names_company(["mews"], cs._soup(html("Smews news")))
    assert cs.names_company(["flowtraders"], cs._soup(html("Flow Traders | Home")))


def test_short_name_is_noted(monkeypatch):
    Site(monkeypatch, {"https://mews.com/": ok(html("Mews | Hotel software"))}, resolves={"mews.com"})
    website, _, notes = cs.find_website(row("Mews"), cs.Scan())
    assert website == "https://mews.com" and notes == ["short name, check"]


def test_recaptcha_is_not_a_bot_wall():
    page = html("Contact us", '<script src="https://www.google.com/recaptcha/api.js"></script>'
                              '<div class="g-recaptcha"></div>')
    assert cs._wall(200, page) == ""
    assert cs._wall(200, html("Captcha check")) == "bot wall (captcha)"


def test_robots_429_is_blocked(monkeypatch):
    Site(monkeypatch, {"https://busy.com/robots.txt": (429, {}, "")})
    out = cs.scan_row(row("Busy", website="https://busy.com"))
    assert out["ats_seen"] == "blocked" and out["scan_note"].startswith("robots.txt unreachable (HTTP 429)")


def test_robots_redirect_to_a_job_system_is_not_followed(monkeypatch):
    site = Site(monkeypatch, {
        "https://jobs.vend.com/robots.txt": redirect("https://vend.recruitee.com/robots.txt"),
        "https://jobs.vend.com/": redirect("https://vend.recruitee.com/"),
    })
    out = cs.scan_row(row("Vend", website="https://jobs.vend.com"))
    assert out["ats_seen"] == "recruitee" and out["ats_evidence"] == "https://vend.recruitee.com/"
    assert not any("recruitee" in u for u in site.urls())


def test_cxsrecruit_host_is_never_requested():
    assert cs.is_vendor_url("https://werkenbij.cxsrecruit.nl/vacatures")


@pytest.mark.parametrize("kind,evidence,token", [
    ("workday", "https://acme.wd3.myworkdayjobs.com/en-US/", ""),
    ("workday", "https://acme.wd3.myworkdayjobs.com/en-US/Acme_Careers", "https://acme.wd3.myworkdayjobs.com/Acme_Careers"),
    ("greenhouse", "https://boards.greenhouse.io/embed/job_app?for=adyen&token=1", "adyen"),
    ("jibe", "https://www.jibeapply.com/ | https://www.jibeapply.com/", ""),
])
def test_token_edge_cases(kind, evidence, token):
    assert cs.token_from_evidence(kind, evidence) == token


# Review round 3: parked pages by sale wording only; an address that is the company's name.
@pytest.mark.parametrize("title,parked", [
    ("This domain is for sale", True),
    ("flowtraders.com - This website is for sale! - flowtraders Resources and Information.", True),
    ("bol.io - This website is for sale! - bol Resources and Information.", True),
    ("This domain name may be for sale!", True),
    ("Deze domeinnaam is te koop", True),
    ("Domein te koop", True),
    ("Buy this domain", True),
    ("acme.nl - parked", True),
    ("acme.com | HugeDomains", True),
    ("acme.com at Sedo", True),
    ("acme.com | Dan.com", True),
    ("acme.com - Afternic", True),
    ("SIDN | Wij zijn de beheerder van .nl", False),
    ("Hostnet | domeinnaam registreren", False),
    ("Funda | Huizen te koop en te huur", False),
    ("Garage sale tips", False),
])
def test_parked_wording(title, parked):
    assert cs.is_parked(cs._soup(html(title))) is parked


@pytest.mark.parametrize("company,host,title", [
    ("Booking.com", "booking.com", "Booking.com | Official site"),
    ("Smartly.io", "smartly.io", "Smartly.io | Ads automation"),
])
def test_address_in_company_name_is_not_stripped(company, host, title):
    names = cs.company_names(row(company))
    assert cs.names_company(names, cs._soup(html(title)), (host, "www." + host))
