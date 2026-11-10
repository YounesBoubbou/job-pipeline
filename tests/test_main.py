import sys

import main
import output


class _NoSheets:
    """Stands in for gspread and the Google auth library and records any use.
    Recorded rather than raised, because a Sheets writer may swallow errors."""
    def __init__(self, touched):
        self._touched = touched

    def __getattr__(self, name):
        self._touched.append(name)
        raise AttributeError(name)


def test_run_makes_no_google_sheets_request(tmp_path, monkeypatch):
    job = {"url": "https://a/1", "title": "Junior Data Engineer", "company": "Catawiki",
           "location": "Amsterdam", "source": "test"}
    monkeypatch.setattr(main, "fetch_indeed_jobs", lambda: [])
    monkeypatch.setattr(main, "fetch_company_jobs", lambda: [])
    monkeypatch.setattr(main, "fetch_target_jobs", lambda: [job])
    monkeypatch.setattr(main, "job_sponsor_status", lambda j: "Yes")
    monkeypatch.setattr(main, "load_seen", lambda: set())
    monkeypatch.setattr(main, "save_seen", lambda seen: None)
    csv_path = tmp_path / "jobs.csv"
    monkeypatch.setattr(output, "CSV_OUTPUT_PATH", str(csv_path))
    touched = []
    for mod in ("gspread", "google.oauth2", "google.oauth2.service_account"):
        monkeypatch.setitem(sys.modules, mod, _NoSheets(touched))

    main.run()

    assert touched == []

    # The job still lands in the CSV, the only place jobs live
    assert "Junior Data Engineer" in csv_path.read_text(encoding="utf-8")


def test_pipeline_has_no_sheet_writer():
    assert not hasattr(output, "write_sheets")
    assert not hasattr(main, "write_sheets")
