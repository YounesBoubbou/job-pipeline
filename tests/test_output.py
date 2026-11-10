import json

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
