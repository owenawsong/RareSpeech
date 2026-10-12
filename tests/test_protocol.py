from copy import deepcopy

import pytest
from test_metrics import case

from rarespeech.evaluate import audit_asr, compare, evaluate, merge_reviews
from rarespeech.protocol import analyze_protocol, balanced_scores, paired_analysis


def corpus(families=3, variants=("isolated", "dense")):
    result = []
    for number in range(families):
        for variant in variants:
            c = case(f"Read term{number}.", f"term{number}")
            c.update(id=f"family{number}.{variant}", family_id=f"family{number}", variant=variant)
            result.append(c)
    return result


def make_report(cases, failed=(), repeats=1, engine="test", metadata=None):
    samples, transcripts = [], []
    for c in cases:
        for repeat in range(1, repeats + 1):
            sample = {
                "id": f"{c['id']}--r{repeat}",
                "case_id": c["id"],
                "repeat": repeat,
                "audio_hash": "a" * 64,
                "status": "ok",
            }
            samples.append(sample)
            transcripts.append(
                {
                    "id": sample["id"],
                    "audio_hash": sample["audio_hash"],
                    "engine": engine,
                    "text": "" if c["id"] in failed else c["text"],
                }
            )
    return evaluate(cases, samples, transcripts, metadata)


def test_balance_conditions_instead_of_counting_extra_occurrences():
    cases = corpus(1)
    dense = cases[1]
    dense["text"] = "term0 term0 term0"
    dense["targets"] = [{"id": f"t{i}", "text": "term0", "start": i * 6, "end": i * 6 + 5} for i in range(3)]
    report = make_report(cases, failed=[cases[0]["id"]])
    assert report["summary"]["automatic_accuracy"] == 0.75  # Historical occurrence score.
    assert report["research_protocol"]["scores"]["primary_target_retention"] == 0.5


def test_neighbor_failure_separate_from_primary_score():
    cases = corpus(1)
    dense = cases[1]
    dense["text"] += " neighbor"
    dense["targets"].append({"id": "neighbor", "text": "neighbor", "start": 12, "end": 20})
    report = make_report(cases)
    row = next(r for r in report["rows"] if r["variant"] == "dense")
    row["metrics"]["targets"][1]["retained"] = False
    score = balanced_scores(report["rows"], cases)["scores"]
    assert score == {"primary_target_retention": 1, "all_target_retention": 0.75}


def test_families_and_categories_have_equal_weight():
    cases = corpus(3, variants=("isolated",))
    cases[2]["category"] = "music"
    report = make_report(cases, failed=[cases[0]["id"]])
    assert report["research_protocol"]["scores"]["primary_target_retention"] == 0.75


def test_generation_repeat_count_does_not_change_family_weight():
    cases = corpus(2, variants=("isolated",))
    report = make_report(cases, failed=[cases[0]["id"]])
    rows = report["rows"] + [deepcopy(report["rows"][0]) for _ in range(20)]
    assert balanced_scores(rows, cases)["scores"]["primary_target_retention"] == 0.5


def test_missing_repeat_declared_by_run_withholds_headline():
    cases = corpus(1, variants=("isolated",))
    report = make_report(cases, metadata={"identity": {"repeats": 2}})
    assert not report["summary"]["complete"]
    assert report["summary"]["automatic_accuracy"] is None
    assert len(report["rows"]) == 2
    assert report["rows"][1]["status"] == "missing"
    assert report["research_protocol"]["scores"]["primary_target_retention"] is None


def test_missing_control_does_not_hide_noncontrol_protocol_score():
    cases = corpus(1, variants=("isolated", "control"))
    complete = make_report(cases)
    report = evaluate(cases, [complete["rows"][0]], [complete["rows"][0]["transcript"]])
    assert report["summary"]["automatic_accuracy"] is None
    assert report["research_protocol"]["scores"]["primary_target_retention"] == 1


def test_missing_primary_target_withholds_balanced_headline():
    cases = corpus(1)
    cases[1]["text"] = "Read neighbor."
    cases[1]["targets"] = [{"id": "t1", "text": "neighbor", "start": 5, "end": 13}]
    report = make_report(cases)
    assert report["research_protocol"]["scores"]["primary_target_retention"] is None
    assert report["research_protocol"]["coverage"]["scored_rows_without_primary"]


def test_paired_bootstrap_zero_delta_and_deterministic_positive_change():
    cases = corpus()
    baseline = make_report(cases)
    identical = compare(baseline, deepcopy(baseline))["paired_analysis"]
    assert identical["intervals_95_percentile"]["primary_target_retention"] == [0, 0]
    weak = make_report(cases, failed=[c["id"] for c in cases])
    strong = compare(weak, baseline)["paired_analysis"]
    assert strong["candidate_minus_baseline"]["primary_target_retention"] == 1
    assert strong["intervals_95_percentile"]["primary_target_retention"] == [1, 1]
    assert compare(weak, baseline)["paired_analysis"] == strong


def test_paired_missing_coverage_has_no_delta_or_interval():
    cases = corpus(2)
    left = make_report(cases)
    right = deepcopy(left)
    right["rows"][0]["metrics"] = None
    analysis = compare(left, right)["paired_analysis"]
    assert analysis["candidate_minus_baseline"]["primary_target_retention"] is None
    assert analysis["interval_unavailable_reason"] == "incomplete_noncontrol_coverage"


def test_mixed_asr_is_visible_but_not_a_headline():
    cases = corpus(2)
    report = make_report(cases)
    transcripts = [deepcopy(r["transcript"]) for r in report["rows"]]
    transcripts[0]["engine"] = "different"
    mixed = evaluate(cases, report["rows"], transcripts)
    assert mixed["summary"]["complete"]
    assert mixed["summary"]["automatic_accuracy"] is None
    assert not mixed["research_protocol"]["recognizer_consistent"]
    assert mixed["summary"]["interval_unavailable_reason"] == "mixed_recognizer_configurations"


def test_recognizer_decoding_settings_gate_comparison():
    cases = corpus(2)
    left = make_report(cases)
    right = deepcopy(left)
    right["rows"][0]["transcript"]["settings"] = {"beam_size": 1}
    with pytest.raises(ValueError, match="ASR"):
        compare(left, right)


def test_empty_corpus_and_invalid_repeat_design_rejected():
    with pytest.raises(ValueError, match="empty"):
        evaluate([], [], [])
    with pytest.raises(ValueError, match="declared repeats"):
        make_report(corpus(1), metadata={"identity": {"repeats": True}})


def test_rater_whitespace_and_case_do_not_create_independence():
    report = make_report(corpus(1, variants=("isolated",)))
    row = report["rows"][0]
    review = {
        "report_id": report["report_id"],
        "sample_id": row["id"],
        "target_id": "t1",
        "audio_hash": row["audio_hash"],
        "verdict": "pass",
        "rater": "Alice",
    }
    with pytest.raises(ValueError, match="duplicate"):
        merge_reviews(report, [review, {**review, "rater": " alice "}])


def test_asr_audit_denominator_and_evaluator_gate():
    report = make_report(corpus(1, variants=("isolated",)))
    identical = audit_asr(report, deepcopy(report))
    assert identical["coverage"]["paired_targets"] == 1
    assert identical["disagreement_rate"] == 0
    changed = deepcopy(report)
    changed["measurement_hash"] = "different"
    with pytest.raises(ValueError, match="evaluator"):
        audit_asr(report, changed)


def test_alias_primary_matching_uses_authored_text_not_recognizer_expansion():
    c = case("Time 3:30", "3:30", ["three thirty"])
    report = make_report([c])
    row = report["rows"][0]
    row["transcript"]["text"] = "Time three thirty"
    report = evaluate([c], [row], [row["transcript"]])
    assert analyze_protocol(report["rows"], [c])["scores"]["primary_target_retention"] == 1


def test_human_balanced_score_uses_consensus_not_asr_predictions():
    cases = corpus(1)
    dense = cases[1]
    dense["text"] = "term0 term0 term0"
    dense["targets"] = [{"id": f"t{i}", "text": "term0", "start": i * 6, "end": i * 6 + 5} for i in range(3)]
    report = make_report(cases)  # ASR says everything passes.
    reviews = []
    for row in report["rows"]:
        for target in row["case"]["targets"]:
            for rater in ("one", "two"):
                reviews.append(
                    {
                        "report_id": report["report_id"],
                        "sample_id": row["id"],
                        "audio_hash": row["audio_hash"],
                        "target_id": target["id"],
                        "rater": rater,
                        "verdict": "fail" if row["variant"] == "isolated" else "pass",
                    }
                )
    merge_reviews(report, reviews[:-1])
    assert report["review_summary"]["balanced_primary_target_accuracy"] is None
    merge_reviews(report, reviews[-1:])
    assert report["review_summary"]["verified_accuracy"] == 0.75
    assert report["review_summary"]["balanced_primary_target_accuracy"] == 0.5
    assert report["research_protocol"]["scores"]["primary_target_retention"] == 1


def test_direct_paired_api_checks_asr_and_sample_identity():
    cases = corpus(2)
    left, right = make_report(cases), make_report(cases, engine="different")
    with pytest.raises(ValueError, match="ASR"):
        paired_analysis(left, right)
    right = deepcopy(left)
    right["rows"][0]["case_id"] = "other"
    with pytest.raises(ValueError, match="sample-to-case"):
        paired_analysis(left, right)
