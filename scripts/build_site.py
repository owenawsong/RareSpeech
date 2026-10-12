import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from rarespeech.corpus import load_cases  # noqa: E402
from rarespeech.report import assets_root  # noqa: E402


def main():
    out = ROOT / "site"
    out.mkdir(exist_ok=True)
    for name in ("index.html", "style.css", "research.css", "app.js"):
        shutil.copyfile(assets_root() / name, out / name)
    manifest = json.loads((ROOT / "data" / "core-manifest.json").read_text(encoding="utf-8"))
    examples = (
        json.loads((ROOT / "examples" / "index.json").read_text(encoding="utf-8"))
        if (ROOT / "examples" / "index.json").exists()
        else []
    )
    value = {
        "schema": "rarespeech.explorer.v1",
        "cases": load_cases(ROOT / "data" / "core-v1.jsonl"),
        "tracks": {
            "core": load_cases(ROOT / "data" / "core-v1.jsonl"),
            "stress": load_cases(ROOT / "data" / "stress-v1.jsonl"),
            "legacy": load_cases(ROOT / "data" / "challenge-v1.jsonl"),
        },
        "manifest": manifest,
        "categories": manifest["categories"],
        "examples": examples,
    }
    value["measurements"] = []
    for example in examples:
        report_path = ROOT / "examples" / example["slug"] / "report.json"
        if report_path.exists() and not example.get("legacy", False):
            report = json.loads(report_path.read_text(encoding="utf-8"))
            alternate = json.loads((report_path.parent / "alternate-asr-report.json").read_text(encoding="utf-8"))
            value["measurements"].append({
                "name": example["name"], "url": example["url"],
                "protocol": report.get("research_protocol", {}), "summary": report["summary"],
                "wer": report["totals"].get("all", {}).get("wer"),
                "asr_audit": report.get("asr_audit", {}), "metadata": report["metadata"],
                "secondary_protocol": alternate.get("research_protocol", {}),
            })
    value["comparisons"] = []
    comparison_dir = ROOT / "examples/comparisons"
    for path in sorted(comparison_dir.glob("*.json")):
        comparison = json.loads(path.read_text(encoding="utf-8"))
        value["comparisons"].append({"name": path.stem, "analysis": comparison["paired_analysis"],
                                     "url": "comparisons/" + path.name})
        (out / "comparisons").mkdir(exist_ok=True)
        shutil.copyfile(path, out / "comparisons" / path.name)
    from rarespeech.audit import audit_corpus

    value["audit"] = audit_corpus(value["cases"])
    (out / "data.js").write_text(
        "window.RARESPEECH_DATA=" + json.dumps(value, ensure_ascii=False).replace("<", "\\u003c") + ";\n",
        encoding="utf-8",
    )
    for example in examples:
        source = ROOT / "examples" / example["slug"]
        if source.exists():
            shutil.copytree(source, out / "examples" / example["slug"], dirs_exist_ok=True)
    print("Built site/ — deploy this directory to static hosting, or run rarespeech serve site")


if __name__ == "__main__":
    main()
