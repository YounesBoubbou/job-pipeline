"""SAP SuccessFactors reader: the careers site's sitemap, then one request per job page
(C3, ADR-0017). No network: requests.get is replaced with a fake."""

from scrapers import targets

SITE = "https://careers.bank.example"
SITE2 = "https://careers.broken.example"


class Response:
    def __init__(self, text="", status_code=200, url=None):
        # url is the final address after redirects; the fake get fills in the asked one.
        self.text, self.status_code, self.url = text, status_code, url
        self.content = text.encode("utf-8")

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"{self.status_code} Server Error")


def _fake_get(monkeypatch, answer):
    """Answers each GET with answer(url) and records the url."""
    calls = []

    def get(url, params=None, headers=None, **kwargs):
        calls.append(url)
        response = answer(url)
        response.url = response.url or url
        return response

    monkeypatch.setattr(targets.requests, "get", get)
    return calls


def _sitemap(urls):
    # Addresses are escaped as the real sitemaps do (&amp;, &apos;); one non-job page too.
    locs = "".join(f"<url><loc>{u.replace('&', '&amp;').replace(chr(39), '&apos;')}</loc></url>"
                   for u in [f"{SITE}/content/About-Us/"] + urls)
    return Response('<?xml version="1.0" encoding="UTF-8"?>'
                    f'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{locs}</urlset>')


def _token(label, value):
    return (f'<div class="joblayouttoken displayDTM "><div class="inner"><div class="row"><div class="col-xs-12">'
            f'<span class="joblayouttoken-label" role="heading">{label} \n</span>'
            f'<span class="rtltextaligneligible">{value} \n</span></div></div></div></div>')


def _page(title="Data Engineer", address="", tokens="", description="<p>Python and SQL</p>"):
    title_html = f'<span itemprop="title" class="rtltextaligneligible">{title}\n</span>' if title else ""
    descr_html = ('<span itemprop="description">\n</span>'  # empty first part, as on Triodos
                  f'<span itemprop="description">{description}\n</span>') if description else ""
    return Response(f'<html><body><div class="jobDisplayShell" itemscope itemtype="http://schema.org/JobPosting">'
                    f'{address}{title_html}{tokens}{descr_html}</div></body></html>')


def _job_url(slug, n):
    return f"{SITE}/job/{slug}/{n}/"


def test_small_site_reads_every_job_page(monkeypatch):
    urls = [_job_url("Brussels-Financing-Specialist-1000", 1), _job_url("Madrid-FS-CD-Consultant-M", 2),
            _job_url("Procurement-%28Sourcing-&-Contract%29-Bank's", 3)]
    calls = _fake_get(monkeypatch, lambda url: _sitemap(urls) if url.endswith("sitemap.xml") else _page())

    jobs = list(targets._successfactors(SITE + "/"))

    assert calls == [f"{SITE}/sitemap.xml"] + urls  # entities unescaped, non-job page left out
    assert [url for _, _, url, _ in jobs] == urls


def test_big_site_reads_only_slugs_that_look_dutch(monkeypatch):
    dutch = [_job_url("Amsterdam-Data-Engineer", 1),                       # NL town
             _job_url("LA-Driebergen-Rijsenburg-Content-Marketer-NLD", 2),  # NLD
             _job_url("Venlo-Software-Engineer-5928-NM", 3),               # Dutch postcode
             _job_url("Remote-Netherlands-Analyst", 4)]                     # Netherlands
    foreign = [_job_url(f"Bangalore-Developer-{n}", 100 + n) for n in range(150)]
    calls = _fake_get(monkeypatch, lambda url: _sitemap(foreign[:75] + dutch + foreign[75:])
                      if url.endswith("sitemap.xml") else _page())

    jobs = list(targets._successfactors(SITE))

    assert calls[1:] == dutch
    assert [url for _, _, url, _ in jobs] == dutch


def test_site_of_exactly_150_jobs_counts_as_small(monkeypatch):
    urls = [_job_url(f"Bangalore-Developer-{n}", n) for n in range(150)]
    calls = _fake_get(monkeypatch, lambda url: _sitemap(urls) if url.endswith("sitemap.xml") else _page())

    assert len(list(targets._successfactors(SITE))) == 150
    assert len(calls) == 151


def _one_page(monkeypatch, page, slug="Some-Job-Title-1000"):
    url = _job_url(slug, 1)
    _fake_get(monkeypatch, lambda u: _sitemap([url]) if u.endswith("sitemap.xml") else page)
    [job] = targets._successfactors(SITE)
    return job


def test_location_from_address_fields(monkeypatch):
    # msg / Under Armour: separate <meta> fields; Volvo / TU Delft: one streetAddress.
    address = ('<span itemprop="jobLocation" itemscope><span itemprop="address" itemscope>'
               '<meta itemprop="addressLocality" content="Ban Pathumwan"><meta itemprop="addressRegion" content="Path">'
               '<meta itemprop="postalCode" content="10330"><meta itemprop="addressCountry" content="TH"></span></span>')
    _, location, _, _ = _one_page(monkeypatch, _page(address=address, tokens=_token("Location:", "Bangkok")))
    assert location == "Ban Pathumwan, Path, 10330, TH"

    street = '<span itemprop="address" itemscope><meta itemprop="streetAddress" content="Delft, NL, 2628 CD"></span>'
    _, location, _, _ = _one_page(monkeypatch, _page(address=street))
    assert location == "Delft, NL, 2628 CD"


def test_location_from_labelled_token_with_country(monkeypatch):
    tokens = (_token("Job Title:", "Data Engineer") + _token("Job Location:", "Germany - Frankfurt PayOne")
              + _token("Country:", "Germany") + _token("Location:", "ignored, only the first one counts"))
    _, location, _, _ = _one_page(monkeypatch, _page(tokens=tokens))
    assert location == "Germany - Frankfurt PayOne, Germany"


def test_location_from_slug_when_page_names_none(monkeypatch):
    _, location, _, _ = _one_page(monkeypatch, _page(), slug="Rotterdam-Product-Owner-Data-Platforms-ZH-3072-AP")
    assert location == "Rotterdam Product Owner Data Platforms ZH 3072 AP"


def test_nld_gets_netherlands_appended(monkeypatch):
    _, location, _, _ = _one_page(
        monkeypatch, _page(tokens=_token("Job Location (Short):", "LA Driebergen-Rijsenburg, NLD")))
    assert location == "LA Driebergen-Rijsenburg, NLD, Netherlands"

    # A location that already names an NL place is left as it is.
    _, location, _, _ = _one_page(monkeypatch, _page(tokens=_token("Location:", "Amsterdam, NLD")))
    assert location == "Amsterdam, NLD"

    # NLD only as part of a word doesn't count.
    _, location, _, _ = _one_page(monkeypatch, _page(tokens=_token("Location:", "NLDX Campus, DE")))
    assert location == "NLDX Campus, DE"


def test_description_from_itemprop_skips_empty_parts(monkeypatch):
    _, _, _, description = _one_page(monkeypatch, _page(description="<p>Python and SQL</p>"))
    assert description == "<p>Python and SQL</p>"


def test_description_from_token(monkeypatch):
    # Seagate: no itemprop description, a "Job Description:" token instead.
    page = _page(description="", tokens=_token("Job Description:", "<p>Spark and Kafka</p>"))
    _, _, _, description = _one_page(monkeypatch, page)
    assert "<p>Spark and Kafka</p>" in description
    assert "Job Description" not in description


def test_description_empty_when_page_has_none(monkeypatch):
    _, _, _, description = _one_page(monkeypatch, _page(description=""))
    assert description == ""


def test_page_without_title_is_skipped(monkeypatch):
    urls = [_job_url("Amsterdam-Expired-Job", 1), _job_url("Amsterdam-Data-Engineer", 2)]
    pages = {urls[0]: _page(title=""), urls[1]: _page(title="Data Engineer")}
    _fake_get(monkeypatch, lambda url: _sitemap(urls) if url.endswith("sitemap.xml") else pages[url])

    assert [(t, url) for t, _, url, _ in targets._successfactors(SITE)] == [("Data Engineer", urls[1])]


def test_title_from_og_title_when_no_itemprop(monkeypatch):
    # NTT DATA / Seagate: no itemprop title; <title> carries a suffix, og:title doesn't.
    page = Response('<html><head><title>SAP Consultant Functiedetails | NTT DATA</title>'
                    '<meta property="og:title" content="SAP Consultant | BTP &amp; Integration Suite (CPI)" />'
                    '</head><body><span itemprop="description"><p>SAP BTP</p></span></body></html>')
    title, _, _, description = _one_page(monkeypatch, page)
    assert title == "SAP Consultant | BTP & Integration Suite (CPI)"
    assert description == "<p>SAP BTP</p>"


def test_page_redirected_off_job_address_is_skipped(monkeypatch):
    urls = [_job_url("Amsterdam-Expired-Job", 1), _job_url("Amsterdam-Data-Engineer", 2)]
    pages = {urls[0]: Response(_page().text, url=f"{SITE}/search/?expired=true"),
             urls[1]: Response(_page().text, url=f"{SITE}/job/Amsterdam-Data-Engineer/999-en_US/")}
    _fake_get(monkeypatch, lambda url: _sitemap(urls) if url.endswith("sitemap.xml") else pages[url])

    # The url kept is the sitemap address, not the redirect target.
    assert [url for _, _, url, _ in targets._successfactors(SITE)] == [urls[1]]


def test_description_from_job_display_block(monkeypatch):
    # Port of Rotterdam: no description itemprop or token; the text is only in .jobDisplay.
    page = Response('<html><body><div class="jobDisplayShell"><div class="jobDisplay">'
                    '<span itemprop="title">Product Owner Data Platforms</span>'
                    + _token("Uren per week:", "36") + '<div><p>Werk aan ons dataplatform</p></div>'
                    '<style>.buttontext a{border:1px solid}</style><script>var x = 1;</script>'
                    '</div></div></body></html>')
    _, _, _, description = _one_page(monkeypatch, page)
    assert "<p>Werk aan ons dataplatform</p>" in description
    assert "Product Owner Data Platforms" in description
    assert "buttontext" not in description and "var x" not in description


def test_failing_page_is_skipped(monkeypatch):
    urls = [_job_url("Amsterdam-Gone", 1), _job_url("Amsterdam-Data-Engineer", 2)]
    pages = {urls[0]: Response(status_code=404), urls[1]: _page()}
    _fake_get(monkeypatch, lambda url: _sitemap(urls) if url.endswith("sitemap.xml") else pages[url])

    assert [url for _, _, url, _ in targets._successfactors(SITE)] == [urls[1]]


def test_failing_sitemap_fails_the_board_and_others_continue(monkeypatch):
    monkeypatch.setattr(targets, "load_targets", lambda: [
        {"company": "Broken", "source": "successfactors", "token": SITE2, "board_status": "auto"},
        {"company": "Bank", "source": "successfactors", "token": SITE, "board_status": "auto"}])
    url = _job_url("LA-Driebergen-Rijsenburg-Junior-Data-Engineer-3972", 1)

    def answer(u):
        if u.startswith(SITE2):
            return Response(status_code=500)
        if u.endswith("sitemap.xml"):
            return _sitemap([url])
        return _page(title="Junior Data Engineer",
                     tokens=_token("Job Location (Short):", "LA Driebergen-Rijsenburg, NLD"))

    _fake_get(monkeypatch, answer)

    jobs, boards, failed = targets.fetch_target_jobs()

    assert [(f["name"], f["source"]) for f in failed] == [("Broken", "target:successfactors")]
    assert "500" in failed[0]["reason"]
    assert boards == [{"name": "Bank", "source": "target:successfactors", "fetched": 1, "kept": 1}]
    assert [(j["title"], j["location"], j["url"], j["source"]) for j in jobs] == [
        ("Junior Data Engineer", "LA Driebergen-Rijsenburg, NLD, Netherlands", url, "Target (successfactors)")]
    assert jobs[0]["description_snippet"] == "Python and SQL"
    assert "successfactors" not in targets.DESCRIPTION_FETCHERS
