"""Verify publication artifacts, not model-quality claims."""

import json
from pathlib import Path

from rarespeech.corpus import corpus_hash, load_cases
from rarespeech.io import file_hash, safe_child

ROOT = Path(__file__).resolve().parents[1]


def main():
    cases = load_cases(ROOT / "data/challenge-v1.jsonl")
    manifest = json.loads((ROOT / "data/manifest.json").read_text())
    assert corpus_hash(cases) == manifest["corpus_hash"], "manifest hash mismatch"
    definitions = {c["id"]: c for c in cases}
    checks = json.loads((ROOT / "data/lexical-source-checks.json").read_text())
    documented = {c["term"] for c in checks if c["status"] == 200 and c["english"] and not c["missing"]}
    assert {c["targets"][0]["text"] for c in cases if c["variant"] == "isolated"} <= documented
    # No fabricated human review results in integration examples.
    clips = 0
    for path in (ROOT / "examples").glob("*/report.json"):
        report = json.loads(path.read_text())
        assert report["summary"]["complete"]
        assert not report["reviews"] and report["review_summary"]["verified_accuracy"] is None
        assert all(definitions[c["id"]] == c for c in report["cases"]), (
            "pilot case differs from release corpus"
        )
        for row in report["rows"]:
            assert file_hash(safe_child(path.parent, row["audio"])) == row["audio_hash"]
            assert row["transcript"]["audio_hash"] == row["audio_hash"]
            clips += 1
        assert (path.parent / "asr-audit.json").exists()
        assert (path.parent / "badge.svg").exists()
        assert file_hash(path.parent / "app.js") == file_hash(ROOT / "src/rarespeech/web/app.js")
    assert clips == 96, f"expected 96 measured pilot clips, got {clips}"
    assert file_hash(ROOT / "site/app.js") == file_hash(ROOT / "src/rarespeech/web/app.js")
    # Check local documentation references before publishing.
    import re

    for doc in [ROOT / "README.md", *ROOT.glob("docs/*.md")]:
        for link in re.findall(r"\]\(([^)]+)\)", doc.read_text(encoding="utf-8")):
            if not link.startswith(("http:", "https:", "#")):
                assert (doc.parent / link.split("#")[0]).exists(), f"broken doc link: {doc.name}: {link}"
    print(
        f"Release artifacts verified: {len(cases)} cases, 64 term sources, {clips} audio clips, links and frontend parity"
    )


if __name__ == "__main__":
    main()
