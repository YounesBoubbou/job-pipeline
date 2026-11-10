import json
import sys
from datetime import datetime

import pytest

import main
import output

JOB = {"url": "https://a/1", "title": "Junior Data Engineer", "company": "Catawiki",
       "location": "Amsterdam", "source": "test"}


class _NoSheets:
    """Stands in for gspread and the Google auth library and records any use.
    Recorded rather than raised, because a Sheets writer may swallow errors."""
    def __init__(self, touched):
        self._touched = touched

    def __getattr__(self, name):
        self._touched.append(name)
        raise AttributeError(name)


@pytest.fixture
def run_env(tmp_path, monkeypatch):
    """No network, no real data/ folder: sources return nothing unless a test says so,
    and the CSV and run summary go to tmp_path."""
    monkeypatch.setattr(main, "fetch_indeed_jobs", lambda: ([], [], []))
    monkeypatch.setattr(main, "fetch_company_jobs", lambda: ([], [], []))
    monkeypatch.setattr(main, "fetch_target_jobs", lambda: ([dict(JOB)], [], []))
    monkeypatch.setattr(main, "job_sponsor_status", lambda j: "Yes")
    monkeypatch.setattr(main, "load_seen", lambda: set())
    monkeypatch.setattr(main, "save_seen", lambda seen: None)
    monkeypatch.setattr(output, "CSV_OUTPUT_PATH", str(tmp_path / "jobs.csv"))
    monkeypatch.setattr(output, "RUN_SUMMARY_PATH", str(tmp_path / "last_run.json"))
    return tmp_path


def _summary(tmp_path):
    with open(tmp_path / "last_run.json", encoding="utf-8") as f:
        return json.load(f)


def test_run_makes_no_google_sheets_request(run_env, monkeypatch):
    touched = []
    for mod in ("gspread", "google.oauth2", "google.oauth2.service_account"):
        monkeypatch.setitem(sys.modules, mod, _NoSheets(touched))

    main.run()

    assert touched == []

    # The job still lands in the CSV, the only place jobs live
    assert "Junior Data Engineer" in (run_env / "jobs.csv").read_text(encoding="utf-8")


def test_pipeline_has_no_sheet_writer():
    assert not hasattr(output, "write_sheets")
    assert not hasattr(main, "write_sheets")


def test_failed_board_still_completes_and_is_in_summary(run_env, monkeypatch):
    # The P5 check: one board forced to fail, the run completes and the summary lists it
    good = {"name": "Good", "source": "target:greenhouse", "fetched": 5, "kept": 1}
    valtech = {"name": "Valtech", "source": "target:greenhouse",
               "reason": "HTTPError: 404 Client Error: Not Found"}
    monkeypatch.setattr(main, "fetch_target_jobs", lambda: ([dict(JOB)], [good], [valtech]))

    main.run()

    s = _summary(run_env)
    assert s["status"] == "completed"
    assert s["error"] is None
    assert s["jobs_added"] == 1
    assert s["boards"] == [good]
    assert s["failed"] == [valtech]
    started = datetime.fromisoformat(s["started_at"])
    finished = datetime.fromisoformat(s["finished_at"])
    assert started <= finished
    assert s["duration_seconds"] >= 0


def test_whole_source_crash_does_not_stop_run(run_env, monkeypatch):
    def boom():
        raise RuntimeError("boom")
    monkeypatch.setattr(main, "fetch_company_jobs", boom)

    main.run()

    assert "Junior Data Engineer" in (run_env / "jobs.csv").read_text(encoding="utf-8")
    s = _summary(run_env)
    assert s["status"] == "completed"
    assert [f["name"] for f in s["failed"]] == ["Company pages"]
    assert "boom" in s["failed"][0]["reason"]


def test_summary_written_when_run_crashes(run_env, monkeypatch):
    def disk_full(jobs):
        raise RuntimeError("disk full")
    monkeypatch.setattr(main, "write_csv", disk_full)

    with pytest.raises(RuntimeError):
        main.run()

    s = _summary(run_env)
    assert s["status"] == "crashed"
    assert "disk full" in s["error"]
    assert s["finished_at"]
    assert s["jobs_added"] == 0


def test_summary_written_when_nothing_new(run_env, monkeypatch):
    monkeypatch.setattr(main, "load_seen", lambda: {JOB["url"]})

    main.run()

    s = _summary(run_env)
    assert s["status"] == "completed"
    assert s["jobs_added"] == 0
