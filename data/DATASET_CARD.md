# Challenge collection · v0.1

**Status:** authored candidate collection; expert pronunciation validation pending.

320 cases / 64 term families / eight domains / five conditions. English. Original carrier text and annotations are CC BY-SA 4.0. `manifest.json` records the hash and limitations; `scripts/build_corpus.py` reproduces the collection with pinned wordfreq metadata.

## Fields

`id`, `family_id`, `category`, `variant`, `language`, `text`, `targets`, `rarity`, `review_status`, `control_pair`, `notes`.

Targets contain an ID, written spelling, Python character offsets, optional accepted spoken forms, review status and discovery link. These are not UTF-8 byte offsets. All current terms use BMP characters; future non-BMP terms require corresponding frontend offset handling.

## Construction

Original sentences present terms as index entries to avoid unsupported scientific assertions. Conditions increase target density, introduce deliberate repetition, and extend passages. Controls repeat the familiar isolated carrier with “garden.” They lack word-length matching and cannot establish a causal obscurity penalty.

Frequency estimates cover the primary family term, not every neighboring target. Zipf zero means below list coverage, not proof of absence in training or in the wild. General written frequency does not establish spoken rarity; words may be familiar within their fields.

## Limitations

Repeated carrier templates limit contextual diversity. Expert pronunciations, discovery-link availability and specialist correctness are not independently validated. There is no hidden private test; future training on the published cases can contaminate comparisons. Publish selected IDs, hashes and settings with results. Use this collection for diagnostics and qualified review development, not an established human-quality ranking.
