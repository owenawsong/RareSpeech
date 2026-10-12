"""Build the authored challenge collection. No scraped sentences or synthetic model results."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from rarespeech.corpus import corpus_hash, load_cases  # noqa: E402
from rarespeech.io import write_json, write_jsonl  # noqa: E402

# Candidate lexemes; source links are discovery aids, not claims of expert pronunciation review.
LEXICON = {
    "mineralogy": (
        "Mineralogy",
        "Minerals, textures & formations",
        [
            "omphacite",
            "aegirine",
            "clinozoisite",
            "riebeckite",
            "lawsonite",
            "charnockite",
            "serpentinite",
            "eclogite",
        ],
    ),
    "botany": (
        "Botany",
        "Structures & specialist descriptions",
        [
            "anemophily",
            "cleistogamy",
            "phyllotaxis",
            "gynobasic",
            "peltate",
            "saxicolous",
            "epipetalous",
            "cauliflory",
        ],
    ),
    "manuscripts": (
        "Manuscript studies",
        "Books, inscriptions & letterforms",
        [
            "opisthograph",
            "quaternion",
            "bifolium",
            "ductus",
            "rubrication",
            "palaeography",
            "codicology",
            "opisthographic",
        ],
    ),
    "linguistics": (
        "Linguistics",
        "Sounds & grammatical structures",
        [
            "haplology",
            "anaptyxis",
            "epenthesis",
            "apocope",
            "metathesis",
            "suppletion",
            "allomorphy",
            "enclitic",
        ],
    ),
    "zoology": (
        "Zoology",
        "Anatomy & uncommon descriptors",
        [
            "opisthobranch",
            "chaetognath",
            "lophophore",
            "pterygopodium",
            "cnidocyte",
            "cercopithecine",
            "platyhelminth",
            "urochordate",
        ],
    ),
    "astronomy": (
        "Astronomy",
        "Orbits & celestial mechanics",
        ["analemma", "apsidal", "anomalistic", "syzygy", "saros", "selenographic", "lunisolar", "nutation"],
    ),
    "mathematics": (
        "Mathematics",
        "Structures & specialist vocabulary",
        [
            "homeomorphism",
            "equicontinuity",
            "diffeomorphism",
            "Noetherian",
            "idempotence",
            "holonomy",
            "cohomology",
            "quasiconformal",
        ],
    ),
    "musicology": (
        "Musicology",
        "Forms, ornaments & notation",
        [
            "sesquialtera",
            "hemiola",
            "isorhythm",
            "passacaglia",
            "appoggiatura",
            "acciaccatura",
            "mensural",
            "tintinnabulation",
        ],
    ),
}


def main():
    try:
        import wordfreq
    except ImportError:
        raise SystemExit("Install rarespeech[rarity] to reproduce corpus frequency metadata.")
    cases, domains = [], []
    for category, (label, description, terms) in LEXICON.items():
        domains.append({"id": category, "label": label, "description": description, "families": len(terms)})
        for i, term in enumerate(terms):
            neighbor, third = terms[(i + 1) % len(terms)], terms[(i + 2) % len(terms)]
            zipf = wordfreq.zipf_frequency(term, "en", wordlist="large")
            evidence = {
                "provider": "wordfreq",
                "version": "3.1.1",
                "language": "en",
                "wordlist": "large",
                "zipf": zipf,
                "tier": "below-coverage"
                if zipf == 0
                else "extreme"
                if zipf < 1.5
                else "rare"
                if zipf < 2.5
                else "specialist",
                "meaning": "general written-frequency estimate; not training exposure or difficulty",
                "source": "https://github.com/rspeer/wordfreq",
            }
            texts = {
                "isolated": f"The entry names {term}. Read the entry once, then continue to the next page.",
                "dense": f"The specialist index lists {term}, {neighbor}, and {third}. Each term has its own entry. Keep all three entries in that order.",
                "confusable": f"Entry A is {term}; entry B is {neighbor}; entry C is {term} again. The duplicate in entry C is intentional. Read A, B, and C without merging them.",
                "extended": f"This is a spoken transcription of an index card. The heading is {term}. The card belongs to a specialist collection, and its spelling must be preserved in the record. A second card has the heading {neighbor}. Those are separate cards, even when a reader is unfamiliar with both headings. The first card is filed before the second. A handwritten note refers back to {term}, and a printed note refers to {third}. The notes should not replace either heading. At the end of the recording, the archivist returns to the first card and repeats its heading: {term}. The recording ends after this sentence.",
                "control": "The entry names garden. Read the entry once, then continue to the next page.",
            }
            family = f"{category}.{i + 1:02d}"
            for variant, text in texts.items():
                chosen = (
                    ["garden"]
                    if variant == "control"
                    else (
                        [term]
                        if variant == "isolated"
                        else [term, neighbor]
                        if variant == "confusable"
                        else [term, neighbor, third]
                    )
                )
                targets = []
                # Every occurrence is separately anchored; an occurrence elsewhere cannot rescue a dropped one.
                import re

                matches = []
                for word in chosen:
                    matches += [
                        (m.start(), m.end(), word) for m in re.finditer(r"\b" + re.escape(word) + r"\b", text)
                    ]
                for j, (start, end, word) in enumerate(sorted(matches)):
                    targets.append(
                        {
                            "id": f"t{j + 1}",
                            "text": word,
                            "start": start,
                            "end": end,
                            "spoken_forms": [],
                            "pronunciation_status": "unreviewed",
                            "reference_url": "https://en.wiktionary.org/wiki/" + word,
                        }
                    )
                cases.append(
                    {
                        "id": family + "." + variant,
                        "family_id": family,
                        "category": category,
                        "variant": variant,
                        "language": "en",
                        "text": text,
                        "targets": targets,
                        "rarity": evidence,
                        "authorship": "Original carrier text by RareSpeech; candidate lexemes",
                        "review_status": "candidate",
                        "control_pair": family + ".control",
                        "notes": "Control matches isolated sentence structure, not term length. Dense passages are index readouts, not scientific assertions.",
                    }
                )
    path = ROOT / "data" / "challenge-v1.jsonl"
    write_jsonl(path, cases)
    load_cases(path)
    write_json(
        ROOT / "data" / "manifest.json",
        {
            "schema": "rarespeech.corpus.v1",
            "version": "0.1.0",
            "status": "authored candidate collection; no expert pronunciation validation yet",
            "license": "CC-BY-SA-4.0",
            "cases": len(cases),
            "families": 64,
            "categories": domains,
            "corpus_hash": corpus_hash(cases),
            "rarity": "wordfreq 3.1.1, large English list; Zipf 0 is below coverage, not proof of zero occurrence",
            "controls": "Identical familiar carrier controls diagnose recognizer/pipeline behavior. They are not length-matched causal controls and are excluded from the main proxy.",
            "known_limitations": [
                "Carrier templates repeat across domains",
                "General written frequency does not establish spoken rarity",
                "Below-coverage terms need specialist source review",
                "Some terms are familiar within their disciplines",
                "Pronunciation judgments require qualified raters",
                "No training-exposure claim",
            ],
        },
    )
    print(f"Built {len(cases)} cases / 64 families / {len(domains)} domains")


if __name__ == "__main__":
    main()
