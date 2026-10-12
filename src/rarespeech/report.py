from __future__ import annotations

import json
import shutil
from pathlib import Path

from .io import file_hash, safe_child, write_json


def assets_root():
    # Packaged frontend assets live inside the Python wheel.
    return Path(__file__).parent / "web"


def build_report(report, out: Path, audio_root: Path | None = None):
    out.mkdir(parents=True, exist_ok=True)
    public = json.loads(json.dumps(report))
    for row in public["rows"]:
        if audio_root and row.get("audio") and row["status"] == "ok":
            source = safe_child(audio_root, row["audio"])
            if file_hash(source) != row["audio_hash"]:
                raise ValueError("audio changed after evaluation")
            relative = "audio/" + row["id"] + ".wav"
            destination = safe_child(out, relative)
            destination.parent.mkdir(exist_ok=True)
            if source.resolve() != destination.resolve():
                shutil.copyfile(source, destination)
            row["audio"] = relative
        else:
            row.pop("audio", None)
    for asset in ("index.html", "style.css", "app.js"):
        shutil.copyfile(assets_root() / asset, out / asset)
    write_json(out / "report.json", public)
    # Escape script terminators; never interpolate text as markup in the frontend.
    encoded = json.dumps(public, ensure_ascii=False).replace("<", "\\u003c").replace("\u2028", "\\u2028")
    (out / "data.js").write_text("window.RARESPEECH_DATA=" + encoded + ";\n", encoding="utf-8")
    (out / "model-card.md").write_text(model_card(report), encoding="utf-8")
    acc = report["summary"]["automatic_accuracy"]
    label = "incomplete" if acc is None else f"{acc * 100:.1f}% ASR proxy"
    import html

    svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="250" height="28" role="img" aria-label="RareSpeech {html.escape(label)}"><rect width="250" height="28" rx="3" fill="#212922"/><rect x="96" width="154" height="28" fill="#2b614a"/><g font-family="Arial,sans-serif" font-size="11" fill="#fff"><text x="48" y="18" text-anchor="middle">RareSpeech</text><text x="173" y="18" text-anchor="middle">{html.escape(label)}</text></g></svg>'
    (out / "badge.svg").write_text(svg, encoding="utf-8")


def model_card(report):
    summary = report["summary"]
    acc = summary["automatic_accuracy"]
    overall = report["totals"].get("all", {})
    wer = overall.get("wer")
    rows = [
        "### RareSpeech\n",
        "Rare-content fidelity diagnostics. Automatic values are ASR proxies, not pronunciation ratings.\n",
        "| Measurement | Result |",
        "|---|---|",
        f"| Target retention (ASR proxy) | {acc * 100:.1f}% |"
        if acc is not None
        else "| Target retention (ASR proxy) | Incomplete run — no headline score |",
        f"| Rare-content WER | {wer * 100:.1f}% |"
        if wer is not None
        else "| Rare-content WER | Not measured |",
        f"| Scored samples | {summary['scored']} / {summary['samples']} |",
        f"| Human consensus coverage | {report['review_summary']['reviewed']} / {report['review_summary']['required']} targets |",
        "",
        f"Corpus SHA-256: `{report['corpus_hash']}`. Evaluator: RareSpeech {report['version']}.",
        "",
        "Add your report URL and generation/ASR settings here. Selected subsets are not comparable to full-suite results.",
        "",
        "[Benchmark and methodology](https://github.com/owenawsong/RareSpeech)",
        "",
    ]
    return "\n".join(rows)
