from __future__ import annotations

import itertools
import random
import re
import unicodedata


def tokens(text: str) -> list[str]:
    """Conservative lexical normalization. No spelling correction or semantic repair."""
    text = unicodedata.normalize("NFKC", text).casefold().replace("’", "'")
    # Hyphens split compounds; diacritics and numeric values are retained.
    return re.findall(r"[^\W_]+(?:'[^\W_]+)*", text, flags=re.UNICODE)


def align(reference: list[str], hypothesis: list[str]) -> list[tuple[str, int | None, int | None]]:
    """Levenshtein alignment, deterministic tie policy: match/substitute, delete, insert."""
    n, m = len(reference), len(hypothesis)
    if n * m > 4_000_000:
        raise ValueError("alignment exceeds 4 million cells; split the case")
    costs = [list(range(m + 1))]
    for i, word in enumerate(reference, 1):
        row = [i]
        prev = costs[-1]
        for j, heard in enumerate(hypothesis, 1):
            row.append(min(prev[j - 1] + (word != heard), prev[j] + 1, row[-1] + 1))
        costs.append(row)
    result = []
    i, j = n, m
    while i or j:
        if i and j and costs[i][j] == costs[i - 1][j - 1] + (reference[i - 1] != hypothesis[j - 1]):
            result.append(("match" if reference[i - 1] == hypothesis[j - 1] else "sub", i - 1, j - 1))
            i -= 1
            j -= 1
        elif i and costs[i][j] == costs[i - 1][j] + 1:
            result.append(("delete", i - 1, None))
            i -= 1
        else:
            result.append(("insert", None, j - 1))
            j -= 1
    return result[::-1]


def score_case(case: dict, transcript: str) -> dict:
    """Accept only explicitly authored target aliases; target hits are alignment-local."""
    if not isinstance(transcript, str):
        raise ValueError("transcript must be a string (empty is a valid failed reading)")
    targets = sorted(case["targets"], key=lambda t: t["start"])
    options = [[t["text"]] + t.get("spoken_forms", []) for t in targets]
    combinations = 1
    for opt in options:
        combinations *= len(opt)
    if combinations > 64:
        raise ValueError("too many spoken-form combinations")
    heard = tokens(transcript)
    best = None
    for choices in itertools.product(*options):
        reference, spans, cursor = [], [], 0
        for target, choice in zip(targets, choices):
            reference += tokens(case["text"][cursor : target["start"]])
            start = len(reference)
            reference += tokens(choice)
            spans.append((start, len(reference)))
            cursor = target["end"]
        reference += tokens(case["text"][cursor:])
        ops = align(reference, heard)
        error = sum(op != "match" for op, _, _ in ops)
        if best is None or error < best[0]:
            best = error, reference, spans, ops, choices
    _, reference, spans, ops, choices = best
    result_targets = []
    for target, (start, end), choice in zip(targets, spans, choices):
        inside = [(op, r, h) for op, r, h in ops if r is not None and start <= r < end]
        retained = bool(inside) and all(op == "match" for op, _, _ in inside)
        result_targets.append(
            {
                "id": target["id"],
                "text": target["text"],
                "accepted_form": choice,
                "retained": retained,
                "heard": " ".join(heard[h] for _, _, h in inside if h is not None),
            }
        )
    errors = {kind: sum(op == kind for op, _, _ in ops) for kind in ("sub", "delete", "insert")}
    return {
        "reference_tokens": len(reference),
        "errors": sum(errors.values()),
        **errors,
        "wer": sum(errors.values()) / len(reference) if reference else None,
        "targets": result_targets,
        "alignment": [
            {
                "op": op,
                "expected": reference[r] if r is not None else None,
                "heard": heard[h] if h is not None else None,
            }
            for op, r, h in ops
        ],
    }


def macro_accuracy(rows: list[dict]) -> float | None:
    buckets = {}
    for row in rows:
        if row["variant"] == "control" or not row.get("metrics"):
            continue
        b = buckets.setdefault(row["category"], [0, 0])
        t = row["metrics"]["targets"]
        b[0] += sum(x["retained"] for x in t)
        b[1] += len(t)
    return sum(good / total for good, total in buckets.values()) / len(buckets) if buckets else None


def bootstrap(rows: list[dict], samples=1000, seed=17):
    # Resample term families together: variants/repeats are not independent evidence.
    categories = {}
    for row in rows:
        if row["variant"] != "control" and row.get("metrics"):
            categories.setdefault(row["category"], {}).setdefault(row["family_id"], []).append(row)
    if not categories or any(len(families) < 2 for families in categories.values()):
        return None
    rng = random.Random(seed)
    values = []
    for _ in range(samples):
        chosen = []
        for families in categories.values():
            keys = list(families)
            for key in rng.choices(keys, k=len(keys)):
                chosen.extend(families[key])
        values.append(macro_accuracy(chosen))
    values.sort()
    return [values[int(0.025 * samples)], values[min(samples - 1, int(0.975 * samples))]]
