import json

import pytest
from fastapi.testclient import TestClient

import api

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
