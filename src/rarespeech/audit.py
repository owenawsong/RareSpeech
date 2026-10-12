"""Design diagnostics; these checks cannot establish training-data absence."""

from __future__ import annotations

import math
from collections import Counter, defaultdict

from .metrics import tokens


def lexical_key(text):
    return " ".join(tokens(text))


def dependency_clusters(cases):
    """Connected family components under shared targets or declared cluster IDs.

    Controls are excluded: a common control word is not rare-lexeme evidence.
    This is a conservative dependency model, not a proof of independence.
    """
    families = {c["family_id"] for c in cases if c["variant"] != "control"}
    parent = {f: f for f in families}

    def find(f):
        while parent[f] != f:
            parent[f] = parent[parent[f]]
            f = parent[f]
        return f

    def union(a, b):
        a, b = find(a), find(b)
        if a != b:
            parent[max(a, b)] = min(a, b)

    owners, declarations, categories = defaultdict(set), defaultdict(set), defaultdict(set)
    for case in cases:
        if case["variant"] == "control":
            continue
        family = case["family_id"]
        categories[family].add(case["category"])
        if case.get("cluster_id"):
            declarations[case["cluster_id"]].add(family)
        for target in case["targets"]:
            for form in [target["text"], *target.get("spoken_forms", [])]:
                key = lexical_key(form)
                if key:
                    owners[key].add(family)
    for group in list(owners.values()) + list(declarations.values()):
        ordered = sorted(group)
        for f in ordered[1:]:
            union(ordered[0], f)
    components = defaultdict(list)
    for family in sorted(families):
        components[find(family)].append(family)
    groups = []
    by_family = {}
    for root, members in sorted(components.items()):
        cats = sorted({cat for f in members for cat in categories[f]})
        groups.append({"id": root, "families": members, "categories": cats})
        by_family.update({f: root for f in members})
    category_counts = Counter(cat for g in groups for cat in g["categories"])
    cross = [g["id"] for g in groups if len(g["categories"]) > 1]
    reason = None
    if not groups:
        reason = "no_noncontrol_families"
    elif cross:
        reason = "dependency_component_crosses_categories"
    elif any(count < 2 for count in category_counts.values()):
        reason = "fewer_than_two_dependency_clusters_in_a_category"
    return {
        "method": "shared-normalized-target/accepted-form and declared-cluster transitive closure",
        "clusters": groups,
        "family_to_cluster": by_family,
        "clusters_per_category": dict(sorted(category_counts.items())),
        "cross_category_clusters": cross,
        "shared_targets": [
            {"text": term, "families": sorted(group)}
            for term, group in sorted(owners.items())
            if len(group) > 1
        ],
        "interval_eligible": reason is None,
        "interval_unavailable_reason": reason,
        "limitation": "Lexical closure does not account for all morphological, carrier or speaker dependencies.",
    }


def audit_corpus(cases):
    """Return inspectable coverage and provenance diagnostics without silent fixes."""
    if not cases:
        raise ValueError("cannot audit an empty corpus")
    ids = [c["id"] for c in cases]
    if len(set(ids)) != len(ids):
        raise ValueError("duplicate corpus IDs")
    terms, carriers, texts, normalized_texts = (
        defaultdict(set),
        Counter(),
        defaultdict(list),
        defaultdict(list),
    )
    written_forms = defaultdict(set)
    frequencies, lengths, aliases = [], Counter(), []
    sources_missing, pronunciations = [], Counter()
    family_conditions = defaultdict(Counter)
    first_primary = {}
    for case in cases:
        family_conditions[case["family_id"]][case["variant"]] += 1
        if case["variant"] == "isolated":
            first_primary[case["family_id"]] = case
        elif case["variant"] != "control":
            first_primary.setdefault(case["family_id"], case)
        texts[case["text"]].append(case["id"])
        normalized_texts[lexical_key(case["text"])].append(case["id"])
        cursor, carrier = 0, ""
        for target in sorted(case["targets"], key=lambda t: t["start"]):
            carrier += case["text"][cursor : target["start"]] + " <TARGET> "
            cursor = target["end"]
            if case["variant"] == "control":
                continue
            terms[lexical_key(target["text"])].add(case["family_id"])
            written_forms[lexical_key(target["text"])].add(target["text"])
            pronunciations[target.get("pronunciation_status", "unspecified")] += 1
            if not target.get("reference_url"):
                sources_missing.append({"case_id": case["id"], "target_id": target["id"]})
            for alias in target.get("spoken_forms", []):
                if not tokens(alias) or lexical_key(alias) == lexical_key(target["text"]):
                    aliases.append({"case_id": case["id"], "target_id": target["id"], "alias": alias})
        carrier += case["text"][cursor:]
        if case["variant"] != "control":
            carriers[carrier] += 1
    for family, case in sorted(first_primary.items()):
        lengths[len(case["targets"][0]["text"])] += 1
        rarity = case.get("rarity", {})
        zipf = rarity.get("zipf")
        frequencies.append(
            {
                "family_id": family,
                "term": case["targets"][0]["text"],
                "zipf": zipf
                if isinstance(zipf, (int, float)) and not isinstance(zipf, bool) and math.isfinite(zipf)
                else None,
                "provider": rarity.get("provider"),
                "version": rarity.get("version"),
                "tier": rarity.get("tier", "unspecified"),
            }
        )
    cmap = {c["id"]: c for c in cases}
    controls = []
    for family, primary in sorted(first_primary.items()):
        control = cmap.get(primary.get("control_pair"))
        if control is None:
            controls.append(
                {"family_id": family, "pair_declared": bool(primary.get("control_pair")), "available": False}
            )
            continue
        primary_text, control_text = primary["targets"][0]["text"], control["targets"][0]["text"]
        controls.append(
            {
                "family_id": family,
                "available": True,
                "character_length_matched": len(primary_text) == len(control_text),
                "primary_characters": len(primary_text),
                "control_characters": len(control_text),
                "primary_tokens": len(tokens(primary_text)),
                "control_tokens": len(tokens(control_text)),
            }
        )
    return {
        "schema": "rarespeech.corpus-audit.v1",
        "cases": len(cases),
        "families": len(first_primary),
        "unique_noncontrol_targets": len(terms),
        "categories": dict(sorted(Counter(c["category"] for c in cases).items())),
        "conditions": dict(sorted(Counter(c["variant"] for c in cases).items())),
        "family_conditions": {f: dict(sorted(v.items())) for f, v in sorted(family_conditions.items())},
        "primary_frequency": frequencies,
        "primary_frequency_tiers": dict(sorted(Counter(f["tier"] for f in frequencies).items())),
        "primary_term_character_lengths": dict(sorted(lengths.items())),
        "carrier_diversity": {
            "unique": len(carriers),
            "noncontrol_cases": sum(carriers.values()),
            "largest_reuse": max(carriers.values(), default=0),
        },
        "most_reused_carriers": [
            {"template": template, "cases": count}
            for template, count in sorted(carriers.items(), key=lambda pair: (-pair[1], pair[0]))[:10]
        ],
        "duplicate_text_groups": [v for v in texts.values() if len(v) > 1],
        "normalized_duplicate_text_groups": [v for v in normalized_texts.values() if len(v) > 1],
        "redundant_or_empty_aliases": aliases,
        "normalization_collisions": [
            {"normalized": key, "written_forms": sorted(forms)}
            for key, forms in sorted(written_forms.items())
            if len(forms) > 1
        ],
        "normalizer": "NFKC, casefold, punctuation boundaries, apostrophes retained; diacritics and numbers preserved",
        "control_pair_audit": controls,
        "control_limitation": "Character/token length matching does not match phonemes, stress, familiarity or carrier semantics.",
        "missing_reference_urls": sources_missing,
        "pronunciation_status_occurrences": dict(sorted(pronunciations.items())),
        "dependency_design": dependency_clusters(cases),
        "claims": {"training_exposure_measured": False, "expert_validation_established": False},
    }
