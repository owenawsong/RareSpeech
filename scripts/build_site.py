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
    for name in ("index.html", "style.css", "app.js"):
        shutil.copyfile(assets_root() / name, out / name)
    manifest = json.loads((ROOT / "data" / "manifest.json").read_text(encoding="utf-8"))
    examples = (
        json.loads((ROOT / "examples" / "index.json").read_text(encoding="utf-8"))
        if (ROOT / "examples" / "index.json").exists()
        else []
    )
    value = {
        "schema": "rarespeech.explorer.v1",
        "cases": load_cases(ROOT / "data" / "challenge-v1.jsonl"),
        "categories": manifest["categories"],
        "examples": examples,
    }
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
