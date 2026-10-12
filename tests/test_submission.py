"""Synthetic evidence fixtures exercise validation; no measured model results."""

from copy import deepcopy

import pytest

from rarespeech.corpus import corpus_hash, load_cases
from rarespeech.datasets import dataset_path
from rarespeech.evaluate import evaluate
from rarespeech.submission import submission


def fixture(cases=None):
    cases = cases or load_cases(dataset_path("core"))
    samples, transcripts = [], []
    for c in cases:
        sid = c["id"] + "--r1"
        samples.append({"id": sid, "case_id": c["id"], "repeat": 1, "status": "ok", "audio_hash": "a" * 64})
        transcripts.append(
            {
                "id": sid,
                "text": c["text"],
                "audio_hash": "a" * 64,
                "engine": "synthetic-test-engine",
                "settings": {
                    "model_weights_sha256": "b" * 64,
                    "model_config_sha256": "c" * 64,
                    "beam_size": 5,
                    "vad_filter": False,
                },
            }
        )
    identity = {
        "corpus_hash": corpus_hash(cases),
        "repeats": 1,
        "model_label": "Synthetic-test-fixture",
        "adapter": {"revision": "weights-sha256:" + "d" * 64, "config_hash": "e" * 64},
    }
    return evaluate(cases, samples, transcripts, {"identity": identity})


def check(report, tmp_path, fragment):
    result = submission(report, tmp_path)
    assert not result["eligible_for_automatic_track_table"]
    assert any(fragment in blocker for blocker in result["blockers"]), result["blockers"]
    assert result["measurements"] == {}
    assert result["legacy_target_retention"] is None
    card = (tmp_path / "model-card.md").read_text(encoding="utf-8")
    assert "Not eligible for a track headline" in card
    assert "| Balanced target retention (ASR proxy) | 100.0% |" not in card
    return result


def test_full_canonical_evidence_eligible_with_explicit_candidate_scope(tmp_path):
    report = fixture()
    result = submission(report, tmp_path)
    assert result["eligible_for_automatic_track_table"]
    assert result["evaluator"]["measurement_hash"] == report["measurement_hash"]
    assert result["measurements"]["primary_target_retention"] == 1
    assert result["pronunciation_consensus"] is None
    assert any("not scientific endorsement" in note for note in result["notes"])
    assert any("not opened" in note for note in result["notes"])


@pytest.mark.parametrize("revision", ["weights-sha256:ACTUAL_SHA256", "sha256:abc", "YOUR_REVISION", "todo-revision"])
def test_unedited_identity_placeholders_cannot_receive_headline(tmp_path, revision):
    report = fixture()
    report["metadata"]["identity"]["adapter"]["revision"] = revision
    check(report, tmp_path, "revision")


@pytest.mark.parametrize(
    "revision",
    [
        None,
        "",
        "main",
        "model@main",
        "provider:latest",
        "replace-with-model-file-sha256",
        "record-the-downloaded-revision",
    ],
)
def test_example_placeholders_and_mutable_model_selectors_are_not_revisions(tmp_path, revision):
    report = fixture()
    report["metadata"]["identity"]["adapter"]["revision"] = revision
    check(report, tmp_path, "immutable model/weights revision")


def test_same_engine_mixed_decoding_settings_rejected(tmp_path):
    report = fixture()
    report["rows"][0]["transcript"]["settings"]["beam_size"] = 1
    check(report, tmp_path, "Mixed recognizer engines or decoding settings")


@pytest.mark.parametrize("settings", [None, [], {}, {"beam_size": 5}])
def test_asr_provenance_must_be_well_formed_and_fingerprinted(tmp_path, settings):
    report = fixture()
    for row in report["rows"]:
        row["transcript"]["settings"] = deepcopy(settings)
    check(report, tmp_path, "ASR model weights and config SHA-256")


def test_vocabulary_priming_disqualifies_primary_proxy(tmp_path):
    report = fixture()
    for row in report["rows"]:
        row["transcript"]["settings"]["hotwords"] = "rare vocabulary"
    check(report, tmp_path, "vocabulary prompts or hotwords")


def test_edited_metric_does_not_become_a_submission(tmp_path):
    report = fixture()
    report["rows"][0]["metrics"]["targets"][0]["retained"] = False
    check(report, tmp_path, "stored metrics are inconsistent")


def test_forged_headline_recomputed_instead_of_trusted(tmp_path):
    report = fixture()
    report["summary"]["automatic_accuracy"] = 0.123
    result = check(report, tmp_path, "historical retention score")
    assert result["observed_recomputed_measurements"]["primary_target_retention"] == 1


def test_forged_balanced_protocol_score_rejected(tmp_path):
    report = fixture()
    report["research_protocol"]["scores"]["primary_target_retention"] = 0.123
    check(report, tmp_path, "Stored balanced scores")


@pytest.mark.parametrize("location", ["generation", "report"])
def test_corpus_provenance_must_match_evaluated_cases(tmp_path, location):
    report = fixture()
    if location == "generation":
        report["metadata"]["identity"]["corpus_hash"] = "f" * 64
        check(report, tmp_path, "Generation corpus hash")
    else:
        report["corpus_hash"] = "f" * 64
        check(report, tmp_path, "Report corpus hash")


def test_subset_never_receives_canonical_score_card(tmp_path):
    report = fixture(load_cases(dataset_path("core"))[:2])
    check(report, tmp_path, "custom or a subset")


def test_missing_declared_repeats_block_even_if_summary_is_forged_complete(tmp_path):
    report = fixture()
    report["metadata"]["identity"]["repeats"] = 2
    check(report, tmp_path, "generation repeats are missing")


def test_same_case_repeat_cannot_be_counted_twice_under_new_sample_id(tmp_path):
    report = fixture()
    duplicate = deepcopy(report["rows"][0])
    duplicate["id"] += "--extra"
    duplicate["transcript"]["id"] = duplicate["id"]
    report["rows"].append(duplicate)
    check(report, tmp_path, "stored metrics are inconsistent")


@pytest.mark.parametrize("field,value", [("measurement_hash", "f" * 64), ("version", "0.0.0")])
def test_evaluator_source_and_version_are_bound(tmp_path, field, value):
    report = fixture()
    report[field] = value
    check(report, tmp_path, "Evaluator identity")


def test_forged_human_consensus_does_not_appear_in_submission(tmp_path):
    report = fixture()
    report["review_summary"]["verified_accuracy"] = 1
    result = check(report, tmp_path, "Human consensus summary")
    assert result["pronunciation_consensus"] is None


@pytest.mark.parametrize(
    "field,value", [("metadata", []), ("summary", None), ("research_protocol", []), ("rows", None)]
)
def test_malformed_imported_report_creates_actionable_rejection(tmp_path, field, value):
    report = fixture()
    report[field] = value
    check(report, tmp_path, "malformed")


def test_bad_schema_or_empty_corpus_fails_before_writing(tmp_path):
    with pytest.raises(ValueError, match="report.v1"):
        submission({}, tmp_path)
    with pytest.raises(ValueError, match="nonempty"):
        submission({"schema": "rarespeech.report.v1", "cases": []}, tmp_path)
    assert not (tmp_path / "submission.json").exists()
