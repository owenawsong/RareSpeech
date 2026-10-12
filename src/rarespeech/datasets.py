"""Frozen, packaged evaluation tracks with explicit selection identities."""
import json
from pathlib import Path

from .corpus import corpus_hash, load_cases

TRACKS = {"core": "core-v1.jsonl", "stress": "stress-v1.jsonl", "legacy": "challenge-v1.jsonl"}


def dataset_path(track="core"):
    if track not in TRACKS:
        raise ValueError(f"unknown track: {track}")
    return Path(__file__).parent / "data" / TRACKS[track]


def track_identity(cases):
    measured_hash = corpus_hash(cases)
    for track, filename in TRACKS.items():
        path = Path(__file__).parent / "data" / filename
        if path.exists() and corpus_hash(load_cases(path)) == measured_hash:
            return {"name": track, "revision": "core-v1" if track == "core" else "stress-v1" if track == "stress" else "legacy-v0.1",
                    "canonical": True, "cases": len(cases), "corpus_hash": measured_hash}
    return {"name": "custom-or-subset", "canonical": False, "cases": len(cases), "corpus_hash": measured_hash}


def manifest():
    return json.loads((Path(__file__).parent / "data/core-manifest.json").read_text(encoding="utf-8"))
