"""Convenience workflow built from the same inspectable generation/scoring stages."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

from .evaluate import evaluate
from .io import read_jsonl, write_json
from .report import build_report
from .run import generate, transcribe


def benchmark(
    cases,
    config,
    out: Path,
    label: str,
    repeats=1,
    seed=17,
    resume=False,
    reuse_from=None,
    asr_model="small.en",
    asr_device="cpu",
    asr_compute="int8",
):
    if importlib.util.find_spec("faster_whisper") is None:
        raise ImportError('one-command evaluation needs ASR: install "rarespeech[asr]" first')
    samples = generate(cases, config, out, label, repeats, seed, resume, reuse_from)
    if any(s["status"] != "ok" for s in samples):
        raise ValueError("generation incomplete; repair the adapter and resume before scoring")
    transcripts = out / "asr.jsonl"
    transcribe(out, transcripts, asr_model, asr_device, asr_compute, resume)
    metadata = json.loads((out / "run.json").read_text(encoding="utf-8"))
    report = evaluate(cases, samples, read_jsonl(transcripts), metadata)
    write_json(out / "report.json", report)
    build_report(report, out / "report", out)
    print(f"Evidence report: {out / 'report' / 'index.html'}")
    return report
