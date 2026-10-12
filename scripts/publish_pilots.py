"""Package measured, hash-checked engineering pilots. No invented transcripts or votes."""

import json
import shutil
from pathlib import Path

from rarespeech.evaluate import audit_asr, evaluate
from rarespeech.io import read_jsonl, write_json
from rarespeech.report import build_report

ROOT = Path(__file__).resolve().parents[1]
PILOTS = [
    (
        "nano-final",
        "inflect-nano",
        "Inflect Nano v2",
        "Author-maintained model; CPU, 32-case integration pilot.",
    ),
    (
        "micro-final",
        "inflect-micro",
        "Inflect Micro v2",
        "Author-maintained model; CPU, 32-case integration pilot.",
    ),
    (
        "piper-final",
        "piper-danny",
        "Piper · Danny low",
        "Separate TTS pipeline; CPU, 32-case integration pilot.",
    ),
]


def main():
    index = []
    for source, slug, name, description in PILOTS:
        run = ROOT / "runs" / source
        transcript = run / "asr-small.jsonl"
        if not transcript.exists():
            raise ValueError(f"complete small.en transcripts first: {source}")
        cases = json.loads((run / "cases.json").read_text())
        samples = json.loads((run / "samples.json").read_text())
        meta = json.loads((run / "run.json").read_text())
        meta["publication"] = {
            "status": "engineering integration pilot, not benchmark ranking",
            "selection": "first family in each domain; isolated/dense/extended/control; one generation",
            "reviewed": False,
            "author_relationship": "Inflect is maintained by Owen Song",
            "scope": "English; local CPU inference; automatic ASR diagnostics",
        }
        result = evaluate(cases, samples, read_jsonl(transcript), meta)
        if not result["summary"]["complete"]:
            raise ValueError("cannot publish an unfinished pilot")
        out = ROOT / "examples" / slug
        base_path = run / "asr-base.jsonl"
        if base_path.exists():
            alternate = evaluate(cases, samples, read_jsonl(base_path), meta)
            audit = audit_asr(alternate, result)
            result["asr_audit"] = audit
            for row in result["rows"]:
                row["asr_disagreements"] = [d for d in audit["disagreements"] if d["sample_id"] == row["id"]]
                row["needs_review"] = row["needs_review"] or bool(row["asr_disagreements"])
            write_json(out / "asr-audit.json", audit)
            write_json(out / "alternate-asr-report.json", alternate)
            shutil.copyfile(base_path, out / "transcripts-base.jsonl")
        build_report(result, out, run)
        shutil.copyfile(transcript, out / "transcripts.jsonl")
        write_json(out / "run.json", meta)
        write_json(out / "samples.json", samples)
        write_json(out / "cases.json", cases)
        index.append(
            {
                "slug": slug,
                "url": "examples/" + slug + "/index.html",
                "name": name,
                "description": description,
                "label": "Measured pilot · Whisper small.en",
            }
        )
    write_json(ROOT / "examples" / "index.json", index)
    print("Published three measured pilots with original WAVs and provenance")


if __name__ == "__main__":
    main()
