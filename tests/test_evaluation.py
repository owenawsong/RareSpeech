from copy import deepcopy

import pytest
from test_metrics import case

from rarespeech.evaluate import compare, evaluate, merge_reviews


def fixtures():
    c = case()
    sample = {"id": "sample--r1", "case_id": "sample", "status": "ok", "audio_hash": "a" * 64}
    transcript = {"id": sample["id"], "text": c["text"], "audio_hash": sample["audio_hash"], "engine": "test"}
    return c, sample, transcript


def test_complete_and_missing_transcripts():
    c, s, t = fixtures()
    report = evaluate([c], [s], [t])
    assert report["summary"]["automatic_accuracy"] == 1
    incomplete = evaluate([c], [s], [])
    assert incomplete["summary"]["automatic_accuracy"] is None
    assert incomplete["summary"]["samples"] == 1


def test_empty_transcript_not_excluded():
    c, s, t = fixtures()
    t["text"] = ""
    report = evaluate([c], [s], [t])
    assert report["summary"]["complete"]
    assert report["summary"]["automatic_accuracy"] == 0


@pytest.mark.parametrize("field,value", [("audio_hash", "wrong"), ("id", "unknown")])
def test_transcript_provenance(field, value):
    c, s, t = fixtures()
    t[field] = value
    with pytest.raises(ValueError):
        evaluate([c], [s], [t])


def test_missing_generation_remains_visible():
    c, _, _ = fixtures()
    r = evaluate([c], [], [])
    assert r["rows"][0]["status"] == "missing"
    assert not r["summary"]["complete"]


def test_duplicate_transcript_rejected():
    c, s, t = fixtures()
    with pytest.raises(ValueError):
        evaluate([c], [s], [t, t])


def review(report, rater, verdict="pass"):
    return {
        "report_id": report["report_id"],
        "sample_id": "sample--r1",
        "target_id": "t1",
        "rater": rater,
        "verdict": verdict,
        "audio_hash": "a" * 64,
    }


def test_consensus_only_after_two_distinct_raters():
    c, s, t = fixtures()
    r = evaluate([c], [s], [t])
    merge_reviews(r, [review(r, "alice")])
    assert r["review_summary"]["verified_accuracy"] is None
    merge_reviews(r, [review(r, "bob")])
    assert r["review_summary"]["verified_accuracy"] == 1


def test_dispute_does_not_become_pass():
    c, s, t = fixtures()
    r = evaluate([c], [s], [t])
    merge_reviews(r, [review(r, "alice"), review(r, "bob", "fail")])
    assert r["review_summary"]["verified_accuracy"] is None
    assert r["review_summary"]["disputed"] == 1


def test_review_cannot_migrate_between_audio_or_reports():
    c, s, t = fixtures()
    r = evaluate([c], [s], [t])
    d = review(r, "alice")
    d["audio_hash"] = "b" * 64
    with pytest.raises(ValueError):
        merge_reviews(r, [d])


def test_duplicate_rater_not_independent_vote():
    c, s, t = fixtures()
    r = evaluate([c], [s], [t])
    with pytest.raises(ValueError):
        merge_reviews(r, [review(r, "alice"), review(r, "alice")])


def test_checkpoint_comparison_and_suite_mismatch():
    c, s, t = fixtures()
    a = evaluate([c], [s], [t])
    bad = deepcopy(t)
    bad["text"] = "the mineral is unknown"
    b = evaluate([c], [s], [bad])
    assert compare(a, b)["changes"][0]["status"] == "regressed"
    b["corpus_hash"] = "changed"
    with pytest.raises(ValueError):
        compare(a, b)
