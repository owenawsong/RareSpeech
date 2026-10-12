"""Build the independently grouped core and stress tracks from frozen v0.1 lexemes.

No new lexemes, guessed pronunciations, or model-generated results are introduced.
The original pilot corpus is never modified by this script.
"""

import copy
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from rarespeech.corpus import corpus_hash, load_cases  # noqa: E402
from rarespeech.io import write_json, write_jsonl  # noqa: E402

CARRIERS = [
    "The glossary has an entry for {term}. I found it on the page beside my notes.",
    "I wrote {term} in my notebook. That entry needs its own line and a clear label.",
    "The heading on this page is {term}. The page belongs to the reference collection on the shelf.",
    "We encountered {term} in the reading list. I copied the entry into the folder for tomorrow.",
    "This card is labeled {term}. I placed it beside the reference book on the desk.",
    "The index includes {term}. I marked the page so we could find the same entry again.",
    "One item on the list is {term}. There is space below it for a short note.",
    "The label reads {term}. I checked the spelling against the printed entry before filing the card.",
    "Our next entry is {term}. The reference sheet is open beside the notebook on the table.",
    "The word on this card is {term}. I copied it carefully and left the next line blank.",
    "I underlined {term} on the reference sheet. The note beside it points to another page.",
    "The document mentions {term}. I put a bookmark there and returned the volume to the desk.",
    "The archive contains an entry headed {term}. Its reference number appears on the edge of the card.",
    "The entry I copied was {term}. I saved the original page with the rest of the reading notes.",
    "On the printed list I found {term}. I added its page number to the margin of my notebook.",
    "The reference card names {term}. We kept the card with its source page in the same folder.",
]
COMMON = [
    "time", "book", "work", "home", "people", "school", "family", "garden", "window", "picture",
    "student", "meeting", "building", "children", "computer", "question", "education", "important",
    "different", "information", "development", "understanding", "responsibility", "administration",
    "communications", "transportation", "international", "environment", "organization", "government",
    "conversation", "relationship", "opportunity", "community", "university", "experience", "photograph",
]


def build():
    import wordfreq

    source = [c for c in load_cases(ROOT / "data/challenge-v1.jsonl") if c["variant"] == "isolated"]
    core, stress, design = [], [], []
    for index, old in enumerate(source):
        term = old["targets"][0]["text"]
        family = old["family_id"]
        # Related derivations form one resampling cluster, rather than pretending independence.
        cluster = "manuscripts.opisthograph" if family in {"manuscripts.01", "manuscripts.08"} else family
        available = [w for w in COMMON if len(w) == len(term) and wordfreq.zipf_frequency(w, "en") >= 3.5]
        pool = available or sorted(COMMON, key=lambda w: (abs(len(w) - len(term)), -wordfreq.zipf_frequency(w, "en")))[:3]
        control = pool[index % len(pool)]
        carrier = CARRIERS[index % len(CARRIERS)]
        texts = {
            "isolated": term,
            "dense": carrier.format(term=term),
            "confusable": f"The first label is {term}. The second label is also {term}. The last label is {term}. These are three separate cards from the same collection.",
            "extended": (
                f"The first reference on my list is {term}. I prepared the notebook before opening the archive. "
                "Each page has a heading, a page number, and space for notes. The first drawer holds the older cards, "
                "while the second drawer holds the recent additions. I checked the first page and made a note beside "
                f"its heading. Halfway through the list, I found {term} again. I kept that reference on its own line. "
                "The remaining pages were sorted into folders and returned to the shelf. I compared the final card "
                "with the notes I had made at the start. Before closing the notebook, I copied the last heading: "
                f"{term}."
            ),
            "control": carrier.format(term=control),
        }
        for variant, text in texts.items():
            target = control if variant == "control" else term
            offsets = []
            for match in re.finditer(r"(?<!\w)" + re.escape(target) + r"(?!\w)", text):
                pos = match.start()
                offsets.append({**copy.deepcopy(old["targets"][0]), "id": f"t{len(offsets)+1}", "text": target,
                                "start": pos, "end": pos + len(target), "reference_url": f"https://en.wiktionary.org/wiki/{target}"})
            is_core = variant in {"isolated", "dense"}
            case = {**copy.deepcopy(old), "id": f"core.{family}.{variant}", "text": text, "targets": offsets, "variant": variant,
                    "cluster_id": cluster, "track": "core-v1" if is_core else "stress-v1",
                    "carrier_id": "bare" if variant == "isolated" else "repetition-neutral" if variant == "confusable" else "long-neutral" if variant == "extended" else f"neutral-{index % len(CARRIERS)+1:02d}",
                    "condition_label": {"isolated": "Bare term", "dense": "Short context", "confusable": "Repetition",
                                        "extended": "Long context", "control": "Familiar control"}[variant],
                    "control_pair": f"core.{family}.control", "primary_term": term,
                    "notes": "No cross-family target terms. Explicit morphology clusters. Controls approximately match written length; pronunciation, stress, meaning and spoken duration are not matched."}
            if variant == "control":
                zipf = wordfreq.zipf_frequency(control, "en", wordlist="large")
                case["rarity"] = {**old["rarity"], "zipf": zipf, "tier": "familiar"}
                case["targets"][0]["pronunciation_status"] = "unreviewed"
                case["control_design"] = {"rare_term": term, "control_term": control, "rare_characters": len(term),
                                          "control_characters": len(control), "exact_length_match": len(term) == len(control)}
                design.append({"family": family, **case["control_design"]})
            (core if is_core else stress).append(case)
    write_jsonl(ROOT / "data/core-v1.jsonl", core)
    write_jsonl(ROOT / "data/stress-v1.jsonl", stress)
    load_cases(ROOT / "data/core-v1.jsonl")
    load_cases(ROOT / "data/stress-v1.jsonl")
    write_json(ROOT / "data/core-manifest.json", {
        "schema": "rarespeech.track.v1", "version": "0.2.0", "protocol": "core-v1",
        "status": "candidate research track; acoustic pronunciation validation pending",
        "cases": len(core), "families": len(source), "independent_lexical_clusters": len({c["cluster_id"] for c in core}),
        "conditions": ["Bare term", "Short context"], "corpus_hash": corpus_hash(core),
        "stress_cases": len(stress), "stress_hash": corpus_hash(stress), "carrier_templates": len(CARRIERS),
        "categories": __import__("json").loads((ROOT / "data/manifest.json").read_text(encoding="utf-8"))["categories"],
        "controls": design, "expert_review_complete": False,
        "notes": ["Frozen v0.1 lexemes and written-frequency annotations retained.",
                  "Core scoring balances domain, term family and condition.",
                  "No training-data absence, causal rarity effect or perceptual validation claim."]})
    import shutil

    packaged = ROOT / "src/rarespeech/data"
    packaged.mkdir(exist_ok=True)
    for name in ("core-v1.jsonl", "stress-v1.jsonl", "challenge-v1.jsonl", "core-manifest.json", "LICENSE"):
        shutil.copyfile(ROOT / "data" / name, packaged / name)
    print(f"Built {len(core)} core + {len(stress)} stress cases; {len(source)} term families.")


if __name__ == "__main__":
    build()
