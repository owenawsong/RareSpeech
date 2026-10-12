from copy import deepcopy

import pytest

from rarespeech.metrics import align, bootstrap, score_case, tokens


def case(text="The mineral is omphacite.", term="omphacite", aliases=None):
    start = text.index(term)
    return {
        "id": "sample",
        "text": text,
        "category": "mineralogy",
        "variant": "isolated",
        "family_id": "mineralogy.01",
        "targets": [
            {
                "id": "t1",
                "text": term,
                "start": start,
                "end": start + len(term),
                "spoken_forms": aliases or [],
            }
        ],
    }


def test_exact_and_normalization():
    m = score_case(case(), "THE mineral is omphacite!")
    assert m["wer"] == 0
    assert m["targets"][0]["retained"]
    assert tokens("Noetherian naïve co-homology") == ["noetherian", "naïve", "co", "homology"]


def test_empty_transcript_is_failure():
    m = score_case(case(), "")
    assert m["wer"] == 1
    assert not m["targets"][0]["retained"]


def test_substitution_and_extra_speech():
    m = score_case(case(), "The mineral is amphibole. Extra speech.")
    assert m["sub"] == 1
    assert m["insert"] == 2
    assert not m["targets"][0]["retained"]


def test_alias_changes_only_designated_occurrence():
    c = case("The clock shows 3:30.", "3:30", ["three thirty"])
    assert score_case(c, "The clock shows three thirty")["wer"] == 0
    assert score_case(c, "The clock shows three thirteen")["wer"] > 0


def test_occurrence_elsewhere_does_not_rescue_all_targets():
    c = case("omphacite then omphacite")
    c["targets"].append({"id": "t2", "text": "omphacite", "start": 15, "end": 24})
    m = score_case(c, "omphacite then")
    assert sum(t["retained"] for t in m["targets"]) == 1


def test_diacritics_not_silently_removed():
    assert score_case(case("Say naïve", "naïve"), "Say naive")["wer"] == 0.5


def test_alignment_known_edit_distance():
    ops = align(["a", "b", "c"], ["a", "x", "c", "d"])
    assert sum(op != "match" for op, _, _ in ops) == 2


def test_bootstrap_requires_families_not_repeated_samples():
    c = case()
    row = {**c, "metrics": score_case(c, c["text"])}
    assert bootstrap([row] * 20) is None
    row2 = deepcopy(row)
    row2["family_id"] = "mineralogy.02"
    assert bootstrap([row, row2], samples=100) == [1, 1]


def test_reference_alternatives_bounded():
    c = case()
    c["targets"][0]["spoken_forms"] = [f"form {i}" for i in range(65)]
    with pytest.raises(ValueError):
        score_case(c, "anything")
