"""Verify publication artifacts, not model-quality claims."""

import json
import tempfile
from collections import Counter
from pathlib import Path

from rarespeech.corpus import corpus_hash, load_cases
from rarespeech.io import file_hash, safe_child
from rarespeech.submission import submission

ROOT = Path(__file__).resolve().parents[1]


def main():
    cases = load_cases(ROOT / "data/challenge-v1.jsonl")
    manifest = json.loads((ROOT / "data/manifest.json").read_text(encoding="utf-8"))
    assert corpus_hash(cases) == manifest["corpus_hash"], "manifest hash mismatch"
    core = load_cases(ROOT / "data/core-v1.jsonl")
    stress = load_cases(ROOT / "data/stress-v1.jsonl")
    assert Counter(c["variant"] for c in core) == {"isolated": 64, "dense": 64}
    assert Counter(c["variant"] for c in stress) == {"confusable": 64, "extended": 64, "control": 64}
    core_manifest = json.loads((ROOT / "data/core-manifest.json").read_text(encoding="utf-8"))
    assert corpus_hash(core) == core_manifest["corpus_hash"]
    assert corpus_hash(stress) == core_manifest["stress_hash"]
    for name in ("challenge-v1.jsonl", "core-v1.jsonl", "stress-v1.jsonl"):
        assert file_hash(ROOT / "data" / name) == file_hash(ROOT / "src/rarespeech/data" / name)
    definitions = {c["id"]: c for c in [*cases, *core, *stress]}
    checks = json.loads((ROOT / "data/lexical-source-checks.json").read_text(encoding="utf-8"))
    documented = {c["term"] for c in checks if c["status"] == 200 and c["english"] and not c["missing"]}
    assert {c["targets"][0]["text"] for c in cases if c["variant"] == "isolated"} <= documented
    # No fabricated human review results in integration examples.
    clips, core_clips = 0, 0
    for path in (ROOT / "examples").glob("*/report.json"):
        report = json.loads(path.read_text(encoding="utf-8"))
        assert report["summary"]["complete"]
        assert not report["reviews"] and report["review_summary"]["verified_accuracy"] is None
        assert all(definitions[c["id"]] == c for c in report["cases"]), (
            "measurement case differs from release corpus"
        )
        if path.parent.name.startswith("core-"):
            assert report["cases"] == core
            assert report["research_protocol"]["headline_eligible"]
            with tempfile.TemporaryDirectory() as directory:
                assert submission(report, Path(directory))["eligible_for_automatic_track_table"]
            correction = json.loads((path.parent / "provenance/correction.json").read_text(encoding="utf-8"))
            assert file_hash(path.parent / "provenance/original-cases.json") == correction["source_cases_sha256"]
            assert file_hash(path.parent / "provenance/original-run.json") == correction["source_run_sha256"]
            assert correction["corrected_corpus_hash"] == corpus_hash(core)
            assert file_hash(path.parent / "samples.json") == correction["source_files_sha256"]["samples.json"]
            assert file_hash(path.parent / "transcripts.jsonl") == correction["source_files_sha256"]["asr-small.en.jsonl"]
            assert file_hash(path.parent / "transcripts-base.jsonl") == correction["source_files_sha256"]["asr-base.en.jsonl"]
            core_clips += len(report["rows"])
        for row in report["rows"]:
            assert file_hash(safe_child(path.parent, row["audio"])) == row["audio_hash"]
            assert row["transcript"]["audio_hash"] == row["audio_hash"]
            clips += 1
        assert (path.parent / "asr-audit.json").exists()
        assert (path.parent / "badge.svg").exists()
        assert file_hash(path.parent / "app.js") == file_hash(ROOT / "src/rarespeech/web/app.js")
        assert file_hash(path.parent / "research.css") == file_hash(ROOT / "src/rarespeech/web/research.css")
    assert clips == 352 and core_clips == 256, f"expected 256 core and 96 historical clips, got {clips}"
    assert file_hash(ROOT / "site/app.js") == file_hash(ROOT / "src/rarespeech/web/app.js")
    assert file_hash(ROOT / "site/research.css") == file_hash(ROOT / "src/rarespeech/web/research.css")
    # Check local documentation references before publishing.
    import re

    for doc in [ROOT / "README.md", ROOT / "examples/README.md", ROOT / "data/DATASET_CARD.md", *ROOT.glob("docs/*.md")]:
        for link in re.findall(r"\]\(([^)]+)\)", doc.read_text(encoding="utf-8")):
            if not link.startswith(("http:", "https:", "#")):
                assert (doc.parent / link.split("#")[0]).exists(), f"broken doc link: {doc.name}: {link}"
    print(
        f"Release artifacts verified: 128 core + 192 stress + {len(cases)} legacy cases, 64 term sources, {clips} audio clips, submissions, links and frontend parity"
    )


if __name__ == "__main__":
    main()
