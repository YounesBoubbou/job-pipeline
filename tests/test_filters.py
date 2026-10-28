from filters import passes_location, passes_exclude


# ── passes_location ───────────────────────────

def test_location_accepts_nl_places():
    assert passes_location("Amsterdam, Netherlands")
    assert passes_location("Utrecht, NL")
    assert passes_location("Den Haag")


def test_location_rejects_countries_containing_nl():
    assert not passes_location("Helsinki, Finland")
    assert not passes_location("Nuuk, Greenland")


def test_location_rejects_empty():
    assert not passes_location("")


# ── passes_exclude ────────────────────────────

def test_exclude_rejects_seniority():
    assert not passes_exclude("Senior Data Engineer")
    assert not passes_exclude("Data Engineering Team Lead")


def test_exclude_keeps_words_containing_lead():
    assert passes_exclude("Junior Data Engineer", "Join a leading fintech")
    assert passes_exclude("Junior Data Engineer", "No misleading dashboards here")


def test_exclude_rejects_year_requirements():
    assert not passes_exclude("Data Engineer", "You have 5+ years of experience")
    assert not passes_exclude("Data Engineer", "5-7 years of experience with Python")
    assert not passes_exclude("Data Engineer", "At least 6 years experience")


def test_exclude_keeps_junior_year_requirements():
    assert passes_exclude("Data Engineer", "1-2 years of experience")
    assert passes_exclude("Data Engineer", "3-5 years of experience")
    assert passes_exclude("Data Engineer", "We have been building software for 20 years")
