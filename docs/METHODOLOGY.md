# Measurement protocol · v0.2

## Scope and frozen tracks

Capture files are immutable evidence. An annotation-only correction uses `rarespeech.reannotate.reannotate(source, corrected_cases, out, reason)` into a new empty directory. It permits only explicit design metadata, verifies unchanged synthesis text/targets, audio and transcript bytes, and retains originals and changed fields. Derived reports and reviews must be recomputed; a changed corpus has a new identity. This tool does not permit correcting measured failures by changing reference text.

RareSpeech evaluates a complete TTS pipeline's lexical content on curated English specialist terms. Automatic values are ASR proxies. The candidate collection does not yet have expert acoustic acceptance rules or validated recognizer calibration. It does not infer training-data absence, assign naturalness scores or certify universal TTS quality.

**Core v1:** 128 cases, 64 primary term families, eight domains; bare terms and short neutral carriers. **Stress v1:** 192 cases; repetition, long context and familiar controls. **Legacy v0.1:** the original 320-case collection, kept separately. Package defaults select core. Track identification uses exact corpus hashes; subsets cannot claim full-track results.

The core/stress lexemes and wordfreq 3.1.1 annotations are retained from the original collection. Core cases contain one primary occurrence, with no cross-family neighbor targets. Explicit morphology clusters group related derivations. There are 63 declared lexical clusters, not proof of statistical independence over a population. Sixteen short carrier templates are shared. Core control-pair IDs reference cases in the separate stress track; an audit of core alone reports them unavailable within that selected track.

## Rarity and controls

Wordfreq large English Zipf estimates below 1.5 are labeled extreme, 1.5–2.5 rare. Zero means below list coverage, not a measured absence. Written frequency is not spoken frequency or model exposure. Dictionary-entry existence is checked; acoustic pronunciation acceptance is pending.

New familiar controls match written character length where the documented control lexicon permits; nearest-length alternatives and actual differences are recorded. They share the corresponding short carrier. Phonemes, stress, meaning and spoken duration are not matched, so differences do not establish a causal rarity effect. Controls are excluded from rare-target aggregates. Legacy controls reuse “garden” and were not length matched.

## Anchors and normalization

Each occurrence has a stable target ID and exact character offsets. Explicit `spoken_forms` can supply documented lexical expansions for that span; there is no inferred synonym, fuzzy spelling correction or LLM repair.

Unicode NFKC and case folding are applied; punctuation defines boundaries, internal apostrophes remain, diacritics and numeric values are preserved. Hyphens split compounds. Number readings and contractions are not automatically expanded. Deterministic minimum-edit alignment prefers diagonal match/substitution, then deletion, then insertion. Alias combinations are bounded at 64, alignments at four million cells.

Repeated text may have several optimal alignments. Deterministic localization is not proof of the acoustic occurrence that failed. Insertions affect WER without necessarily invalidating a target whose reference tokens all match.

## Automatic measurements

WER = (substitutions + deletions + insertions) / reference tokens; it can exceed 100%. Group WER micro-aggregates errors and reference tokens. Each target occurrence is retained only when all its aligned reference tokens match.

**Balanced primary-target retention** averages occurrences within generation, generations within case, cases within condition, conditions within family, families within domain, then domains equally. Neighbor-inclusive retention is separate. The historical headline averages occurrence retention equally across domains and is retained under its original meaning. Do not silently substitute one protocol for another.

An incomplete declared design gets no complete aggregate. Missing generations, missing transcripts and never-generated declared repeats stay visible. Blank transcripts are scored failures. Mixed recognizer configurations withhold comparable headlines. Observed scored-subset values are separate.

## Uncertainty and paired comparisons

Connected lexical families form bootstrap clusters; explicit `cluster_id` values also link families. Resampling is category-stratified with 1,000 draws and seed 17. Percentile endpoints are at 2.5/97.5%. There must be at least two clusters per category for an interval. Related samples and repeats remain together.

The legacy dense neighbors connect all families within each domain, leaving one cluster per domain. Its previous family-only interval was overconfident and is now withheld. Paired analysis resamples the same clusters on both sides and reports candidate minus baseline. Corpus, evaluator source, ASR settings and sample/repeat assignment must match. Intervals describe variation within the specified collection; they do not address ASR bias, reviewer error or generalization to all rare language.

## Recognizer provenance and confounds

The default ASR uses small.en, CPU int8, beam size 5, temperature zero, no VAD, no previous-text conditioning and no vocabulary prompt. Actual model.bin/config.json SHA-256 values, library versions, precision/device and decoding settings are recorded. Custom local recognizer paths are labeled without publishing private directories. A second recognizer measures paired disagreement, not ground truth.

ASR may reject correct rare speech or reconstruct incorrectly pronounced words. Human reference recordings and qualified adjudication of successes and failures are required to calibrate the proxy. This release does not claim that work is complete.

## Listening review

Randomized packets hide model names, original sample/report IDs, generation settings and ASR verdicts. An organizer-only key is written outside the participant directory. The reference passage is visible and listeners may recognize voices. This is not a guarantee of complete perceptual blinding or a naturalness preference arena.

Decisions use pass/fail/uncertain under the presence-plus-pronunciation rubric and bind to exact audio and target IDs. Identity is restored with `unblind`; two distinct raters must agree for consensus. Uncertain/conflicting votes remain unresolved. Only complete consensus yields pronunciation aggregates. Distinct pseudonyms, playback events and agreeing votes do not establish independent expert judgment. Reviewer names are normalized for duplicate detection. [Study workflow](SUBMISSIONS.md).

## Generation, reporting and submission

Persistent Python adapters load once; shell-free command adapters may reload each invocation. Adapter-call wall time excludes factory load and is not streaming TTFA, memory measurement or a comparable speed ranking. Imported audio has no synthesis timing. Record immutable model identity, voice, frontend and effective parameters. Seeds do not guarantee reproducibility; unsupported seeds are declared.

Selected cases, audio, transcript identity and evaluator source are hash bound. Public adapter configurations omit local paths/commands and reject inline credentials. Custom adapters execute with user privileges. Reports are portable local assets without telemetry.

Submission checks recompute measurements and verify bindings, coverage, canonical track, implementation version, immutable model identity, fixed recognizer settings and recognizer weights/configuration fingerprints. Passing these checks is not scientific endorsement. Rejected submissions suppress headline measurements while exposing separately labeled reconstructed observations.

See [the technical report](TECHNICAL_REPORT.md), [baseline appendix](BASELINES.md) and [external validation plan](RESEARCH_PLAN.md).
