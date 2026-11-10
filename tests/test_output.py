import csv
import json

import pytest

import ind_checker
import output
from output import deduplicate


def _job(url, title="Junior Data Engineer", company="Catawiki"):
    return {"url": url, "title": title, "company": company}


def test_dedup_drops_seen_url():
    seen = {"https://a/1"}
    assert deduplicate([_job("https://a/1")], seen) == []


def test_dedup_drops_same_posting_under_different_url():
    jobs = [_job("https://a/1"), _job("https://b/2", company="Catawiki B.V.")]
    assert len(deduplicate(jobs, set())) == 1


def test_dedup_drops_posting_seen_in_earlier_run():
    seen = set()
    deduplicate([_job("https://a/1")], seen)
    assert deduplicate([_job("https://b/2")], seen) == []


def test_dedup_keeps_different_titles():
    jobs = [_job("https://a/1"), _job("https://a/2", title="Junior ML Engineer")]
    assert len(deduplicate(jobs, set())) == 2


def test_dedup_keeps_target_copy_labelled_yes_in_either_order(monkeypatch):
    # The Stream case: a board lists the job under its trade name, which is not on the
    # register; the target-list row carries the registered name, which is.
    monkeypatch.setattr(ind_checker, "_SPONSORS", {ind_checker.normalise_name("Stream.io B.V.")})
    board = {"url": "https://remoteok.com/1", "title": "Junior Backend Engineer",
             "company": "Stream", "source": "RemoteOK"}
    target = {"url": "https://boards.greenhouse.io/stream/1", "title": "Junior Backend Engineer",
              "company": "Stream", "ind_registered_name": "Stream.io B.V.",
              "source": "Target (greenhouse)"}

    for jobs in ([board, target], [target, board]):
        kept = deduplicate([dict(j) for j in jobs], set())
        assert len(kept) == 1
        assert kept[0]["source"] == "Target (greenhouse)"
        assert ind_checker.job_sponsor_status(kept[0]) == "Yes"


def test_write_run_summary_creates_dir_and_valid_json(tmp_path, monkeypatch):
    path = tmp_path / "sub" / "last_run.json"
    monkeypatch.setattr(output, "RUN_SUMMARY_PATH", str(path))
    summary = {"status": "completed", "jobs_added": 1,
               "failed": [{"name": "Valtech", "source": "target:greenhouse", "reason": "404 — not found"}]}

    output.write_run_summary(summary)

    with open(path, encoding="utf-8") as f:
        assert json.load(f) == summary
    assert list(path.parent.iterdir()) == [path]  # no .tmp file left behind


# ── P3: a second run adds nothing ─────────────────────────────────────────────

BOARD_JOB = {"url": "https://remoteok.com/1", "title": "Junior Data Engineer",
             "company": "Catawiki", "location": "Amsterdam", "source": "RemoteOK"}


@pytest.fixture
def two_runs(tmp_path, monkeypatch):
    """Runs the whole pipeline with fake sources but the real seen-cache, CSV and
    summary files, all under tmp_path. Set `feeds[n]` to what the sources return on run n."""
    import main
    feeds = {1: [], 2: []}
    run_no = {"n": 0}

    def fetch_jobs():
        run_no["n"] += 1
        return [dict(j) for j in feeds[run_no["n"]]], [], []

    monkeypatch.setattr(main, "fetch_indeed_jobs", fetch_jobs)
    monkeypatch.setattr(main, "fetch_company_jobs", lambda: ([], [], []))
    monkeypatch.setattr(main, "fetch_target_jobs", lambda: ([], [], []))
    monkeypatch.setattr(main, "job_sponsor_status", lambda j: "No")
    monkeypatch.setattr(output, "CSV_OUTPUT_PATH", str(tmp_path / "jobs.csv"))
    monkeypatch.setattr(output, "SEEN_CACHE_PATH", str(tmp_path / "seen_jobs.json"))
    monkeypatch.setattr(output, "RUN_SUMMARY_PATH", str(tmp_path / "last_run.json"))

    def run_twice():
        main.run()
        rows_after_1 = _csv_rows(tmp_path)
        main.run()
        return rows_after_1, _csv_rows(tmp_path), _jobs_added(tmp_path)

    return feeds, run_twice


def _csv_rows(tmp_path):
    with open(tmp_path / "jobs.csv", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _jobs_added(tmp_path):
    with open(tmp_path / "last_run.json", encoding="utf-8") as f:
        return json.load(f)["jobs_added"]


def test_second_run_with_same_jobs_adds_zero_rows(two_runs):
    # The P3 check: running the pipeline twice in a row adds zero rows the second time
    feeds, run_twice = two_runs
    other = dict(BOARD_JOB, url="https://remoteok.com/2", title="Junior ML Engineer")
    feeds[1] = feeds[2] = [BOARD_JOB, other]

    after_1, after_2, added_2 = run_twice()

    assert len(after_1) == 2
    assert after_2 == after_1
    assert added_2 == 0


def test_second_run_same_posting_from_another_source_adds_nothing(two_runs):
    # Same company and title, new link and new source (here the target list, with the
    # company written as its registered name): still the job seen yesterday
    feeds, run_twice = two_runs
    feeds[1] = [BOARD_JOB]
    feeds[2] = [{"url": "https://boards.greenhouse.io/catawiki/9", "title": "Junior  data engineer",
                 "company": "Catawiki B.V.", "location": "Amsterdam",
                 "source": "Target (greenhouse)"}]

    after_1, after_2, added_2 = run_twice()

    assert len(after_1) == 1
    assert after_2 == after_1
    assert added_2 == 0


def test_second_run_still_adds_a_genuinely_new_job(two_runs):
    # Guards the tests above: run 2 is not blocked wholesale
    feeds, run_twice = two_runs
    new = dict(BOARD_JOB, url="https://remoteok.com/3", title="Junior Analytics Engineer")
    feeds[1] = [BOARD_JOB]
    feeds[2] = [BOARD_JOB, new]

    after_1, after_2, added_2 = run_twice()

    assert len(after_1) == 1
    assert [r["title"] for r in after_2] == ["Junior Data Engineer", "Junior Analytics Engineer"]
    assert added_2 == 1
