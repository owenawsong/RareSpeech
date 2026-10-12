# Measurement protocol · v0.1

## Scope

RareSpeech measures content retention on authored English specialist-text challenges. The collection is a candidate release without expert pronunciation validation. It does not establish training-data absence, naturalness, universal TTS quality, or a population listening-study ranking. The bundled pilots test complete inference pipelines, including frontends and chunking. They cannot identify the internal cause of an observed error. Inflect is maintained by this project’s author.

## Rarity and corpus

Eight equally represented domains, 64 primary term families, five conditions per family. Frequency metadata uses wordfreq 3.1.1’s large English list: Zipf <1.5 extreme, 1.5–2.5 rare. Zero is below coverage, not measured absence. Written frequency is not spoken frequency or known training exposure. Neighboring targets in dense passages do not have individual frequency metadata in this release.

Carrier templates repeat. Passages are index readouts, not scientific assertions. Familiar controls repeat the isolated carrier with “garden”; they are not word-length-matched causal controls and cannot establish a rarity penalty. Controls are excluded from the headline.

## References

Each occurrence has exact character offsets and a stable target ID. Explicit `spoken_forms` can provide documented lexical expansions only for that span. No spelling correction, inferred synonyms, fuzzy matching, or LLM repair.

Normalization: Unicode NFKC, case folding, punctuation-boundary tokenization, internal apostrophes retained. Diacritics and numbers remain. Hyphens split compounds. Contractions and number readings are not automatically expanded. Acoustic distinctions can be concealed by transcription; target retention is therefore a proxy.

## Automatic metrics

Deterministic Levenshtein alignment tie policy: diagonal match/substitution, deletion, insertion. Select the authored alias combination with minimum edit count (up to 64 combinations). Alignment is bounded to four million cells.

WER = (substitutions + deletions + insertions) / reference tokens, micro-aggregated within each reported group. It may exceed 100%. Target retention requires all reference tokens in the designated span to match identical hypothesis tokens. Insertions inside/around a span affect WER but need not invalidate retention. Repeated text can have multiple optimum alignments; deterministic localization is not proof of the actual missing occurrence.

The headline is the equal-category mean of retained/scored targets, excluding controls. Dense/extended cases contribute more target occurrences within a category. Missing audio/transcripts withhold the complete-suite headline; observed scored-subset values are separate. Blank transcripts are scored failures. Do not silently exclude unavailable measurements or replace them with zero.

## Uncertainty

Resample term families within each category, keeping variants/repeats together, 1,000 draws with seed 17. Report percentile 2.5/97.5 endpoints only if every scored category has at least two families. This estimates variation under that design, not recognizer bias, human-review uncertainty or generalization to all rare speech. The one-family-per-domain pilots have no interval.

## Recognizer confounds

ASR can reject valid rare speech or reconstruct incorrectly spoken words. Multiple recognizers are a disagreement detector, not ground truth. Do not prime the main ASR with target vocabulary. Record model/revision, precision/device, decoding, VAD and context settings. Human reference recordings and qualified reviews of both apparent failures and successes are needed to validate the proxy. This release does not claim that calibration is complete.

## Human review

Per-target pass/fail/uncertain under the presence-plus-pronunciation rubric. Decisions bind to report ID, sample, audio hash, target and rater pseudonym. Two distinct pseudonyms must agree, without uncertain/conflicting votes. Pseudonyms do not prove independence or expertise. Only complete consensus coverage produces a verified headline. Disputes stay unresolved until auditable adjudication replaces previous decisions.

The diagnostic report exposes model identity and ASR results. This is not a blinded preference arena. For a research listening study, use a separately randomized, blinded protocol with qualified listeners.

## Generation and provenance

Persistent Python adapters load once; command adapters may cold-load per call. Wall time covers the adapter call and file writing, excludes factory startup, and is not TTFA, a memory measurement or a comparable speed ranking. Imported audio has no timing. Declare immutable model revision, voice, actual seed support, frontend and effective synthesis parameters. Seeds do not ensure bitwise reproducibility.

Corpus SHA-256 covers selected cases sorted by ID. Run identity covers corpus, adapter hash, model label, repeats and seed. Each successful WAV is hashed. Transcripts/reviews must match it. Report identity covers corpus, samples and transcripts. Public configs omit local paths/commands and inline credentials are rejected. Custom adapters execute with the user’s privileges.

Checkpoint comparisons require identical selected corpus and repeat IDs. Different ASR settings are a confound. Never compare subsets with full-suite scores or silently change normalization/reference rules.

## Related work

- [TTSProof](https://github.com/Mormolykos/ttsproof): difficult-input failure diagnostics.
- [Open TTS Eval](https://github.com/inworld-ai/open-tts-eval): reproducible metrics and ASR limitations.
- [ASR evaluation confidence intervals](https://www.isca-archive.org/interspeech_2021/taylor21_interspeech.html).
- [Semantically unpredictable sentences](https://www.isca-archive.org/sioa_1989/hazan89_sioa.html).
- [wordfreq](https://github.com/rspeer/wordfreq): written-frequency estimates.
