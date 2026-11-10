import json

import pandas as pd
import pytest
from fastapi.testclient import TestClient

import api
import output

client = TestClient(api.app)

SUMMARY = {
    "started_at": "2026-11-10T08:00:03+01:00",
    "finished_at": "2026-11-10T08:12:41+01:00",
    "duration_seconds": 758,
    "status": "completed",
    "error": None,
    "jobs_added": 12,
    "boards": [{"name": "Adyen", "source": "target:greenhouse", "fetched": 140, "kept": 3}],
    "failed": [{"name": "Valtech", "source": "target:greenhouse", "reason": "HTTPError: 404"}],
}


@pytest.fixture
def summary_path(tmp_path, monkeypatch):
    path = tmp_path / "last_run.json"
    monkeypatch.setattr(api, "SUMMARY_PATH", str(path))
    return path


def test_last_run_returns_summary(summary_path):
    summary_path.write_text(json.dumps(SUMMARY), encoding="utf-8")
    res = client.get("/api/last-run")
    assert res.status_code == 200
    assert res.json() == {"found": True, "summary": SUMMARY}


def test_last_run_is_read_at_request_time(summary_path):
    summary_path.write_text(json.dumps(SUMMARY), encoding="utf-8")
    client.get("/api/last-run")
    newer = dict(SUMMARY, finished_at="2026-11-11T08:10:00+01:00")
    summary_path.write_text(json.dumps(newer), encoding="utf-8")
    assert client.get("/api/last-run").json()["summary"]["finished_at"] == "2026-11-11T08:10:00+01:00"


def test_last_run_missing_file(summary_path):
    res = client.get("/api/last-run")
    assert res.status_code == 200
    body = res.json()
    assert body["found"] is False
    assert "not run yet" in body["message"]


def test_last_run_crashed_run_is_passed_through(summary_path):
    crashed = dict(SUMMARY, status="crashed", error="RuntimeError: boom", jobs_added=0)
    summary_path.write_text(json.dumps(crashed), encoding="utf-8")
    body = client.get("/api/last-run").json()
    assert body["found"] is True
    assert body["summary"]["status"] == "crashed"
    assert body["summary"]["error"] == "RuntimeError: boom"


@pytest.mark.parametrize("content", ['{"started_at": "2026-11-10T08:00', "", "[1, 2]"])
def test_last_run_unreadable_file(summary_path, content):
    summary_path.write_text(content, encoding="utf-8")
    res = client.get("/api/last-run")
    assert res.status_code == 200
    body = res.json()
    assert body["found"] is False
    assert "could not be read" in body["message"]


# ── W3: jobs added by the last run are marked new ─────────────────────────────

@pytest.fixture
def csv_path(tmp_path, monkeypatch):
    path = tmp_path / "jobs.csv"
    monkeypatch.setattr(api, "CSV_PATH", str(path))
    return path


def make_jobs(prefix, n, date_found="2026-11-10"):
    return [
        {"title": f"{prefix} job {i}", "company": "Acme", "url": f"https://example.com/{prefix}/{i}",
         "date_found": date_found}
        for i in range(n)
    ]


def write_jobs_csv(path, jobs):
    pd.DataFrame(jobs).to_csv(path, index=False)


def write_summary(path, **fields):
    path.write_text(json.dumps(dict(SUMMARY, **fields)), encoding="utf-8")


def new_urls(res):
    return [job["url"] for job in res.json() if job["is_new"] is True]


def test_jobs_marks_last_run_rows_new(csv_path, summary_path):
    jobs = make_jobs("a", 5)
    write_jobs_csv(csv_path, jobs)
    write_summary(summary_path, jobs_added=2)
    res = client.get("/api/jobs")
    assert res.status_code == 200
    assert [job["is_new"] for job in res.json()] == [False, False, False, True, True]
    assert new_urls(res) == [j["url"] for j in jobs[3:]]


def test_jobs_two_runs_same_day_marks_only_latest(csv_path, summary_path, monkeypatch):
    # Both runs write through the pipeline's own CSV writer, on the same date.
    monkeypatch.setattr(output, "CSV_OUTPUT_PATH", str(csv_path))
    first, second = make_jobs("first", 3), make_jobs("second", 2)
    output.write_csv(first)
    output.write_csv(second)
    write_summary(summary_path, jobs_added=len(second))
    res = client.get("/api/jobs")
    assert len(res.json()) == 5
    assert new_urls(res) == [j["url"] for j in second]


def test_jobs_last_run_added_none(csv_path, summary_path):
    write_jobs_csv(csv_path, make_jobs("a", 3))
    write_summary(summary_path, jobs_added=0)
    assert new_urls(client.get("/api/jobs")) == []


def test_jobs_no_summary_file(csv_path, summary_path):
    write_jobs_csv(csv_path, make_jobs("a", 3))
    res = client.get("/api/jobs")
    assert res.status_code == 200
    assert [job["is_new"] for job in res.json()] == [False, False, False]


@pytest.mark.parametrize("content", [
    '{"jobs_added": 2',                      # invalid JSON
    "[1, 2]",                                # not an object
    json.dumps({"status": "completed"}),     # jobs_added missing
    json.dumps({"jobs_added": "abc"}),
    json.dumps({"jobs_added": "2"}),
    json.dumps({"jobs_added": -1}),
    json.dumps({"jobs_added": True}),
    json.dumps({"jobs_added": 1.5}),
])
def test_jobs_unreadable_summary(csv_path, summary_path, content):
    write_jobs_csv(csv_path, make_jobs("a", 3))
    summary_path.write_text(content, encoding="utf-8")
    res = client.get("/api/jobs")
    assert res.status_code == 200
    assert [job["is_new"] for job in res.json()] == [False, False, False]


def test_jobs_crashed_run_with_added_jobs(csv_path, summary_path):
    jobs = make_jobs("a", 4)
    write_jobs_csv(csv_path, jobs)
    write_summary(summary_path, status="crashed", error="RuntimeError: boom", jobs_added=2)
    assert new_urls(client.get("/api/jobs")) == [j["url"] for j in jobs[2:]]


def test_jobs_added_exceeds_rows(csv_path, summary_path):
    write_jobs_csv(csv_path, make_jobs("a", 3))
    write_summary(summary_path, jobs_added=10)
    assert new_urls(client.get("/api/jobs")) == []


def test_jobs_keeps_list_shape(csv_path, summary_path):
    write_jobs_csv(csv_path, make_jobs("a", 3))
    write_summary(summary_path, jobs_added=1)
    body = client.get("/api/jobs").json()
    assert isinstance(body, list)
    assert len(body) == 3
    assert body[0]["title"] == "a job 0"
