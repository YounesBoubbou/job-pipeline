import ind_checker
from ind_checker import job_sponsor_status


def test_sponsor_status_prefers_registered_name(monkeypatch):
    monkeypatch.setattr(ind_checker, "_SPONSORS", {"jump trading europe"})
    job = {"company": "Jump Trading", "ind_registered_name": "Jump Trading Europe B.V."}
    assert job_sponsor_status(job) == "Yes"


def test_sponsor_status_falls_back_to_company(monkeypatch):
    monkeypatch.setattr(ind_checker, "_SPONSORS", {"adyen"})
    assert job_sponsor_status({"company": "Adyen N.V."}) == "Yes"
    assert job_sponsor_status({"company": "Huzzle", "ind_registered_name": ""}) == "No"


def test_sponsor_status_unknown_without_a_name(monkeypatch):
    monkeypatch.setattr(ind_checker, "_SPONSORS", {"adyen"})
    assert job_sponsor_status({"company": ""}) == "Unknown"
