# RareSpeech dataset card · v0.2

**Candidate English research collection.** Independent specialist pronunciation validation is pending. Authored carrier text and annotations are CC BY-SA 4.0. Software is MIT.

| Frozen track | Cases | Conditions | Intended use |
|---|---:|---|---|
| Core v1 | 128 | Bare term; short neutral context | Balanced primary-target retention |
| Stress v1 | 192 | Repetition; long context; familiar control | Condition diagnostics |
| Legacy v0.1 | 320 | Original five conditions | Reproduce integration pilots |

The core/stress tracks retain the original 64 primary specialist lexemes across eight domains. Each core case has one anchored occurrence. Repetition and long-context cases each have three. Related opisthograph derivations share a resampling cluster, giving 63 declared lexical clusters in the core. This annotation does not prove biological or linguistic independence.

## Construction and provenance

`scripts/build_corpus.py` reproduces the frozen legacy collection using wordfreq 3.1.1. `scripts/build_core.py` derives the core/stress text and emits `core-manifest.json` with both hashes and control design. Sixteen neutral short carriers rotate across families; the longer/repetition carriers remain shared templates. Lexical entry checks are in `lexical-source-checks.json`; an existing dictionary page does not establish expert-approved pronunciation.

Frequency metadata describes the primary family term, not all neighboring legacy targets. Zipf zero means below the list's coverage, **not** zero real frequency or absence from training. General written frequency cannot establish spoken rarity or rarity within a specialist field.

Familiar controls prefer exact written character length, then a close length from a documented common-word pool. Matching is approximate and does not control phonemes, syllables, stress, semantic familiarity or spoken duration. The control gap cannot establish a causal rarity effect. Legacy controls use “garden” and have no length matching.

## Fields

Cases carry `id`, `family_id`, `category`, `variant`, `language`, `text`, `targets`, `rarity`, review status and notes. New tracks add `track`, `cluster_id`, `primary_term`, `carrier_id`, `condition_label` and control design. IDs retain historical condition codes: core `dense` means **short neutral context**, stress `confusable` means **repetition**. These codes are compatibility names, not acoustic claims.

Target offsets are Python character offsets, not UTF-8 bytes. Terms in this release use BMP characters. Targets include discovery links and optional accepted written forms; they do not include guessed phonetic references.

## What has and has not been validated

Software checks validate offsets, case counts, grouping, frequency provenance, source entries, hashes and measured audio/transcript bindings. Expert-approved pronunciations, reference recordings, independent human agreement and proxy calibration remain pending. No hidden test set exists; training on these public cases can contaminate comparisons. Carrier diversity and English-only coverage limit generalization.

Publish the selected corpus/evaluator hash, voice, weights, repeat/seed settings, recognizer identity and review coverage with every result. A subset is a diagnostic selection, not a canonical core score. See [methodology](../docs/METHODOLOGY.md) and [validation plan](../docs/RESEARCH_PLAN.md).
