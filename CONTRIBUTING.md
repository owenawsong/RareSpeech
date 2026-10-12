# Contributing

Contributions should make measurements easier to reproduce and conclusions
easier to inspect. Good first contributions: documented accepted pronunciations,
source-backed rare terms, more varied original passages, model adapters, and
regression tests for a reproduced scoring bug.

```bash
python -m pip install -e ".[dev,rarity]"
python -m pytest
ruff check src scripts examples tests
python scripts/build_corpus.py
python scripts/build_site.py
```

Corpus changes require a new hash and regeneration of dependent examples.
Scoring changes need tests describing the failure and a protocol/version update.
Do not add undocumented transcript repair or present automated verdicts as
human judgments. See docs/CONTRIBUTING_CASES.md and docs/REVIEW_RUBRIC.md.

Code contributions are MIT; original dataset text/annotations are CC BY-SA 4.0.
Disclose third-party sources and licenses. Do not submit API keys, private
documents, identifiable reviewer information, or model weights.
