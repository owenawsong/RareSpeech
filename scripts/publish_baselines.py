"""Publish measured full-core evidence from local captures. Never synthesize scores."""

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from rarespeech.corpus import corpus_hash, load_cases  # noqa: E402
from rarespeech.evaluate import audit_asr, compare, evaluate  # noqa: E402
from rarespeech.io import read_jsonl, write_json  # noqa: E402
from rarespeech.report import build_report  # noqa: E402
from rarespeech.submission import submission  # noqa: E402

CONFIGURATIONS = [
    ("core-piper-danny-corrected", "core-piper-danny", "Piper / en_US-danny-low"),
    ("core-kokoro-heart-corrected", "core-kokoro-heart", "Kokoro-82M v1.0 / af_heart (ONNX)"),
]


def pct(value):
    return "not measured" if value is None else f"{value * 100:.2f}%"


def main():
    canonical = load_cases(ROOT / "data/core-v1.jsonl")
    index_path = ROOT / "examples/index.json"
    index = [item for item in json.loads(index_path.read_text(encoding="utf-8")) if item.get("legacy")]
    reports, table, conditions, identities = [], [], [], []
    for source, slug, name in CONFIGURATIONS:
        run = ROOT / "runs" / source
        cases = json.loads((run / "cases.json").read_text(encoding="utf-8"))
        if cases != canonical:
            raise ValueError(f"baseline cases must match canonical core: {source}")
        samples = json.loads((run / "samples.json").read_text(encoding="utf-8"))
        meta = json.loads((run / "run.json").read_text(encoding="utf-8"))
        meta["publication"] = {"status": "full-core automatic baseline; independent listening pending",
                               "scope": "English; original local CPU clips; one generation per case",
                               "selection": "complete core v1, 128 cases", "reviewed": False,
                               "timing_comparable": False}
        primary = read_jsonl(run / "asr-small.en.jsonl")
        secondary = read_jsonl(run / "asr-base.en.jsonl")
        result = evaluate(cases, samples, primary, meta)
        alternate = evaluate(cases, samples, secondary, meta)
        if not result["summary"]["complete"] or not alternate["summary"]["complete"]:
            raise ValueError(f"incomplete measured baseline: {source}")
        audit = audit_asr(result, alternate)
        result["asr_audit"] = audit
        for row in result["rows"]:
            row["asr_disagreements"] = [d for d in audit["disagreements"] if d["sample_id"] == row["id"]]
            row["needs_review"] = row["needs_review"] or bool(row["asr_disagreements"])
        out = ROOT / "examples" / slug
        build_report(result, out, run)
        check = submission(result, out / "submission")
        if not check["eligible_for_automatic_track_table"]:
            raise ValueError(f"baseline failed submission checks: {source}: {check['blockers']}")
        for source_name, public_name in (("asr-small.en.jsonl", "transcripts.jsonl"),
                                         ("asr-base.en.jsonl", "transcripts-base.jsonl"),
                                         ("cases.json", "cases.json"), ("samples.json", "samples.json")):
            shutil.copyfile(run / source_name, out / public_name)
        write_json(out / "run.json", meta)
        shutil.copytree(run / "provenance", out / "provenance", dirs_exist_ok=True)
        write_json(out / "alternate-asr-report.json", alternate)
        write_json(out / "asr-audit.json", audit)
        reports.append((slug, result))
        score = result["research_protocol"]["scores"]["primary_target_retention"]
        alternative = alternate["research_protocol"]["scores"]["primary_target_retention"]
        table.append(f"| {name} | {pct(score)} | {pct(result['totals']['all']['wer'])} | {pct(alternative)} | {len(audit['disagreements'])} / 128 | [Evidence](../examples/{slug}/report.json) |")
        values = {r["condition"]: r["primary_target_retention"] for r in result["research_protocol"]["conditions"]}
        conditions.append(f"| {name} | {pct(values.get('isolated'))} | {pct(values.get('dense'))} |")
        identities.append(f"### {name}\n\nTTS revision: `{meta['identity']['adapter']['revision']}`.\n\nPublic generation identity: [run JSON](../examples/{slug}/run.json). Primary and secondary recognizer settings: [small.en](../examples/{slug}/transcripts.jsonl), [base.en](../examples/{slug}/transcripts-base.jsonl).\n")
        index.insert(len(index) - sum(e.get("legacy", False) for e in index), {
            "slug": slug, "url": f"examples/{slug}/index.html", "name": name,
            "description": "Full core v1 · 128 original clips · two-recognizer audit",
            "label": "Core v1 · Whisper small.en", "legacy": False})
    comparisons = []
    for i, (left_slug, left) in enumerate(reports):
        for right_slug, right in reports[i + 1:]:
            name = f"{left_slug}--{right_slug}.json"
            result = compare(left, right)
            write_json(ROOT / "examples/comparisons" / name, result)
            comparisons.append(f"- [{left_slug} → {right_slug}](../examples/comparisons/{name}): candidate minus baseline; paired lexical-cluster bootstrap.")
    write_json(index_path, index)
    content = """# Measured baseline appendix · core v1

These are original CPU recordings from **two configurations across two TTS architectures**, each covering the same 128 cases. They are automatic lexical diagnostics, not a broad model ranking or verified pronunciation assessment. One generation per case; stochastic robustness and voice diversity remain unmeasured.

Primary recognizer: faster-whisper small.en, English, CPU int8, beam 5, temperature 0, VAD off, previous-text conditioning off. Secondary: base.en with the same decoding policy. Both record actual model/config SHA-256 and runtime versions. No vocabulary prompt or transcript repair.

| Configuration | Balanced retention ↑ / small.en | Rare-content WER ↓ / small.en | Balanced retention / base.en | Target verdict disagreements | Evidence |
|---|---:|---:|---:|---:|---|
""" + "\n".join(table) + "\n\n## Conditions / primary recognizer\n\n| Configuration | Bare term | Short context |\n|---|---:|---:|\n" + "\n".join(conditions)
    content += f"\n\nCore corpus SHA-256: `{corpus_hash(canonical)}`. Evaluator source SHA-256: `{reports[0][1]['measurement_hash']}`.\n\n"
    content += "Recognizer disagreement signals uncertainty, not which recognizer is right. Audio is supplied for every measured sample; human votes remain empty. The paired intervals below reflect variation over these declared lexical clusters, conditional on the carrier/voice/ASR choices; they do not include ASR bias or listener uncertainty.\n\n## Paired comparisons\n\n" + "\n".join(comparisons)
    content += "\n\n## Reproducible identities\n\n" + "\n".join(identities)
    content += """
## Annotation correction

Before publication, the core builder inherited an incorrect condition label from the legacy bare-term case. The actual case IDs, synthesis text, target offsets and audio were unchanged. An audited metadata-only correction sets the intended `variant`; originals, source hashes, changed fields and the correction reason remain in each evidence folder's `provenance/`. Audio and transcript files retain their original hashes. All scores were recomputed on the corrected frozen core. No recordings or listening votes were relabeled as better performances.

## Licensing and limits

No model weights are redistributed. Kokoro-82M is Apache-2.0; the ONNX adapter uses the upstream model-files-v1.1 assets, voice af_heart, speed 1, English US, CPU with two threads. Piper Danny uses its upstream low-quality voice checkpoint and default synthesis settings. A third local evaluation used Piper Ryan, whose upstream training dataset is listed as CC BY-NC-SA 4.0; that voice's artifacts are excluded from this publication bundle rather than assigning them broader reuse rights. See the source voice model cards and [audio/provenance notes](../examples/README.md). The reference collection has no expert acoustic validation yet; familiar controls are not phonetic matches. This appendix cannot establish a causal rarity effect, naturalness, multilingual capability or model training exposure.

Historical 32-case integration pilots remain available separately; they are not core-v1 submissions and do not define the headline protocol.
"""
    (ROOT / "docs/BASELINES.md").write_text(content, encoding="utf-8")
    print("Published 256 full-core recordings, recognizer audits and a paired comparison.")


if __name__ == "__main__":
    main()
