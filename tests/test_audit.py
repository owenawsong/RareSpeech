from copy import deepcopy

import pytest
from test_protocol import corpus, make_report

from rarespeech.audit import audit_corpus, dependency_clusters
from rarespeech.metrics import bootstrap


def test_shared_neighbors_join_transitively_not_only_primary_family():
    cases = corpus(3, variants=("isolated",))
    for index, neighbor in ((0, "term1"), (1, "term2")):
        c = cases[index]
        c["text"] += " " + neighbor
        start = len(c["text"]) - len(neighbor)
        c["targets"].append({"id": "neighbor", "text": neighbor, "start": start, "end": len(c["text"])})
    design = dependency_clusters(cases)
    assert len(design["clusters"]) == 1
    assert design["clusters"][0]["families"] == ["family0", "family1", "family2"]
    assert not design["interval_eligible"]
    report = make_report(cases)
    assert report["summary"]["interval"] is None
    assert bootstrap(report["rows"], samples=50) is None


def test_declared_morphological_cluster_and_controls():
    cases = corpus(3, variants=("isolated", "control"))
    for c in cases:
        if c["family_id"] in ("family0", "family1"):
            c["cluster_id"] = "morphological-pair"
        if c["variant"] == "control":
            c["targets"][0]["text"] = "garden"
    design = dependency_clusters(cases)
    assert len(design["clusters"]) == 2
    assert design["interval_eligible"]


def test_cross_category_dependency_suppresses_stratified_interval():
    cases = corpus(2, variants=("isolated",))
    cases[1]["category"] = "music"
    for c in cases:
        c["cluster_id"] = "shared"
    design = dependency_clusters(cases)
    assert design["interval_unavailable_reason"] == "dependency_component_crosses_categories"


def test_alias_collisions_also_link_dependencies():
    cases = corpus(2, variants=("isolated",))
    cases[0]["targets"][0]["spoken_forms"] = ["term1"]
    assert len(dependency_clusters(cases)["clusters"]) == 1


def test_audit_reports_duplicates_provenance_and_normalization_without_claiming_exposure():
    cases = corpus(1, variants=("isolated",))
    extra = deepcopy(cases[0])
    extra["id"] = "extra"
    extra["text"] = cases[0]["text"].upper()
    extra["rarity"] = {"zipf": 0, "provider": "wordfreq", "tier": "below-coverage"}
    cases[0]["targets"][0]["spoken_forms"] = [".", "TERM0"]
    report = audit_corpus(cases + [extra])
    assert report["normalized_duplicate_text_groups"] == [[cases[0]["id"], "extra"]]
    assert report["duplicate_text_groups"] == []
    assert len(report["redundant_or_empty_aliases"]) == 2
    assert len(report["missing_reference_urls"]) == 2
    assert report["claims"]["training_exposure_measured"] is False


def test_audit_empty_and_duplicate_ids_rejected():
    with pytest.raises(ValueError, match="empty"):
        audit_corpus([])
    c = corpus(1)[0]
    with pytest.raises(ValueError, match="duplicate"):
        audit_corpus([c, deepcopy(c)])


def test_blank_transcripts_remain_real_failures_not_missing():
    cases = corpus(2, variants=("isolated",))
    report = make_report(cases, failed=[c["id"] for c in cases])
    assert report["research_protocol"]["complete"]
    assert report["research_protocol"]["scores"]["primary_target_retention"] == 0
    assert report["summary"]["interval"] == [0, 0]


def test_control_length_audit_never_turns_matching_into_causal_evidence():
    cases = corpus(1, variants=("isolated", "control"))
    cases[0]["control_pair"] = cases[1]["id"]
    report = audit_corpus(cases)
    assert report["control_pair_audit"][0]["character_length_matched"]
    assert "does not match phonemes" in report["control_limitation"]


def test_distinct_written_targets_colliding_after_normalization_are_reported():
    cases = corpus(2, variants=("isolated",))
    cases[1]["targets"][0]["text"] = "TERM0"
    report = audit_corpus(cases)
    assert report["normalization_collisions"] == [
        {"normalized": "term0", "written_forms": ["TERM0", "term0"]}
    ]
