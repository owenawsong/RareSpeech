"""Versioned, balanced analysis alongside the historical occurrence-weighted proxy."""

from __future__ import annotations

import random
from collections import defaultdict

from .audit import dependency_clusters, lexical_key
from .io import digest, unique

PROTOCOL_ID = "rarespeech.balanced-primary.v1"


def _mean(values):
    values = [v for v in values if v is not None]
    return sum(values) / len(values) if values else None


def primary_terms(cases):
    result = {}
    for case in sorted(cases, key=lambda c: (c["variant"] != "isolated", c["id"])):
        if case["variant"] != "control":
            result.setdefault(case["family_id"], lexical_key(case["targets"][0]["text"]))
    return result


def balanced_scores(rows, cases):
    """Equal weight: category -> family -> condition -> case -> repeat -> occurrence.

    Occurrence means keep repeats of the same primary term from over-weighting
    extended passages. All-target retention additionally includes neighbors.
    """
    primaries = primary_terms(cases)
    cells = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(list))))
    for row in rows:
        if row["variant"] == "control" or not row.get("metrics"):
            continue
        targets = row["metrics"]["targets"]
        primary = [t for t in targets if lexical_key(t["text"]) == primaries[row["family_id"]]]
        values = {
            "primary_target_retention": _mean([int(t["retained"]) for t in primary]),
            "all_target_retention": _mean([int(t["retained"]) for t in targets]),
        }
        cells[row["category"]][row["family_id"]][row["variant"]][row["case_id"]].append(values)
    metrics = ("primary_target_retention", "all_target_retention")
    family_rows, category_rows, condition_rows = [], [], defaultdict(list)
    for category, families in sorted(cells.items()):
        family_values = []
        for family, conditions in sorted(families.items()):
            condition_values = []
            for condition, case_rows in sorted(conditions.items()):
                value = {
                    m: _mean(
                        [_mean([r[m] for r in repeats if r[m] is not None]) for repeats in case_rows.values()]
                    )
                    for m in metrics
                }
                condition_values.append(value)
                condition_rows[(category, condition)].append(value)
            value = {m: _mean([v[m] for v in condition_values if v[m] is not None]) for m in metrics}
            family_values.append(value)
            family_rows.append({"category": category, "family_id": family, **value})
        category_rows.append(
            {"category": category, **{m: _mean([v[m] for v in family_values]) for m in metrics}}
        )
    scores = {m: _mean([v[m] for v in category_rows]) for m in metrics}
    conditions = []
    for condition in sorted({key[1] for key in condition_rows}):
        categories = [vs for (cat, cond), vs in condition_rows.items() if cond == condition]
        conditions.append(
            {
                "condition": condition,
                **{m: _mean([_mean([v[m] for v in vs]) for vs in categories]) for m in metrics},
            }
        )
    return {"scores": scores, "categories": category_rows, "families": family_rows, "conditions": conditions}


def analyze_protocol(rows, cases):
    observed = balanced_scores(rows, cases)
    expected = {c["id"] for c in cases if c["variant"] != "control"}
    seen = {r["case_id"] for r in rows if r["variant"] != "control" and r.get("metrics")}
    complete = (
        bool(expected)
        and expected == seen
        and all(r.get("metrics") is not None for r in rows if r["variant"] != "control")
    )
    primaries = primary_terms(cases)
    missing_primary = [
        r["id"]
        for r in rows
        if r["variant"] != "control"
        and r.get("metrics")
        and not any(lexical_key(t["text"]) == primaries[r["family_id"]] for t in r["metrics"]["targets"])
    ]
    complete = complete and not missing_primary
    recognizers = sorted(
        {
            digest({"engine": r["transcript"].get("engine"), "settings": r["transcript"].get("settings")})
            for r in rows
            if r["variant"] != "control" and r.get("transcript")
        }
    )
    consistent = len(recognizers) <= 1
    eligible = complete and consistent
    return {
        "schema": "rarespeech.protocol.v1",
        "protocol_id": PROTOCOL_ID,
        "label": "Balanced primary-target retention (ASR proxy)",
        "weighting": "equal category / family / condition / case / generation repeat; mean primary occurrences",
        "complete": complete,
        "headline_eligible": eligible,
        "recognizer_consistent": consistent,
        "recognizer_configuration_count": len(recognizers),
        "coverage": {
            "expected_cases": len(expected),
            "scored_cases": len(seen),
            "missing_case_ids": sorted(expected - seen),
            "scored_rows_without_primary": sorted(missing_primary),
        },
        "scores": observed["scores"] if eligible else {m: None for m in observed["scores"]},
        "observed_scores": observed["scores"],
        "categories": observed["categories"],
        "families": observed["families"],
        "conditions": observed["conditions"],
        "dependency_design": dependency_clusters(cases),
        "limitations": [
            "ASR retention is not pronunciation ground truth.",
            "Condition values apply only to the declared selected corpus.",
            "Controls are excluded; this score is not a causal rarity penalty.",
        ],
    }


def paired_analysis(left, right, samples=1000, seed=17):
    """Paired dependency-cluster resampling; a single cluster gives no interval."""
    if type(samples) is not int or samples < 2:
        raise ValueError("bootstrap samples must be an integer >= 2")
    if left["corpus_hash"] != right["corpus_hash"]:
        raise ValueError("paired analysis requires identical selected corpora")
    if left.get("measurement_hash") != right.get("measurement_hash"):
        raise ValueError("paired analysis requires identical evaluator implementations")
    left_rows, right_rows = unique(left["rows"]), unique(right["rows"])
    if set(left_rows) != set(right_rows):
        raise ValueError("paired analysis requires identical sample IDs/repeats")
    for sid, row in left_rows.items():
        other = right_rows[sid]
        if row["case_id"] != other["case_id"]:
            raise ValueError("paired analysis requires identical sample-to-case assignments")
        ta, tb = row.get("transcript"), other.get("transcript")
        if ta and tb and (ta.get("engine"), ta.get("settings")) != (tb.get("engine"), tb.get("settings")):
            raise ValueError("paired analysis requires identical ASR configurations")
    cases = left["cases"]
    x, y = analyze_protocol(left["rows"], cases), analyze_protocol(right["rows"], cases)
    complete = x["complete"] and y["complete"]
    consistent = x["recognizer_consistent"] and y["recognizer_consistent"]
    keys = tuple(x["scores"])
    deltas = {k: y["scores"][k] - x["scores"][k] if complete and consistent else None for k in keys}
    design = dependency_clusters(cases)
    reason = None if complete else "incomplete_noncontrol_coverage"
    reason = reason or (None if consistent else "mixed_recognizer_configurations")
    reason = reason or design["interval_unavailable_reason"]
    intervals = {k: None for k in keys}
    if reason is None:
        grouped = defaultdict(list)
        for cluster in design["clusters"]:
            grouped[cluster["categories"][0]].append(cluster)
        # Pre-aggregate all within-family levels once. Resampling a family or
        # connected cluster changes its multiplicity, not its internal score.
        family_left = {f["family_id"]: f for f in x["families"]}
        family_right = {f["family_id"]: f for f in y["families"]}
        rng, draws = random.Random(seed), {k: [] for k in keys}
        for _ in range(samples):
            category_deltas = {k: [] for k in keys}
            for category, clusters in sorted(grouped.items()):
                members = [
                    f for cluster in rng.choices(clusters, k=len(clusters)) for f in cluster["families"]
                ]
                for k in keys:
                    category_deltas[k].append(
                        _mean([family_right[f][k] - family_left[f][k] for f in members])
                    )
            for k in keys:
                draws[k].append(_mean(category_deltas[k]))
        for k, values in draws.items():
            values.sort()
            intervals[k] = [values[int(0.025 * samples)], values[min(samples - 1, int(0.975 * samples))]]
    return {
        "protocol_id": PROTOCOL_ID,
        "complete": complete,
        "candidate_minus_baseline": deltas,
        "intervals_95_percentile": intervals,
        "interval_unavailable_reason": reason,
        "resampling": {
            "unit": "lexical-dependency cluster",
            "strata": "category",
            "paired": True,
            "draws": samples,
            "seed": seed,
        },
        "dependency_design": design,
        "note": "Conditional on these terms, carriers, voices and ASR; does not include recognizer or human-review bias.",
    }
