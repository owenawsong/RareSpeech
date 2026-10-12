from __future__ import annotations

import re
from pathlib import Path

from .io import digest, read_jsonl, unique

ID = re.compile(r"^[a-z0-9][a-z0-9._-]{0,100}$")
VARIANTS = {"isolated", "dense", "confusable", "extended", "control"}


def load_cases(path: Path) -> list[dict]:
    cases = read_jsonl(path)
    unique(cases)
    if not cases:
        raise ValueError("empty corpus")
    for case in cases:
        for field in ("id", "family_id", "category"):
            if not isinstance(case.get(field), str) or not ID.fullmatch(case[field]):
                raise ValueError(f"invalid {field}: {case.get(field)!r}")
        if case.get("variant") not in VARIANTS:
            raise ValueError(f"invalid variant in {case['id']}")
        if case.get("language") != "en":
            raise ValueError("v0.1 scoring supports English only")
        text = case.get("text")
        if not isinstance(text, str) or not text.strip() or len(text) > 50000:
            raise ValueError(f"invalid text in {case['id']}")
        targets = case.get("targets")
        if not isinstance(targets, list) or not targets:
            raise ValueError(f"missing targets in {case['id']}")
        seen = set()
        occupied = set()
        for target in targets:
            tid, start, end = target.get("id"), target.get("start"), target.get("end")
            if not isinstance(tid, str) or not ID.fullmatch(tid) or tid in seen:
                raise ValueError(f"invalid/duplicate target in {case['id']}")
            seen.add(tid)
            if type(start) is not int or type(end) is not int or not 0 <= start < end <= len(text):
                raise ValueError(f"invalid target offsets in {case['id']}")
            if text[start:end] != target.get("text"):
                raise ValueError(f"target text/offset mismatch in {case['id']}")
            positions = set(range(start, end))
            if occupied & positions:
                raise ValueError(f"overlapping targets in {case['id']}")
            occupied |= positions
            aliases = target.get("spoken_forms", [])
            if not isinstance(aliases, list) or any(not isinstance(a, str) or not a.strip() for a in aliases):
                raise ValueError(f"invalid spoken forms in {case['id']}")
    return cases


def select(cases, category=None, variant=None, limit=None):
    result = [
        c
        for c in cases
        if (not category or c["category"] == category) and (not variant or c["variant"] == variant)
    ]
    if limit is not None:
        if limit < 1:
            raise ValueError("limit must be positive")
        result = result[:limit]
    if not result:
        raise ValueError("selection is empty")
    return result


def corpus_hash(cases) -> str:
    return digest(sorted(cases, key=lambda c: c["id"]))
