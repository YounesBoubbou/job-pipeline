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
