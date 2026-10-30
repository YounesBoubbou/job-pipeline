from filters import names_nl_place, passes_language, passes_location, passes_exclude, strip_html


# ── passes_location ───────────────────────────

def test_location_accepts_nl_places():
    assert passes_location("Amsterdam, Netherlands")
    assert passes_location("Utrecht, NL")
    assert passes_location("Den Haag")


def test_location_rejects_countries_containing_nl():
    assert not passes_location("Helsinki, Finland")
    assert not passes_location("Nuuk, Greenland")


def test_location_accepts_other_nl_cities():
    assert passes_location("Veldhoven, Noord-Brabant")
    assert passes_location("The Hague")
    assert passes_location("'s-Hertogenbosch")
    assert passes_location("Eindhoven, nl")


def test_nl_place_ignores_work_modes():
    assert names_nl_place("Remote - Amsterdam")
    assert not names_nl_place("Remote")
    assert not names_nl_place("Hybrid")


def test_location_rejects_empty():
    assert not passes_location("")


# ── passes_exclude ────────────────────────────

def test_exclude_rejects_seniority():
    assert not passes_exclude("Senior Data Engineer")
    assert not passes_exclude("Data Engineering Team Lead")


def test_exclude_keeps_words_containing_lead():
    assert passes_exclude("Junior Data Engineer", "Join a leading fintech")
    assert passes_exclude("Junior Data Engineer", "No misleading dashboards here")


def test_exclude_rejects_short_seniority_in_title():
    assert not passes_exclude("Sr. Software Engineer")


def test_exclude_ignores_seniority_words_in_description():
    assert passes_exclude("Data Engineer", "You report to the engineering manager and work with senior staff")
    assert passes_exclude("Graduate Program", "You will lead a project")


def test_exclude_rejects_bare_year_requirements_in_description():
    assert not passes_exclude("Data Engineer", "Requirements: 5+ years in Python")


def test_exclude_rejects_year_requirements():
    assert not passes_exclude("Data Engineer", "You have 5+ years of experience")
    assert not passes_exclude("Data Engineer", "5-7 years of experience with Python")
    assert not passes_exclude("Data Engineer", "At least 6 years experience")


def test_exclude_keeps_junior_year_requirements():
    assert passes_exclude("Data Engineer", "1-2 years of experience")
    assert passes_exclude("Data Engineer", "3-5 years of experience")
    assert passes_exclude("Data Engineer", "We have been building software for 20 years")


def test_location_accepts_bare_work_mode():
    assert passes_location("Remote")
    assert passes_location("Remote job")
    assert passes_location("Hybrid - Amsterdam")


def test_location_rejects_remote_elsewhere():
    assert not passes_location("Remote - Indonesia; Remote - Malaysia")
    assert not passes_location("Remote, United States")


# ── strip_html ────────────────────────────────

def test_strip_html_handles_plain_escaped_and_cut_off_html():
    assert strip_html("<p>Hello <b>world</b></p>") == "Hello world"
    assert strip_html("&lt;p&gt;Fish &amp;amp; chips&lt;/p&gt;") == "Fish & chips"
    assert strip_html("Hello&nbsp;world <di") == "Hello world"
    assert strip_html("Plain text") == "Plain text"


# ── passes_language ───────────────────────────

def test_language_rejects_dutch_postings():
    assert not passes_language("Data Engineer", "Wij zoeken een collega voor het team van jouw dromen")
    assert not passes_language("Data Engineer", "&lt;p&gt;Als data engineer werk je aan de data van onze klanten&lt;/p&gt;")


def test_language_rejects_dutch_titles_without_description():
    assert not passes_language("Junior Software Ontwikkelaar")
    assert not passes_language("Data Engineer bij Coolblue")


def test_language_keeps_english_postings():
    assert passes_language("Data Engineer", "You will work with our team on the data platform")
    assert passes_language("Data Engineer", "Join Van der Berg and the team to work with your peers")


def test_language_keeps_postings_with_no_signal():
    assert passes_language("Data Engineer")
    assert passes_language("Junior Data Analyst", "Python, SQL, dbt")
